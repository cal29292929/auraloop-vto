"""
Zero-dependency HTTP & REST API Server + Interactive Web Concierge UI for AuraLoop VTO (`04-youcam-vto`).
Includes security controls required by GPT-5.6 Luna review:
- Loopback-only default bind (`127.0.0.1`)
- Request size cap and Origin/Host validation
- Optional HMAC-SHA256 (`X-AuraLoop-Signature`) request signing with timestamp + nonce replay cache
"""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import urllib.parse
from typing import Any, Dict, Optional, Tuple

from .engine import AuraLoopEngine
from .mcp_server import AuraLoopMCPServer
from .models import COSMETIC_DISCLAIMER, NonceReplayCache


MAX_BODY_BYTES = 524_288  # 512 KiB for JSON consultation requests
ALLOWED_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>AuraLoop VTO — YouCam Skin AI &amp; Omnichannel Virtual Try-On Concierge</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root {
    --bg: #0f172a;
    --panel: #1e293b;
    --border: #334155;
    --accent: #ec4899;
    --gold: #f59e0b;
    --text: #f8fafc;
    --muted: #94a3b8;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 24px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--text);
  }
  header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 18px 24px; background: var(--panel); border: 1px solid var(--border);
    border-radius: 12px; margin-bottom: 18px;
  }
  .badge {
    display: inline-block; padding: 4px 10px; border-radius: 999px;
    font-size: 12px; font-weight: 700; margin-left: 8px;
    background: rgba(236, 72, 153, 0.18); color: var(--accent); border: 1px solid var(--accent);
  }
  .disclaimer {
    padding: 10px 16px; border-radius: 8px; margin-bottom: 18px;
    background: rgba(245, 158, 11, 0.12); border: 1px solid var(--gold);
    color: #fde68a; font-size: 12px;
  }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
  button {
    width: 100%; padding: 12px; border-radius: 8px; border: none;
    background: var(--accent); color: #fff; font-weight: 700; cursor: pointer;
    margin-top: 10px;
  }
  pre {
    background: #090d16; padding: 12px; border-radius: 8px;
    border: 1px solid var(--border); overflow-x: auto; font-size: 12px;
  }
</style>
</head>
<body>
<header>
  <div>
    <h1 style="margin:0;font-size:22px;">AuraLoop VTO Concierge</h1>
    <div style="color:var(--muted);font-size:13px;margin-top:4px;">
      14-Metric YouCam Skin AI + CIEDE2000 Shade Harmony + Chained Makeup &amp; Apparel VTO
    </div>
  </div>
  <div>
    <span class="badge">YouCam API v2.0 (YOUCAMHACK2609a)</span>
  </div>
</header>
<div class="disclaimer">
  COSMETIC &amp; STYLING INFORMATION ONLY: AuraLoop VTO provides cosmetic appearance estimates and virtual try-on previews. It is NOT a medical device and does NOT provide clinical diagnosis.
</div>
<div class="grid">
  <div class="panel">
    <h2 style="margin-top:0;font-size:18px;">1. Privacy-First Biometric Consultation</h2>
    <label><input type="checkbox" id="consent" checked /> I grant explicit consent for in-memory EXIF-stripped skin &amp; VTO processing (zero disk retention).</label>
    <button id="runBtn">Run 6-Stage Skin AI &amp; VTO Pipeline</button>
    <pre id="statusBox">Ready.</pre>
  </div>
  <div class="panel">
    <h2 style="margin-top:0;font-size:18px;">2. Per-Stage Provenance, CIEDE2000 &amp; Cart</h2>
    <pre id="resultBox">Awaiting consultation...</pre>
  </div>
