"""
Comprehensive Unit & Security Test Suite for AuraLoop VTO (`04-youcam-vto`).
Covers all requirements from DESIGN_OPUS55.md and REVIEW_LUNA56.md.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import unittest
import urllib.request

from auraloop_vto.engine import (
    AuraLoopEngine,
    CartBuilder,
    IMMUTABLE_SKU_CATALOG,
    build_default_sample_png_bytes,
)
from auraloop_vto.mcp_server import AuraLoopMCPServer
from auraloop_vto.models import (
    NonceReplayCache,
    SKUItem,
    ciede2000_delta_e,
    srgb_hex_to_cielab,
    validate_and_sanitize_image,
)
from auraloop_vto.providers import (
    BudgetExhaustedError,
    UnitBudgetLedger,
    YouCamAuthError,
    YouCamClient,
)
from auraloop_vto.server import create_http_server


class TestUnitBudgetLedgerAndUnknownState(unittest.TestCase):
    def test_reserve_commit_rollback_and_unknown_submission(self) -> None:
        ledger = UnitBudgetLedger(total_units=1000, hard_ceiling=950)
        ledger.reserve("task-1", 100)
        ledger.commit("task-1")
        snap1 = ledger.snapshot()
        self.assertEqual(snap1["committed_units"], 100)
        self.assertEqual(snap1["reserved_units"], 0)

        ledger.reserve("task-2", 50)
        ledger.rollback("task-2")
        snap2 = ledger.snapshot()
        self.assertEqual(snap2["committed_units"], 100)
        self.assertEqual(snap2["reserved_units"], 0)

        # Non-idempotent POST timeout marks unknown_submission and retains unit hold
        ledger.reserve("task-3", 200)
        ledger.mark_unknown_submission("task-3", "POST timed out")
        snap3 = ledger.snapshot()
        self.assertEqual(snap3["unknown_submission_units"], 200)
        self.assertEqual(snap3["remaining_safe_units"], 950 - 300)

        # Cannot rollback an unknown_submission task
        with self.assertRaises(KeyError):
            ledger.rollback("task-3")

        # Hard ceiling enforcement
        with self.assertRaises(BudgetExhaustedError):
            ledger.reserve("task-4", 651)


class TestImageSanitizerAndConsentGate(unittest.TestCase):
    def test_consent_required(self) -> None:
        sample = build_default_sample_png_bytes()
        with self.assertRaises(PermissionError):
            validate_and_sanitize_image(sample, consent_granted=False)

    def test_png_metadata_stripping_and_magic_bytes(self) -> None:
        sample = build_default_sample_png_bytes()
        self.assertIn(b"FakeGPSAndCameraSerialMetadata", sample)
        info = validate_and_sanitize_image(sample, consent_granted=True)
        self.assertEqual(info["mime_type"], "image/png")
        self.assertTrue(info["exif_stripped"])
        self.assertGreaterEqual(info["stripped_segments"], 1)
        self.assertNotIn(b"FakeGPSAndCameraSerialMetadata", info["sanitized_payload"])

        with self.assertRaises(ValueError):
            validate_and_sanitize_image(b"not-a-valid-image-header-at-all-1234567890", consent_granted=True)


class TestColorScienceAndCartValidation(unittest.TestCase):
    def test_ciede2000_identity_and_symmetry(self) -> None:
        lab1 = srgb_hex_to_cielab("#E3B998")
        lab2 = srgb_hex_to_cielab("#E1B695")
        self.assertEqual(ciede2000_delta_e(lab1, lab1), 0.0)
        d12 = ciede2000_delta_e(lab1, lab2)
        d21 = ciede2000_delta_e(lab2, lab1)
        self.assertAlmostEqual(d12, d21, places=4)
        self.assertLess(d12, 3.0)

    def test_cart_builder_rejects_bad_quantity_or_untrusted_url(self) -> None:
        sku = IMMUTABLE_SKU_CATALOG[0]
        with self.assertRaises(ValueError):
            CartBuilder.build_cart([(sku, 0, "zero qty")])

        bad_sku = SKUItem(
            sku_id="BAD-1",
            brand="Brand",
            name="Bad URL Item",
            category="skincare",
            price_usd=20.0,
            currency="USD",
            hex_color="#FFFFFF",
            lab_color=(100.0, 0.0, 0.0),
            target_concerns=(),
            contraindications=(),
            checkout_url="http://evil.example.org/phish",
        )
        with self.assertRaises(ValueError):
            CartBuilder.build_cart([(bad_sku, 1, "bad host")])


class TestEndToEndPipelineAndProvenance(unittest.TestCase):
    def test_consultation_provenance_and_side_by_side_fallback(self) -> None:
        eng = AuraLoopEngine()
        res = eng.run_consultation(consent_granted=True, mode="simulated", seed=42, allow_chained_vto=True)
        self.assertEqual(res["overall_mode"], "simulated")
        self.assertEqual(len(res["stage_provenance"]), 6)
        self.assertTrue(res["regimen"]["barrier_sensitivity_detected"])
        self.assertEqual(len(res["regimen"]["suppressed_contraindicated_skus"]), 1)

        # Side-by-side fallback when chained VTO is disabled
        res_sbs = eng.run_consultation(consent_granted=True, mode="simulated", seed=42, allow_chained_vto=False)
        self.assertEqual(res_sbs["vto_artifacts"]["apparel_vto"]["ref_type"], "side_by_side_preview")
        self.assertEqual(res_sbs["stage_provenance"]["apparel_vto"]["status"], "fallback")

    def test_hmac_replay_cache(self) -> None:
        cache = NonceReplayCache(window_sec=300)
        secret = "my-hmac-secret"
        ts = str(time.time())
        nonce = "nonce-12345678"
        body = b'{"consent_granted": true}'
        sig = hmac.new(secret.encode("utf-8"), f"{ts}.{nonce}.".encode("utf-8") + body, hashlib.sha256).hexdigest()

        ok1, _ = cache.verify_and_record(secret, ts, nonce, body, sig)
        self.assertTrue(ok1)

        # Replay with same nonce must fail
        ok2, reason2 = cache.verify_and_record(secret, ts, nonce, body, sig)
        self.assertFalse(ok2)
        self.assertIn("Replay", reason2)

    def test_mcp_and_http_server(self) -> None:
        mcp = AuraLoopMCPServer()
        tools = mcp.handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(len(tools["result"]["tools"]), 3)

        srv = create_http_server(host="127.0.0.1", port=0)
        port = srv.server_address[1]
        import threading

        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                body = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(body["status"], "ok")
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
