# Devpost Submission Draft — YouCam API: Skin AI & eCommerce VTO Hackathon

- **Hackathon URL**: https://youcam-api-skin-ai-ecommerce.devpost.com/
- **Submission Target**: `2026-11-01 12:45 JST` (Official Devpost deadline: `2026-11-02 08:45 AM PDT` / `2026-11-03 01:45 JST`)
- **Project Title**: AuraLoop VTO: Agentic 14-Metric Skin AI & Omnichannel Try-On Concierge
- **Tagline**: Privacy-first 14-metric YouCam Skin AI diagnostics, CIEDE2000 shade & apparel harmony matching, contraindication-safe skincare regimen engine, and chained Makeup + Clothes VTO.

## Built With
- `perfect-corp-youcam-api` (`v2.0`, Promo Code `YOUCAMHACK2609a`)
- `cielab-ciede2000`
- `model-context-protocol` (`MCP 2025-06-18`)
- `python`

## Key Highlights for Judges
1. **End-to-End 6-Stage Per-Stage Provenance**: Explicitly tracks `provider`, `mode` (`live`/`simulated`), `status`, `units_reserved`, and `units_spent` across `skin_analysis`, `skin_tone`, `makeup_vto`, `apparel_vto`, `regimen_engine`, and `cart_builder`.
2. **Thread-Safe Atomic 1,000-Unit Budget Ledger**: Prevents credit exhaustion and avoids double-charging on non-idempotent POST timeouts via `mark_unknown_submission`.
3. **CIEDE2000 Perceptual Color Matching + Barrier Safety Gate**: Pairs mathematical $\Delta E_{00}$ shade matching with dermatological contraindication filtering and in-memory EXIF stripping.
