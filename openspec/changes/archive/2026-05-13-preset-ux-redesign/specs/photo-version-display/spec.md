## ADDED Requirements

### Requirement: BeforeAfter header shows full source chain

The Preview page's Before/After comparison component SHALL display the currently selected version of the active photo as a textual source chain on the header, naming the AI version (with its color preset) and the manual version layer (if any), plus the top 3 most-deviated slider values when manual adjustments are present.

#### Scenario: Photo with AI + manual + non-default sliders
- **WHEN** the active photo has `AI v1` (展間白) and `manual v2` selected with `對比 +25`, `色溫 +120`, `飽和 +5`
- **THEN** the BeforeAfter header shows `Before: 原圖 · After: 手動 v2 — 基於 AI v1 / 展間白 · 對比 +25 / 色溫 +120 / 飽和 +5`

#### Scenario: Photo with AI but no manual
- **WHEN** the active photo has `AI v1` (展間白) selected and no manual version
- **THEN** the BeforeAfter header shows `Before: 原圖 · After: AI v1 / 展間白`

#### Scenario: Photo with original only
- **WHEN** the active photo has only 「原圖」 selected (no AI, no manual)
- **THEN** the BeforeAfter header shows `Before: 原圖 · After: 原圖（尚未處理）`

#### Scenario: Mobile fallback truncates slider summary
- **WHEN** the viewport width is below the mobile breakpoint and a full source chain would overflow
- **THEN** the BeforeAfter header collapses the slider summary, showing only the version layers (e.g. `After: 手動 v2 — 基於 AI v1`) without the per-slider deviation list

### Requirement: Selected AI version drives displayed image

When the user selects an AI batch version, the Preview page SHALL display that exact immutable AI version output in PhotoCards and the Before/After after-side by using the selected version's `processing_job_id`, not the latest preset compatibility cache.

#### Scenario: Selecting a completed AI version
- **WHEN** the user clicks 「查看版本」 for `AI v14`
- **THEN** every photo with a completed `AI v14` output has its selected version value set to that AI version
- **AND** the photo tile and Before/After after-side image URL use `/photos/{photo}/file?processing_job_id={AI v14 job id}`
- **AND** the display does not fall back to `/photos/{photo}/file?variant=processed&preset=showroom_white` while that selected AI output exists

#### Scenario: Active comparison photo is outside a partial AI version
- **WHEN** the currently active comparison photo has no completed output in the AI version the user selected
- **THEN** the Preview page switches the active comparison photo to the first project photo with a completed output in that selected AI version
- **AND** the Before/After after-side shows that selected AI version output rather than the previously active photo's older version

### Requirement: PhotoCard displays current AI and manual version chips

Each photo card in the Preview grid SHALL display two color-coded chips below the thumbnail naming the photo's currently selected AI version and manual version, plus an entry point to switch versions.

#### Scenario: Photo with AI + manual versions
- **WHEN** a photo has `AI v1` and `manual v2` selected
- **THEN** the photo card shows an AI-colored chip 「AI v1」 and a manual-colored chip 「手動 v2」
- **AND** an entry point 「▼ N 個版本」 is rendered showing the total number of available non-archived versions

#### Scenario: Photo with no manual
- **WHEN** a photo has `AI v1` selected and no manual version
- **THEN** the photo card shows the 「AI v1」 chip and a 「無手動」 placeholder chip

#### Scenario: Photo unprocessed
- **WHEN** a photo has only 「原圖」 selected (no AI, no manual)
- **THEN** the photo card shows a 「原圖」 chip and a 「尚未處理」 hint
- **AND** no version-count entry is shown

#### Scenario: Cleared manual versions excluded from count
- **WHEN** a photo had 3 manual versions and the user clicks 「清空目前照片的微調」
- **THEN** all 3 manual version rows are deleted from `photo_adjustment_versions`
- **AND** the 「N 個版本」 count reflects only the remaining AI versions and original (e.g. shows 「▼ 2 個版本」 if the photo has AI v1 and original)
- **AND** archived AI versions remain excluded from the count (unchanged from prior behavior)

### Requirement: AI versions and manual versions use distinct visual treatment

The Preview UI SHALL use distinct visual styles (color, label prefix) for AI batch versions versus manual adjustment versions so users can tell the two version types apart at a glance in headers, chips, and version dropdowns.

#### Scenario: Version label conventions
- **WHEN** the system displays an AI batch version
- **THEN** it uses the prefix 「AI v」 and an AI-themed accent color
- **WHEN** the system displays a manual version
- **THEN** it uses the prefix 「手動 v」 and a manual-themed accent color
- **AND** the same convention is used in version dropdowns, photo card chips, and BeforeAfter header
