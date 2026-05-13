## 1. Backend — clear adjustments endpoint

- [x] 1.1 Add `clear_adjustments_for_photos(db, project_id, photo_ids)` service function that for each photo (a) deletes the `photo_adjustments` row (or resets to defaults) (b) hard-deletes every `photo_adjustment_versions` row for that photo and removes the corresponding disk file (c) clears the `processed_paths["adjusted"]` cache entry (d) recomputes the active version selector to the latest non-archived AI version or original, all within a per-photo DB transaction (disk delete is best-effort post-commit, log on failure)
- [x] 1.2 Add `ClearAdjustmentsRequest` Pydantic schema (body: `photo_ids: list[UUID]`) and `ClearAdjustmentsResponse` (response: `cleared_count: int`, `photos: list[PhotoOut]`)
- [x] 1.3 Add `POST /projects/{project_id}/adjustments/clear` route in `api/routers/adjustments.py` calling the service function and returning the response schema
- [x] 1.4 Handle mixed-state: photos that have no manual adjustments are no-op and not counted in `cleared_count`; not an error
- [x] 1.5 Pure-function unit tests in `tests/test_adjustments_clear.py` covering: full-clear path, mixed-state, archived rows excluded from active version recompute, original fallback when no AI version exists
- [x] 1.6 Document the new endpoint contract in design.md is enough; do not add a new ADR (no architectural decision here)

## 2. Frontend — vocabulary rename (no logic change)

- [x] 2.1 `web/src/components/PipelinePanel.tsx`: rename action button label `開始產生` → `開始 AI 處理已選 N 張` (use selected count)
- [x] 2.2 `web/src/components/AdjustmentPanel.tsx`: rename `產生目前版本` → `套用微調到目前照片`
- [x] 2.3 `web/src/components/AdjustmentPanel.tsx`: rename `產生已選版本` → `套用微調到已選照片`
- [x] 2.4 `web/src/components/AdjustmentPanel.tsx`: rename `重設` → `清空目前照片的微調`
- [x] 2.5 `web/src/components/AdjustmentPanel.tsx`: add new button `清空已選照片的微調` next to 2.4 (action wired in section 5)
- [x] 2.6 `web/src/pages/Upload.tsx`: rename section title `色調風格` → `AI 色調風格` and rewrite the hint text per design `docs/superpowers/specs/2026-05-13-preset-ux-redesign-design.md` §4.6
- [x] 2.7 Add inline hint text below each state-changing button (apply / clear / start AI / delete preset) per `ai-batch-vocabulary` spec scenarios
- [x] 2.8 Run `npm run build` and `npm run lint` after the rename pass — no logic change should mean no test regressions

## 3. Frontend — PhotoCard version chip component

- [x] 3.1 Create `web/src/components/PhotoVersionChip.tsx` that takes a photo's current AI version + manual version + version count and renders two color-coded chips (AI = `#7aa8d8`, manual = `#d8a87a`) plus a `▼ N 個版本` entry
- [x] 3.2 Handle empty states per `photo-version-display` spec: "無手動" chip when no manual version selected, "原圖" chip + "尚未處理" when neither AI nor manual exists
- [x] 3.3 Exclude `archived_at != null` versions from the count and from the dropdown (AI archive only; manual versions are now hard-deleted by clear flow)
- [x] 3.4 Wire `PhotoVersionChip` into `web/src/components/PhotoGrid.tsx` photo card layout above the existing version dropdown (kept dropdown for switching, chips for status)
- [x] 3.5 Style additions in `PhotoVersionChip.css` consistent with existing tokens.css (warm-near-black + champagne gold + AI/manual accent colors)

## 4. Frontend — BeforeAfter header source chain

- [x] 4.1 Source chain builder lives in `web/src/utils/photoSourceChain.ts` (not BeforeAfter — kept BeforeAfter as a pure swipe widget); header rendered in Preview.tsx
- [x] 4.2 `topSliderDeviations` helper computes top-3 absolute slider deviations, formatted as `對比 +25` etc.
- [x] 4.3 Source chain rendered in section header `mono` meta line; slider summary rendered as separate `<p className="preview-compare__slider-summary mono">` below the header
- [x] 4.4 Responsive CSS: below 600px breakpoint, `.preview-compare__slider-summary` is hidden (only version layers in header line)
- [ ] 4.5 Pure-function tests deferred — `web/` has no test runner yet (no vitest / jest); build serves as the regression gate. Listed in design.md §8 as a known gap; `add-frame-test-harness` (already a backlog change) can pull FE testing later

## 5. Frontend — clear adjustments action wiring

- [x] 5.1 Add `clearPhotoAdjustments(projectId, photoIds)` in `web/src/api/client.ts` calling `POST /projects/{id}/adjustments/clear`
- [x] 5.2 Wire `清空目前照片的微調` button onClick to `clearPhotoAdjustments(projectId, [activePhotoId])` with optimistic UI update + reload on success
- [x] 5.3 Wire `清空已選照片的微調` button onClick to `clearPhotoAdjustments(projectId, Array.from(selected))` (with `window.confirm`)
- [x] 5.4 Toast on success: `已清空 X 張照片的微調`; if `cleared_count` < selected count, append `（Y 張本來就沒微調，已略過）`
- [x] 5.5 On success, re-fetch project; FE version selector falls back automatically via existing `selectedPhotoVersion` logic since manual versions and `processed_paths["adjusted"]` are now gone

## 6. Frontend — Preset management modal

- [x] 6.1 Create `web/src/components/PresetManagerModal.tsx` with list of presets + per-row 「刪除」 button (「重新命名」 deferred — listed in design.md §8 open questions)
- [x] 6.2 Replace `刪除 preset...` dropdown in AdjustmentPanel with 「⚙ 管理」 button that opens modal
- [x] 6.3 Disclaimer rendered prominently at top of modal body with gold-soft accent panel
- [x] 6.4 Delete uses `window.confirm` per design Decision 1 (template-only delete, no cascade)
- [x] 6.5 Modal re-uses `presets` state from Preview.tsx; deletePreset already calls reloadPresets which refreshes; modal lives in `presets` state directly so refresh is automatic on close
- [x] 6.6 Styled in `PresetManagerModal.css` using tokens.css variables

## 7. Verification and release

- [x] 7.1 Run `pytest tests/` (full backend suite) — 91 passed
- [x] 7.2 Run `npm run build` and `npm run lint` — both green
- [ ] 7.3 Smoke test on local dev: full flow (upload → AI process → load preset → apply → clear → delete preset) — pending user / staging verification
- [x] 7.4 Update ROADMAP.md with v0.5.0 ship entry under the appropriate phase heading
- [x] 7.5 Bump app version: `api/main.py`, `web/src/version.ts`, `web/package.json`, `pyproject.toml`, `.github/workflows/deploy-dev.yml:EXPECTED_APP_VERSION` to `0.5.0`
- [x] 7.6 Commit with `feat: redesign preset and adjustment UX (v0.5.0)` and the Co-Authored-By line; push to main (commit `1620142`)
- [ ] 7.7 Watch CI/CD workflows: docker-publish then deploy-dev; verify `/api/health` returns `version=0.5.0`
- [ ] 7.8 Production smoke test on `https://frame.sisihome.org`: full flow + verify mobile BeforeAfter header fallback works
- [x] 7.9 Update CLAUDE.md with v0.5.0 operational invariants (preset = template, clear = hard delete, vocabulary split, state visibility, action consequence hints)
- [ ] 7.10 Archive this OpenSpec change via `openspec-archive-change` workflow
