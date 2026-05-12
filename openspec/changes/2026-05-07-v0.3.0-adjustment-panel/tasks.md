# Tasks — v0.3.0 Adjustment Panel

## Immediate Preview Fixes

- [x] Make `showroom_white` neutral/cooler instead of warmer than original.
- [x] Clicking a photo card updates the top before/after preview to that photo.
- [x] Add individual processed JPG download on each photo card.

## Backend

- [x] Add `services/adjustments.py` for exposure, contrast, highlights, shadows, temp/tint, saturation, vibrance, clarity, sharpness, and HSL.
- [x] Add `PhotoAdjustment` model and migration for per-photo adjustment params.
- [x] Add `AdjustmentPreset` model and migration for saved presets.
- [x] Add preview endpoint returning debounced small JPEG previews.
- [x] Add apply endpoint for current photo.
- [x] Add apply-to-selected support in the frontend by applying each selected photo.
- [x] Update export path priority to adjusted output, latest completed AI version, processed preset cache, then original.
- [x] Add vibrance, clarity, and sharpness controls.
- [x] Add manual level, crop zoom/offset, and distortion controls.
- [x] Add per-photo one-click left/right 90-degree rotation with immediate preview update.
- [x] Persist per-photo draft adjustment state separately from generated versions.
- [x] Create downloadable manual versions only when the user presses generate/apply.
- [x] Add per-photo version download selection.
- [x] Add visual geometry editor window with crop frame and live preview.
- [x] Move apply-to-selected into worker progress for large batches.
- [x] Keep manual geometry/crop corrections on non-AI path.

## Frontend

- [x] Build AdjustmentPanel with Light, Color, and HSL groups.
- [x] Build saved preset load/save/delete UI.
- [x] Support one-click apply to all selected photos.
- [x] Support per-photo independent overrides after apply-all.
- [x] Keep top BeforeAfter in sync with active photo selection.
- [x] Keep per-photo processed download visible after render.
- [x] Make photo-card version dropdown switch the tile image, active preview base, adjustment base, and download target.
- [x] Rename visible version labels to user-facing wording and hide raw internal state names.
- [x] Make top Before/After a large editing workspace on desktop and mobile.
- [x] Make live preview render from a resized preview image before manual adjustments so rotation/color changes are immediate.
- [x] Increase manual warmth/tint feedback enough to be visible in mobile preview.
- [x] Replace the geometry two-column modal with a full-screen single-photo editor with grid overlay and cancel/done controls.
- [x] Make the geometry crop frame draggable/resizable and split manual perspective into horizontal/vertical controls with live transform preview.
- [x] Default pipeline settings to medium denoise, lens correction off, level correction off, original crop ratio.
- [x] Warn when Before/After is showing manual preview before AI denoise has been generated.
- [x] Strengthen heavy denoise when NAFNet is conservative or unavailable.
- [x] Strengthen medium denoise so the default pipeline is visibly cleaner when NAFNet is conservative or unavailable.
- [x] Make heavy denoise edge-aware so flat regions stay clean without erasing architecture detail.
- [x] Add a low-light portrait regression for clean dark backgrounds without oil-painting face/hair/clothing detail.
- [x] Auto-start default batch generation for missing preset outputs while keeping Before as the original.
- [x] Add post-denoise detail restoration for medium/heavy outputs.
- [x] Add automatic vertical perspective correction to the lens correction toggle.
- [x] Move the primary batch start action below the manual adjustment section.
- [x] Sync Upload-selected style into Preview pipeline settings and automatic batch generation.
- [x] Add a sticky Preview action summary so the primary batch start action stays visible and is disabled while a job is running.
- [x] Add previous/next controls inside the Before/After comparison viewer so users can review adjacent photos without scrolling back to the grid.
- [x] Document Preview UX audit findings and follow-up priorities in `docs/preview-ux-audit.md`.
- [ ] Validate mobile layout on iPhone Safari.

## Verification

- [ ] Smoke test with real photos for showroom white neutrality.
- [x] Smoke test live preview and manual geometry apply correctness.
- [ ] Verify individual processed downloads.
- [x] Run frontend build/typecheck and backend lint/compile.
- [x] Smoke test preview/apply/preset endpoints with vibrance, clarity, and sharpness payload.
- [x] Update docs, commit, and push.
