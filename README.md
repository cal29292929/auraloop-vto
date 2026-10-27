# AuraLoop VTO — Agentic 14-Metric Skin AI & Omnichannel Virtual Try-On Concierge

> **Built for the [YouCam API: Skin AI & eCommerce VTO Hackathon](https://youcam-api-skin-ai-ecommerce.devpost.com/) (October–November 2026)**
> **Powered by**: Perfect Corp. YouCam API v2.0 (`YOUCAMHACK2609a` — 1,000 API Units)
> **Author**: Kazutoshi Hayashi (`cal29292929`) | **License**: MIT

---

## 1. Overview & Problem Solved

Online beauty and fashion shoppers face a **42%+ shade & fit return rate** because skin analysis tools, makeup try-on widgets, and apparel virtual try-on operate in isolated silos—and often recommend harsh active ingredients (retinoids/AHAs) even when the user's skin barrier shows elevated redness or dehydration.

**AuraLoop VTO** unifies **Perfect Corp. YouCam API v2.0** into a 6-stage agentic eCommerce concierge:
1. **Privacy-First In-Memory EXIF Sanitizer & Consent Gate (`validate_and_sanitize_image`)**: Enforces explicit biometric consent (`consent_granted=True`), verifies JPEG/PNG magic bytes and dimensions, and strips EXIF/APP1/GPS/XMP and PNG `eXIf`/`tEXt` metadata in memory (`zero_disk_retention_verified=True`).
2. **14-Metric AI Skin Analysis (`skin_analysis`)**: Evaluates moisture, oiliness, redness, texture, pores, wrinkles, acne, dark spots, radiance, firmness, dark circles, eye bags, and upper/lower eyelid droopiness.
3. **Pure-Python CIELAB & CIEDE2000 ($\Delta E_{00}$) Color Science (`skin_tone`)**: Converts detected skin tone sRGB (`#RRGGBB`) via linear RGB and CIE XYZ (D65) into CIELAB ($L^*, a^*, b^*$) and ranks foundation shades and seasonal apparel palettes using perceptual $\Delta E_{00}$.
4. **Chained & Side-by-Side Omnichannel Virtual Try-On (`makeup_vto` + `apparel_vto`)**: Renders foundation/lip VTO and chains into apparel VTO (with automatic side-by-side composite fallback when chained VTO is unavailable).
5. **Contraindication-Aware Regimen Engine (`regimen_engine`)**: Automatically suppresses high-irritation retinoid/AHA SKUs when redness or moisture scores indicate barrier sensitivity.
6. **Thread-Safe Atomic `UnitBudgetLedger` & Validated `CartBuilder`**: Protects the 1,000-unit hackathon credit allowance (`hard_ceiling=950`) with `reserve`, `commit`, `rollback`, and `mark_unknown_submission` (never blind-retrying non-idempotent POST timeouts), and outputs a validated omnichannel cart with mandatory cosmetic-only (non-medical) disclaimers.

---

## 2. Quickstart (< 5 Seconds, Zero External Dependencies)

```bash
# Run full unit test suite and generate consultation artifacts
./run_demo.sh

# Start the local Web Concierge & REST/MCP Server (loopback 127.0.0.1:8081)
python3 -m auraloop_vto.cli serve --host 127.0.0.1 --port 8081

# Run as a JSON-RPC 2.0 Model Context Protocol (MCP) stdio server
python3 -m auraloop_vto.cli mcp
```
