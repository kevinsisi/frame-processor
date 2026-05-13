# photo-version-display Specification

## Purpose
Defines how Preview surfaces the currently selected photo version, including Before/After source-chain labels, PhotoCard AI/manual chips, version counts, and mobile-safe fallback display.
## Requirements
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

