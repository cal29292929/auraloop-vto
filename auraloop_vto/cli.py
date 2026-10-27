"""
CLI entrypoint for AuraLoop VTO (`auraloop_vto.cli`):
- `demo`: Runs full 6-stage consultation and writes `artifacts/latest_consultation.json` & `.md`
- `serve`: Starts local Web Concierge & REST/MCP server
- `mcp`: Runs stdio JSON-RPC 2.0 MCP server
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import List, Optional

from .engine import AuraLoopEngine
from .mcp_server import run_stdio_server
from .server import create_http_server


def render_consultation_markdown(data: dict) -> str:
    sa = data["skin_analysis"]
    cs = data["color_science"]
    pa = data["privacy_audit"]
    cart = data["cart"]
    ledger = data["unit_budget_ledger"]

    lines = [
        f"# AuraLoop VTO Consultation Report — `{data['consultation_id']}`",
        "",
        f"> **{data['cosmetic_disclaimer']}**",
        "",
        f"- **Timestamp (JST)**: `{data['created_at_jst']}`",
        f"- **Overall Mode / Status**: `{data['overall_mode']}` / `{data['overall_status']}`",
        f"- **Privacy & EXIF Audit**: `consent_granted={pa['consent_granted']}`, `exif_stripped={pa['exif_stripped']}` (Stripped `{pa['stripped_metadata_segments']}` metadata segment(s)), `zero_disk_retention={pa['zero_disk_retention_verified']}`",
        f"- **YouCam Credit Ledger (`{ledger['promo_code']}`)**: `{ledger['committed_units']}` committed / `{ledger['remaining_safe_units']}` safe remaining (Hard ceiling `{ledger['hard_ceiling']}/{ledger['total_units']}`)",
        "",
        "## 1. Per-Stage Execution Provenance",
        "",
        "| Stage | Provider | Mode | Status | Units (Res/Spent) | Duration (ms) | Degraded Reason |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]
    for s_name, prov in data["stage_provenance"].items():
        lines.append(
            f"| `{s_name}` | `{prov['provider']}` | `{prov['mode']}` | **{prov['status']}** | "
            f"{prov['units_reserved']}/{prov['units_spent']} | {prov['duration_ms']:.1f} | {prov['degraded_reason'] or 'None'} |"
        )

    lines.extend(
        [
            "",
            "## 2. 14-Metric Skin AI & CIEDE2000 Color Science",
            "",
            f"- **Overall Skin Score**: `{sa['overall_score']}` (Estimated Skin Age: `{sa['skin_age_estimate']}`)",
            f"- **Detected Skin Tone**: `{cs['skin_tone_hex']}` (`CIELAB = {cs['skin_tone_cielab']}`, Undertone: `{sa['undertone']}`, Palette: `{sa['seasonal_palette']}`)",
            f"- **Foundation Shade Match**: `{cs['matched_foundation_sku']}` ($\\Delta E_{{00}} = {cs['foundation_ciede2000_delta_e']:.4f}$)",
            f"- **Apparel Harmony Match**: `{cs['matched_apparel_sku']}` ($\\Delta E_{{00}} = {cs['apparel_ciede2000_delta_e']:.4f}$)",
            "",
            "## 3. Contraindication-Aware Regimen & Suppressed Actives",
            "",
            f"- **Barrier Sensitivity Detected**: `{data['regimen']['barrier_sensitivity_detected']}`",
        ]
    )
    for sup in data["regimen"]["suppressed_contraindicated_skus"]:
        lines.append(f"- **Suppressed `{sup['sku_id']}` ({sup['name']})**: {sup['reason']}")

    lines.extend(
        [
            "",
            "## 4. Validated Omnichannel Shopping Cart",
            "",
            "| SKU | Category | Product Name | Qty | Unit Price | Rationale |",
            "| :--- | :---: | :--- | :-: | :---: | :--- |",
        ]
    )
    for item in cart["line_items"]:
        lines.append(
            f"| `{item['sku_id']}` | `{item['category']}` | {item['name']} | {item['quantity']} | "
            f"${item['unit_price_usd']:.2f} | {item['rationale']} |"
        )
    lines.extend(
        [
            "",
            f"- **Subtotal**: `${cart['subtotal_usd']:.2f}` | **Bundle Discount (10%)**: `-${cart['bundle_discount_usd']:.2f}` | **Total**: **`${cart['total_usd']:.2f} {cart['currency']}`**",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="auraloop-vto", description="AuraLoop VTO CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_demo = sub.add_parser("demo", help="Run 6-stage Skin AI & VTO pipeline and save artifacts")
    p_demo.add_argument("--mode", choices=["simulated", "hybrid", "live"], default="simulated")
    p_demo.add_argument("--seed", type=int, default=42)
    p_demo.add_argument("--out-dir", default="artifacts")

    p_serve = sub.add_parser("serve", help="Start HTTP Web Concierge & REST/MCP server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8081)

    sub.add_parser("mcp", help="Run stdio JSON-RPC 2.0 MCP server")

    args = parser.parse_args(argv)
    engine = AuraLoopEngine()

    if args.cmd == "mcp":
        run_stdio_server()
        return 0

    if args.cmd == "serve":
        srv = create_http_server(host=args.host, port=args.port, engine=engine)
        print(f"AuraLoop VTO Concierge listening on http://{args.host}:{args.port}")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            srv.server_close()
        return 0

    if args.cmd == "demo":
        res = engine.run_consultation(consent_granted=True, mode=args.mode, seed=args.seed)
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "latest_consultation.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        (out_dir / "latest_consultation.md").write_text(render_consultation_markdown(res), encoding="utf-8")
        print(
            json.dumps(
                {
                    "consultation_id": res["consultation_id"],
                    "overall_mode": res["overall_mode"],
                    "total_usd": res["cart"]["total_usd"],
                },
                indent=2,
            )
        )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
