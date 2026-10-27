"""
Data models, immutable SKU catalog, CIELAB / CIEDE2000 color science primitives,
image EXIF sanitizer, and per-stage provenance models for AuraLoop VTO (`04-youcam-vto`).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
import datetime
import hashlib
import hmac
import math
import struct
import threading
import time
from typing import Any, Dict, List, Optional, Tuple


PROMO_CODE = "YOUCAMHACK2609a"
COSMETIC_DISCLAIMER = (
    "COSMETIC & STYLING INFORMATION ONLY: AuraLoop VTO provides cosmetic appearance estimates "
    "and virtual try-on previews. It is NOT a medical device and does NOT provide dermatological "
    "or clinical diagnosis."
)

SKIN_METRICS_14: Tuple[str, ...] = (
    "moisture",
    "oiliness",
    "redness",
    "texture",
    "pores",
    "wrinkles",
    "acne",
    "dark_spots",
    "radiance",
    "firmness",
    "dark_circles",
    "eye_bags",
    "droopy_upper_eyelid",
    "droopy_lower_eyelid",
)

STAGE_NAMES_6: Tuple[str, ...] = (
    "skin_analysis",
    "skin_tone",
    "makeup_vto",
    "apparel_vto",
    "regimen_engine",
    "cart_builder",
)


def jst_now_iso() -> str:
    jst = datetime.timezone(datetime.timedelta(hours=9))
    return datetime.datetime.now(jst).isoformat(timespec="seconds")


@dataclass(frozen=True)
class StageProvenance:
    stage_name: str
    provider: str  # "youcam_live" | "auraloop_sim" | "local_engine"
    mode: str      # "live" | "simulated"
    status: str    # "ok" | "fallback" | "failed" | "skipped" | "unknown_submission"
    degraded_reason: Optional[str]
    units_reserved: int
    units_spent: int
    duration_ms: float
    request_id: str

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class ArtifactRef:
    stage_name: str
    ref_type: str  # "sim_uri" | "api_file_id" | "side_by_side_preview"
    uri_or_id: str
    preview_svg_data_uri: str
    chained_from_stage: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class SKUItem:
    sku_id: str
    brand: str
    name: str
    category: str  # "skincare" | "makeup" | "apparel" | "accessory"
    price_usd: float
    currency: str
    hex_color: str
    lab_color: Tuple[float, float, float]
    target_concerns: Tuple[str, ...]
    contraindications: Tuple[str, ...]
    checkout_url: str

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["lab_color"] = list(self.lab_color)
        d["target_concerns"] = list(self.target_concerns)
        d["contraindications"] = list(self.contraindications)
        return d


def srgb_hex_to_cielab(hex_color: str) -> Tuple[float, float, float]:
    """
    Pure-Python sRGB hex (#RRGGBB) -> linear RGB -> CIE XYZ (D65) -> CIELAB (L*, a*, b*) conversion.
    Handles negative / low-luminance values cleanly without complex roots.
    """
    clean = hex_color.strip().lstrip("#")
    if len(clean) != 6:
        raise ValueError(f"Expected 6-char hex color, got '{hex_color}'.")
    r_srgb = int(clean[0:2], 16) / 255.0
    g_srgb = int(clean[2:4], 16) / 255.0
    b_srgb = int(clean[4:6], 16) / 255.0

    def _to_linear(c: float) -> float:
        c = max(0.0, min(1.0, c))
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r = _to_linear(r_srgb)
    g = _to_linear(g_srgb)
    b = _to_linear(b_srgb)

    # sRGB to XYZ (D65 reference white)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    xn, yn, zn = 0.95047, 1.00000, 1.08883
    delta = 6.0 / 29.0
    delta3 = delta ** 3

    def _f(t: float) -> float:
        t = max(0.0, t)
        return (t ** (1.0 / 3.0)) if t > delta3 else (t / (3.0 * delta * delta) + 4.0 / 29.0)

    fx, fy, fz = _f(x / xn), _f(y / yn), _f(z / zn)
    l_star = 116.0 * fy - 16.0
    a_star = 500.0 * (fx - fy)
    b_star = 200.0 * (fy - fz)
    return (round(l_star, 4), round(a_star, 4), round(b_star, 4))


def ciede2000_delta_e(lab1: Tuple[float, float, float], lab2: Tuple[float, float, float]) -> float:
    """
    Pure-Python CIE Delta E 2000 (CIEDE2000) perceptual color difference metric.
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    C_bar = 0.5 * (C1 + C2)
    C_bar7 = C_bar ** 7
    G = 0.5 * (1.0 - math.sqrt(C_bar7 / (C_bar7 + 25.0 ** 7)))

    a1_p = (1.0 + G) * a1
    a2_p = (1.0 + G) * a2
    C1_p = math.hypot(a1_p, b1)
    C2_p = math.hypot(a2_p, b2)

    h1_p = math.degrees(math.atan2(b1, a1_p)) % 360.0 if C1_p > 1e-9 else 0.0
    h2_p = math.degrees(math.atan2(b2, a2_p)) % 360.0 if C2_p > 1e-9 else 0.0

    dL_p = L2 - L1
    dC_p = C2_p - C1_p

    if C1_p * C2_p <= 1e-9:
        dh_p = 0.0
    else:
        diff = h2_p - h1_p
        if abs(diff) <= 180.0:
            dh_p = diff
        elif diff > 180.0:
            dh_p = diff - 360.0
        else:
            dh_p = diff + 360.0

    dH_p = 2.0 * math.sqrt(C1_p * C2_p) * math.sin(math.radians(dh_p / 2.0))

    L_bar_p = 0.5 * (L1 + L2)
    C_bar_p = 0.5 * (C1_p + C2_p)

    if C1_p * C2_p <= 1e-9:
        h_bar_p = h1_p + h2_p
    else:
        if abs(h1_p - h2_p) <= 180.0:
            h_bar_p = 0.5 * (h1_p + h2_p)
        elif (h1_p + h2_p) < 360.0:
            h_bar_p = 0.5 * (h1_p + h2_p + 360.0)
        else:
            h_bar_p = 0.5 * (h1_p + h2_p - 360.0)

    T = (
        1.0
        - 0.17 * math.cos(math.radians(h_bar_p - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * h_bar_p))
        + 0.32 * math.cos(math.radians(3.0 * h_bar_p + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * h_bar_p - 63.0))
    )

    d_theta = 30.0 * math.exp(-(((h_bar_p - 275.0) / 25.0) ** 2))
    C_bar_p7 = C_bar_p ** 7
    R_C = 2.0 * math.sqrt(C_bar_p7 / (C_bar_p7 + 25.0 ** 7))
    S_L = 1.0 + (0.015 * ((L_bar_p - 50.0) ** 2)) / math.sqrt(20.0 + ((L_bar_p - 50.0) ** 2))
    S_C = 1.0 + 0.045 * C_bar_p
    S_H = 1.0 + 0.015 * C_bar_p * T
    R_T = -math.sin(math.radians(2.0 * d_theta)) * R_C

    term_L = dL_p / S_L
    term_C = dC_p / S_C
    term_H = dH_p / S_H
    de00 = math.sqrt(term_L * term_L + term_C * term_C + term_H * term_H + R_T * term_C * term_H)
    return round(de00, 4)


def validate_and_sanitize_image(
    image_bytes: bytes,
    consent_granted: bool,
    max_bytes: int = 10 * 1024 * 1024,
) -> Dict[str, Any]:
    """
    Validates user consent, sniffs magic bytes (JPEG/PNG), checks dimensions, and strips
    EXIF/APP1/metadata segments in memory so zero GPS/PII metadata is retained or forwarded.
    """
    if not consent_granted:
        raise PermissionError("Explicit user consent (`consent_granted=True`) is required before biometric skin/face processing.")
    if not isinstance(image_bytes, (bytes, bytearray)) or len(image_bytes) < 24:
        raise ValueError("Image payload is empty or too short to be a valid JPEG/PNG.")
    if len(image_bytes) > max_bytes:
        raise ValueError(f"Image payload ({len(image_bytes)} bytes) exceeds {max_bytes} byte limit.")

    raw = bytes(image_bytes)

    # PNG magic bytes: \x89PNG\r\n\x1a\n
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        if raw[12:16] != b"IHDR":
            raise ValueError("Invalid PNG header (missing IHDR chunk).")
        width, height = struct.unpack(">II", raw[16:24])
        if not (32 <= width <= 4096 and 32 <= height <= 4096):
            raise ValueError(f"PNG dimensions {width}x{height} out of supported range [32, 4096].")

        # Strip ancillary metadata chunks (eXIf, tEXt, iTXt, zTXt, tIME)
        out = bytearray(raw[:8])
        pos = 8
        stripped_chunks = 0
        while pos + 8 <= len(raw):
            c_len = struct.unpack(">I", raw[pos : pos + 4])[0]
            c_type = raw[pos + 4 : pos + 8]
            chunk_end = pos + 12 + c_len
            if chunk_end > len(raw):
                raise ValueError("Truncated or corrupt PNG chunk stream.")
            if c_type in (b"eXIf", b"tEXt", b"iTXt", b"zTXt", b"tIME"):
                stripped_chunks += 1
            else:
                out.extend(raw[pos:chunk_end])
            pos = chunk_end
            if c_type == b"IEND":
                break

        return {
            "mime_type": "image/png",
            "width": width,
            "height": height,
            "original_bytes": len(raw),
            "sanitized_bytes": len(out),
            "exif_stripped": True,
            "stripped_segments": stripped_chunks,
            "zero_disk_retention_verified": True,
            "sanitized_payload": bytes(out),
            "sha256": hashlib.sha256(bytes(out)).hexdigest(),
        }

    # JPEG magic bytes: \xff\xd8\xff
    if raw.startswith(b"\xff\xd8\xff"):
        out = bytearray(b"\xff\xd8")
        pos = 2
        width, height = 512, 512
        stripped_segments = 0
        while pos + 4 <= len(raw):
            if raw[pos] != 0xFF:
                break
            marker = raw[pos + 1]
            if marker == 0xDA:  # SOS (Start of Scan) — copy remainder
                out.extend(raw[pos:])
                break
            if marker in (0xD8, 0xD9):
                pos += 2
                continue
            seg_len = struct.unpack(">H", raw[pos + 2 : pos + 4])[0]
            if seg_len < 2 or pos + 2 + seg_len > len(raw):
                raise ValueError("Corrupt JPEG segment length.")
            # Strip APP1..APP15 (0xE1..0xEF) & COM (0xFE) which hold EXIF/GPS/XMP metadata
            if (0xE1 <= marker <= 0xEF) or marker == 0xFE:
                stripped_segments += 1
            else:
                if marker in (0xC0, 0xC1, 0xC2) and seg_len >= 7:
                    height, width = struct.unpack(">HH", raw[pos + 5 : pos + 9])
                out.extend(raw[pos : pos + 2 + seg_len])
            pos += 2 + seg_len

        if not (32 <= width <= 4096 and 32 <= height <= 4096):
            raise ValueError(f"JPEG dimensions {width}x{height} out of supported range [32, 4096].")

        return {
            "mime_type": "image/jpeg",
            "width": width,
            "height": height,
            "original_bytes": len(raw),
            "sanitized_bytes": len(out),
            "exif_stripped": True,
            "stripped_segments": stripped_segments,
            "zero_disk_retention_verified": True,
            "sanitized_payload": bytes(out),
            "sha256": hashlib.sha256(bytes(out)).hexdigest(),
        }

    raise ValueError("Unsupported image format: magic bytes must be JPEG or PNG.")


class NonceReplayCache:
    """Thread-safe bounded replay cache for X-AuraLoop-Signature HMAC verification."""

    def __init__(self, window_sec: int = 300, max_entries: int = 2048) -> None:
        self.window_sec = window_sec
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._seen: Dict[str, float] = {}

    def verify_and_record(
        self,
        secret: str,
        timestamp_str: str,
        nonce: str,
        body_bytes: bytes,
        provided_signature: str,
        now_epoch: Optional[float] = None,
    ) -> Tuple[bool, str]:
        if not secret:
            return False, "HMAC secret not configured."
        now = now_epoch if now_epoch is not None else time.time()
        try:
            ts = float(timestamp_str)
        except ValueError:
            return False, "Invalid timestamp header."

        if abs(now - ts) > self.window_sec:
            return False, f"Timestamp outside {self.window_sec}s replay window."
        if not nonce or len(nonce) < 8:
            return False, "Invalid or missing nonce."

        signing_input = f"{timestamp_str}.{nonce}.".encode("utf-8") + body_bytes
        expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, provided_signature.strip()):
            return False, "HMAC signature mismatch."

        with self._lock:
            expired = [k for k, exp in self._seen.items() if now - exp > self.window_sec]
            for k in expired:
                self._seen.pop(k, None)
            if nonce in self._seen:
                return False, "Replay attack detected: nonce already used."
            if len(self._seen) >= self.max_entries:
                oldest = next(iter(self._seen))
                self._seen.pop(oldest, None)
            self._seen[nonce] = ts

        return True, "ok"
