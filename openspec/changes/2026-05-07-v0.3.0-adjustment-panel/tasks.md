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
- [x] Update export path priority to adjusted output, then processed preset, then original.
- [x] Add vibrance, clarity, and sharpness controls.
- [x] Add manual level, crop zoom/offset, and distortion controls.
- [x] Add per-photo one-click left/right 90-degree rotation with immediate preview update.
- [x] Move apply-to-selected into worker progress for large batches.
- [x] Keep manual geometry/crop corrections on non-AI path.

## Frontend

- [x] Build AdjustmentPanel with Light, Color, and HSL groups.
- [x] Build saved preset load/save/delete UI.
- [x] Support one-click apply to all selected photos.
- [x] Support per-photo independent overrides after apply-all.
- [x] Keep top BeforeAfter in sync with active photo selection.
- [x] Keep per-photo processed download visible after render.
- [ ] Validate mobile layout on iPhone Safari.

## Verification

- [ ] Smoke test with real photos for showroom white neutrality.
- [x] Smoke test live preview and manual geometry apply correctness.
- [ ] Verify individual processed downloads.
- [x] Run frontend build/typecheck and backend lint/compile.
- [x] Smoke test preview/apply/preset endpoints with vibrance, clarity, and sharpness payload.
- [ ] Update docs, commit, and push.
