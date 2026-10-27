# Devpost Submission Draft — YouCam API: Skin AI & eCommerce VTO Hackathon (`04-youcam-vto`)

- **Devpost URL**: https://youcam-api-skin-ai-ecommerce.devpost.com/
- **Submission Deadline (JST)**: `2026-11-01T12:45:00+09:00`
- **Project Name**: AuraLoop VTO: Agentic 14-Metric Skin AI & Omnichannel Try-On Concierge
- **Elevator Pitch**: Privacy-first 14-metric YouCam Skin AI diagnostics, CIEDE2000 shade & apparel harmony matching, contraindication-safe skincare regimen engine, and chained Makeup + Clothes VTO.
- **Target GitHub Repository URL**: `https://github.com/cal29292929/auraloop-vto`
- **Target GitHub Release URL**: `https://github.com/cal29292929/auraloop-vto/releases/tag/v1.0.0`
- **Demo Video**: `/workspace/hackathons/04-youcam-vto/submission_assets/demo_video.mp4` (1920x1080, 150s, H.264/AAC)
- **Unit Test Suite**: `8 passed`

## Built With Tags
- `perfect-corp-youcam-api`
- `cielab-ciede2000`
- `model-context-protocol`
- `python`

## Try It Out URLs
- https://github.com/cal29292929/auraloop-vto
- https://github.com/cal29292929/auraloop-vto/releases/tag/v1.0.0

## About the Project (Copy-Paste Ready for Devpost)

## Inspiration
Online beauty and fashion shoppers struggle to connect skin health diagnostics with foundation shade selection and outfit color harmony—while raw selfie uploads often leak EXIF GPS metadata and burn API credits on unvalidated images.

## What it does
**AuraLoop VTO** is an end-to-end 6-stage Skin AI & Virtual Try-On concierge:
1. **In-Memory EXIF Stripping & Quality Pre-Check**: Strips all EXIF/GPS metadata in memory before any YouCam S3 presigned upload.
2. **Thread-Safe Atomic 1,000-Unit Credit Ledger**: Tracks `units_reserved` and `units_spent` across `skin_analysis`, `skin_tone`, `makeup_vto`, and `apparel_vto`, marking timed-out non-idempotent POSTs as `unknown_submission` rather than double-charging.
3. **CIEDE2000 Perceptual Shade Matching & Barrier Safety Gate**: Computes exact $\Delta E_{00}$ color distance in CIELAB space and filters out retinoids/AHA/BHA when skin barrier sensitivity (`redness` / `moisture`) exceeds safe thresholds.

## How we built it
Architected with Claude Opus 5.5 (`DESIGN_OPUS55.md`), audited by OpenAI GPT-5.6 Luna (`REVIEW_LUNA56.md` & `CODE_REVIEW_LUNA56.md`), and implemented via Sakura AI Engine `preview/Kimi-K2.7-Code` (`auraloop_vto/`).

## Verification & Testing
- **Unit Tests**: `8 passed` (`pytest -q`)
- **Demo Video**: `submission_assets/demo_video.mp4` (1920x1080, 150s, H.264/AAC)


## Multi-Model Pipeline Provenance & Custom Questions
```json
{
  "youcam_promo_code": "YOUCAMHACK2609a",
  "opus55_session_id": "3048c208-91fc-449d-8c10-ae7b52b6c449",
  "luna56_review_session_id": "01a17da5-425d-75c0-a350-505ae54a9d55",
  "luna56_codereview_session_id": "01a17db7-4144-7b83-ae4b-c3996bd4b175",
  "sakura_completion_ids": [
    "chatcmpl-9206fbc5df5e2583",
    "chatcmpl-ad1318e7e5a69da6"
  ]
}
```

## Screenshots (1920x1080 PNG)
- `/workspace/hackathons/04-youcam-vto/submission_assets/00_thumbnail.png`
- `/workspace/hackathons/04-youcam-vto/submission_assets/01_six_stage_vto_pipeline.png`
- `/workspace/hackathons/04-youcam-vto/submission_assets/02_privacy_exif_and_budget_ledger.png`
- `/workspace/hackathons/04-youcam-vto/submission_assets/03_ciede2000_color_science.png`
- `/workspace/hackathons/04-youcam-vto/submission_assets/04_chained_vto_and_fallback.png`
- `/workspace/hackathons/04-youcam-vto/submission_assets/05_validated_omnichannel_cart.png`
- `/workspace/hackathons/04-youcam-vto/submission_assets/06_multi_model_audit_and_tests.png`
