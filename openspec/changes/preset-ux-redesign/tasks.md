## 1. Backend — clear adjustments endpoint

- [ ] 1.1 Add `clear_adjustments_for_photos(db, project_id, photo_ids)` service function that for each photo (a) resets `photo_adjustments` row to defaults (b) sets `archived_at` on every non-archived `photo_adjustment_versions` row for that photo (c) recomputes the active version selector to the latest non-archived AI version or original, all within a per-photo DB transaction
- [ ] 1.2 Add `ClearAdjustmentsRequest` Pydantic schema (body: `photo_ids: list[UUID]`) and `ClearAdjustmentsResponse` (response: `cleared_count: int`, `photos: list[PhotoOut]`)
- [ ] 1.3 Add `POST /projects/{project_id}/adjustments/clear` route in `api/routers/adjustments.py` calling the service function and returning the response schema
- [ ] 1.4 Handle mixed-state: photos that have no manual adjustments are no-op and not counted in `cleared_count`; not an error
- [ ] 1.5 Pure-function unit tests in `tests/test_adjustments_clear.py` covering: full-clear path, mixed-state, archived rows excluded from active version recompute, original fallback when no AI version exists
- [ ] 1.6 Document the new endpoint contract in design.md is enough; do not add a new ADR (no architectural decision here)

## 2. Frontend — vocabulary rename (no logic change)

- [ ] 2.1 `web/src/components/PipelinePanel.tsx`: rename action button label `開始產生` → `開始 AI 處理已選 N 張` (use selected count)
- [ ] 2.2 `web/src/components/AdjustmentPanel.tsx`: rename `產生目前版本` → `套用微調到目前照片`
- [ ] 2.3 `web/src/components/AdjustmentPanel.tsx`: rename `產生已選版本` → `套用微調到已選照片`
- [ ] 2.4 `web/src/components/AdjustmentPanel.tsx`: rename `重設` → `清空目前照片的微調`
- [ ] 2.5 `web/src/components/AdjustmentPanel.tsx`: add new button `清空已選照片的微調` next to 2.4 (action wired in section 5)
- [ ] 2.6 `web/src/pages/Upload.tsx`: rename section title `色調風格` → `AI 色調風格` and rewrite the hint text per design `docs/superpowers/specs/2026-05-13-preset-ux-redesign-design.md` §4.6
- [ ] 2.7 Add inline hint text below each state-changing button (apply / clear / start AI / delete preset) per `ai-batch-vocabulary` spec scenarios
- [ ] 2.8 Run `npm run build` and `npm run lint` after the rename pass — no logic change should mean no test regressions

## 3. Frontend — PhotoCard version chip component

- [ ] 3.1 Create `web/src/components/PhotoVersionChip.tsx` that takes a photo's current AI version + manual version + version count and renders two color-coded chips (AI = `#7aa8d8`, manual = `#d8a87a`) plus a `▼ N 個版本` entry
- [ ] 3.2 Handle empty states per `photo-version-display` spec: "無手動" chip when no manual version selected, "原圖" chip + "尚未處理" when neither AI nor manual exists
- [ ] 3.3 Exclude `archived_at != null` versions from the count and from the dropdown
- [ ] 3.4 Wire `PhotoVersionChip` into `web/src/components/PhotoGrid.tsx` photo card layout, replacing the current bare version dropdown
- [ ] 3.5 Style additions in `PhotoGrid.css` consistent with existing tokens.css (warm-near-black + champagne gold + AI/manual accent colors)

## 4. Frontend — BeforeAfter header source chain

- [ ] 4.1 In `web/src/components/BeforeAfter.tsx`, compute the source chain string from the active photo's currently selected version: `After: 手動 v<N> — 基於 AI v<M> / <preset>` or `After: AI v<M> / <preset>` or `After: 原圖`
- [ ] 4.2 Compute "top 3 most-deviated sliders" helper using absolute deviation from default; render as `· 對比 +25 / 色溫 +120 / 飽和 +5`
- [ ] 4.3 Render the source chain in the BeforeAfter header above the comparison area
- [ ] 4.4 Add responsive CSS: below mobile breakpoint, hide the per-slider summary and keep only the version layers
- [ ] 4.5 Add a snapshot test (or pure-function unit test) for the source chain builder covering: AI-only, AI+manual, original-only, mixed sliders

## 5. Frontend — clear adjustments action wiring

- [ ] 5.1 Add `clearPhotoAdjustments(projectId, photoIds)` in `web/src/api/client.ts` calling `POST /projects/{id}/adjustments/clear`
- [ ] 5.2 Wire `清空目前照片的微調` button onClick to `clearPhotoAdjustments(projectId, [activePhotoId])` with optimistic UI update + reload on success
- [ ] 5.3 Wire `清空已選照片的微調` button onClick to `clearPhotoAdjustments(projectId, Array.from(selected))`
- [ ] 5.4 Toast on success: `已清空 X 張照片的微調`; if `cleared_count` < selected count, append `（Y 張本來就沒微調，已略過）`
- [ ] 5.5 On success, re-fetch project and switch active version to the new recommended version per backend response

## 6. Frontend — Preset management modal

- [ ] 6.1 Create `web/src/components/PresetManagerModal.tsx` with list of presets, per-row 「重新命名」 (inline edit, nice-to-have, can ship empty) + 「刪除」 button
- [ ] 6.2 Add modal trigger button 「⚙ 管理」 in `AdjustmentPanel.tsx`, replacing the current 「刪除 preset...」 dropdown
- [ ] 6.3 Display the no-photo-impact disclaimer prominently in the modal body per `manual-adjustment-workflow` spec scenario
- [ ] 6.4 Confirm delete inline (or via window.confirm minimum viable) — no cascade dialog needed since Decision 1 is template-only delete
- [ ] 6.5 Re-fetch preset list on modal close
- [ ] 6.6 Style with existing tokens.css palette

## 7. Verification and release

- [ ] 7.1 Run `pytest tests/` (full backend suite) — should be green
- [ ] 7.2 Run `cd web && npm run build` and `npm run lint` — should be green
- [ ] 7.3 Smoke test on local dev: full flow (upload → AI process → load preset → apply → clear → delete preset) — verify no regression on existing AI batch / version dropdown behavior
- [ ] 7.4 Update ROADMAP.md with v0.5.0 ship entry under the appropriate phase heading
- [ ] 7.5 Bump app version: `api/main.py`, `web/src/version.ts`, `web/package.json`, `pyproject.toml`, `.github/workflows/deploy-dev.yml:EXPECTED_APP_VERSION` to `0.5.0`
- [ ] 7.6 Commit with `feat: redesign preset and adjustment UX (v0.5.0)` and the Co-Authored-By line; push to main
- [ ] 7.7 Watch CI/CD workflows: docker-publish then deploy-dev; verify `/api/health` returns `version=0.5.0`
- [ ] 7.8 Production smoke test on `https://frame.sisihome.org`: full flow + verify mobile BeforeAfter header fallback works
- [ ] 7.9 Update CLAUDE.md if any new operational invariants emerge (e.g. clear endpoint contract)
- [ ] 7.10 Archive this OpenSpec change via `openspec-archive-change` workflow
