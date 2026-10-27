"""
JSON-RPC 2.0 Model Context Protocol (MCP) Server for AuraLoop VTO (`2025-06-18`).
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional

from .engine import AuraLoopEngine, IMMUTABLE_SKU_CATALOG
from .models import ciede2000_delta_e, srgb_hex_to_cielab


MCP_PROTOCOL_VERSION = "2025-06-18"

MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "auraloop_run_consultation",
        "description": "Execute 6-stage YouCam Skin AI & Omnichannel VTO consultation with per-stage provenance and EXIF sanitization.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "consent_granted": {"type": "boolean", "default": True},
                "mode": {"type": "string", "enum": ["simulated", "hybrid", "live"], "default": "simulated"},
                "seed": {"type": "integer", "default": 42},
                "allow_chained_vto": {"type": "boolean", "default": True},
            },
            "required": ["consent_granted"],
        },
    },
    {
        "name": "auraloop_match_shade_ciede2000",
        "description": "Compute CIELAB coordinates and rank makeup/apparel SKUs by perceptual CIEDE2000 Delta E distance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skin_hex": {"type": "string", "default": "#E3B998"},
            },
            "required": ["skin_hex"],
        },
    },
    {
        "name": "auraloop_get_budget_status",
        "description": "Inspect the thread-safe 1,000-unit YouCam API Hackathon budget ledger (`YOUCAMHACK2609a`).",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


class AuraLoopMCPServer:
    def __init__(self, engine: Optional[AuraLoopEngine] = None) -> None:
        self.engine = engine or AuraLoopEngine()

    def handle_jsonrpc(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id") if isinstance(request, dict) else None,
                "error": {"code": -32600, "message": "Invalid JSON-RPC 2.0 request."},
            }

        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params") or {}

        if method == "notifications/initialized" or (req_id is None and method.startswith("notifications/")):
            return None

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "auraloop-vto-mcp", "version": "1.0.0"},
                },
            }

        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}

        if method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments") or {}
            try:
                result_obj = self._call_tool(tool_name, args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result_obj, ensure_ascii=False)}],
                        "isError": False,
                    },
                }
            except KeyError as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {exc}"},
                }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps({"error": str(exc)}, ensure_ascii=False)}],
                        "isError": True,
                    },
                }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    def _call_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if name == "auraloop_run_consultation":
            return self.engine.run_consultation(
                consent_granted=(args.get("consent_granted") is True),
                mode=str(args.get("mode", "simulated")),
                seed=int(args.get("seed", 42)),
                allow_chained_vto=(args.get("allow_chained_vto", True) is True),
            )
        if name == "auraloop_match_shade_ciede2000":
            skin_hex = str(args.get("skin_hex", "#E3B998"))
            lab = srgb_hex_to_cielab(skin_hex)
            matches = [
                {
                    "sku_id": s.sku_id,
                    "name": s.name,
                    "category": s.category,
                    "hex_color": s.hex_color,
                    "delta_e_00": ciede2000_delta_e(lab, s.lab_color),
                }
                for s in IMMUTABLE_SKU_CATALOG
            ]
            matches.sort(key=lambda x: x["delta_e_00"])
            return {"skin_hex": skin_hex, "skin_lab": list(lab), "matches": matches}
        if name == "auraloop_get_budget_status":
            return self.engine.youcam.ledger.snapshot()
        raise KeyError(name)


def run_stdio_server() -> None:
    server = AuraLoopMCPServer()
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}) + "\n")
            sys.stdout.flush()
            continue
        resp = server.handle_jsonrpc(payload)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_server()