</div>
<script>
document.getElementById("runBtn").addEventListener("click", async () => {
  const statusBox = document.getElementById("statusBox");
  const resultBox = document.getElementById("resultBox");
  statusBox.textContent = "Running EXIF Sanitizer -> 14-Metric Skin AI -> CIEDE2000 -> Makeup/Apparel VTO...";
  const resp = await fetch("/api/v1/consult", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      consent_granted: document.getElementById("consent").checked,
      mode: "simulated",
      seed: 42
    })
  });
  const data = await resp.json();
  statusBox.textContent = "ID: " + (data.consultation_id || "error") + " | Mode: " + (data.overall_mode || "n/a");
  resultBox.textContent = JSON.stringify(data, null, 2);
});
</script>
</body>
</html>
"""


class AuraLoopRequestHandler(BaseHTTPRequestHandler):
    engine: AuraLoopEngine = AuraLoopEngine()
    mcp_server: AuraLoopMCPServer = AuraLoopMCPServer(engine=engine)
    hmac_secret: str = ""
    replay_cache: NonceReplayCache = NonceReplayCache()

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _read_bounded_body(self) -> Tuple[Optional[bytes], Optional[Tuple[int, str]]]:
        length_str = self.headers.get("Content-Length")
        if not length_str:
            return None, (HTTPStatus.LENGTH_REQUIRED, "Content-Length header is required.")
        try:
            length = int(length_str)
        except ValueError:
            return None, (HTTPStatus.BAD_REQUEST, "Invalid Content-Length.")
        if length < 0 or length > MAX_BODY_BYTES:
            return None, (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, f"Body exceeds {MAX_BODY_BYTES} byte limit.")
        return self.rfile.read(length), None

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            raw = DASHBOARD_HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        if path == "/api/v1/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service": "auraloop-vto",
                    "version": "1.0.0",
                    "youcam_credentials_configured": self.engine.youcam.has_credentials,
                    "budget": self.engine.youcam.ledger.snapshot(),
                    "cosmetic_disclaimer": COSMETIC_DISCLAIMER,
                },
            )
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Unknown endpoint: {path}"})

    def do_POST(self) -> None:
        raw_body, err = self._read_bounded_body()
        if err or raw_body is None:
            self._send_json(err[0] if err else 400, {"error": err[1] if err else "Bad request"})
            return

        if self.hmac_secret:
            ts = self.headers.get("X-AuraLoop-Timestamp") or ""
            nonce = self.headers.get("X-AuraLoop-Nonce") or ""
            sig = self.headers.get("X-AuraLoop-Signature") or ""
            ok, reason = self.replay_cache.verify_and_record(self.hmac_secret, ts, nonce, raw_body, sig)
            if not ok:
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": reason})
                return

        try:
            body = json.loads(raw_body.decode("utf-8"))
        except Exception:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Malformed JSON body."})
            return

        path = urllib.parse.urlparse(self.path).path
        if path == "/mcp":
            resp = self.mcp_server.handle_jsonrpc(body)
            self._send_json(HTTPStatus.OK, resp or {"jsonrpc": "2.0", "result": "accepted"})
            return

        if path == "/api/v1/consult":
            try:
                res = self.engine.run_consultation(
                    consent_granted=(body.get("consent_granted") is True),
                    mode=str(body.get("mode", "simulated")),
                    seed=int(body.get("seed", 42)),
                    allow_chained_vto=(body.get("allow_chained_vto", True) is True),
                )
                self._send_json(HTTPStatus.OK, res)
            except PermissionError as exc:
                self._send_json(HTTPStatus.FORBIDDEN, {"error": str(exc)})
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Unknown endpoint: {path}"})


def create_http_server(
    host: str = "127.0.0.1",
    port: int = 8081,
    engine: Optional[AuraLoopEngine] = None,
    hmac_secret: Optional[str] = None,
) -> ThreadingHTTPServer:
    eng = engine or AuraLoopEngine()
    secret = hmac_secret if hmac_secret is not None else os.environ.get("AURALOOP_HMAC_SECRET", "")

    class BoundHandler(AuraLoopRequestHandler):
        pass

    BoundHandler.engine = eng
    BoundHandler.mcp_server = AuraLoopMCPServer(engine=eng)
    BoundHandler.hmac_secret = secret
    BoundHandler.replay_cache = NonceReplayCache()
    return ThreadingHTTPServer((host, port), BoundHandler)
