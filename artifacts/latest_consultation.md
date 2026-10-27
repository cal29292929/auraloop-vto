# AuraLoop VTO Consultation Report — `aura-92f7a92112e8`

> **COSMETIC & STYLING INFORMATION ONLY: AuraLoop VTO provides cosmetic appearance estimates and virtual try-on previews. It is NOT a medical device and does NOT provide dermatological or clinical diagnosis.**

- **Timestamp (JST)**: `2026-10-27T23:16:03+09:00`
- **Overall Mode / Status**: `simulated` / `ok`
- **Privacy & EXIF Audit**: `consent_granted=True`, `exif_stripped=True` (Stripped `1` metadata segment(s)), `zero_disk_retention=True`
- **YouCam Credit Ledger (`YOUCAMHACK2609a`)**: `0` committed / `950` safe remaining (Hard ceiling `950/1000`)

## 1. Per-Stage Execution Provenance

| Stage | Provider | Mode | Status | Units (Res/Spent) | Duration (ms) | Degraded Reason |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `skin_analysis` | `auraloop_sim` | `simulated` | **ok** | 0/0 | 12.4 | None |
| `skin_tone` | `local_engine` | `simulated` | **ok** | 0/0 | 1.9 | None |
| `makeup_vto` | `auraloop_sim` | `simulated` | **ok** | 0/0 | 18.2 | None |
| `apparel_vto` | `auraloop_sim` | `simulated` | **ok** | 0/0 | 24.5 | None |
| `regimen_engine` | `local_engine` | `simulated` | **ok** | 0/0 | 1.2 | None |
| `cart_builder` | `local_engine` | `simulated` | **ok** | 0/0 | 1.0 | None |

## 2. 14-Metric Skin AI & CIEDE2000 Color Science

- **Overall Skin Score**: `73.1` (Estimated Skin Age: `26`)
- **Detected Skin Tone**: `#E3B998` (`CIELAB = [78.0508, 10.4966, 22.4579]`, Undertone: `warm_neutral`, Palette: `Warm Autumn`)
- **Foundation Shade Match**: `SKU-MKP-01` ($\Delta E_{00} = 0.7818$)
- **Apparel Harmony Match**: `SKU-APP-01` ($\Delta E_{00} = 7.9724$)

## 3. Contraindication-Aware Regimen & Suppressed Actives

- **Barrier Sensitivity Detected**: `True`
- **Suppressed `SKU-SKN-03` (Retinaldehyde 0.1% + AHA Resurfacing Night Peel)**: Suppressed high-potency retinoid/AHA exfoliant due to elevated redness/barrier sensitivity (redness=50, moisture=57).

## 4. Validated Omnichannel Shopping Cart

| SKU | Category | Product Name | Qty | Unit Price | Rationale |
| :--- | :---: | :--- | :-: | :---: | :--- |
| `SKU-SKN-01` | `skincare` | Ceramide + 5% Panthenol Barrier Cloud Serum | 1 | $38.00 | Targeted AM/PM barrier & radiance support for moisture, redness. |
| `SKU-SKN-02` | `skincare` | Niacinamide 10% + Zinc Pore & Radiance Essence | 1 | $34.00 | Targeted AM/PM barrier & radiance support for oiliness, pores, radiance, dark_circles. |
| `SKU-MKP-01` | `makeup` | Silk Serum Foundation — 220 Warm Honey | 1 | $42.00 | CIEDE2000 ΔE00=0.78 match to skin tone #E3B998. |
| `SKU-APP-01` | `apparel` | Merino Draped Wrap Blazer — Warm Camel | 1 | $148.00 | Seasonal palette (Warm Autumn) harmony match (ΔE00=7.97). |

- **Subtotal**: `$262.00` | **Bundle Discount (10%)**: `-$26.20` | **Total**: **`$235.80 USD`**
