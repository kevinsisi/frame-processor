# Preview UX Audit

Date: 2026-05-10
Scope: `/preview` review, batch generation, manual adjustment, version selection, and export handoff.
Code reviewed: `web/src/pages/Preview.tsx`, `web/src/pages/Preview.css`, `web/src/components/BeforeAfter.tsx`, `web/src/components/PhotoGrid.tsx`, `web/src/components/PipelinePanel.tsx`, `web/src/components/AdjustmentPanel.tsx`.

This is the current static/code audit. It is not a replacement for real-photo smoke testing or iPhone Safari QA.

## User Workflow

The intended user workflow is still simple:

1. Upload a batch of vehicle photos.
2. Pick a style and default processing options.
3. Let the system generate usable AI processed versions.
4. Review Before/After quickly across the batch.
5. Manually fix only the photos that need correction.
6. Export the chosen versions.

The current implementation supports that workflow, but `/preview` also contains several advanced tools in one long page. The main UX risk is not missing capability; it is mode mixing and weak source/status clarity.

## Already Improved

- Upload-selected style now feeds Preview pipeline settings and automatic batch generation.
- The default denoise path is medium, reducing the risk of oil-painting output.
- The primary batch action is sticky and disables while a job is pending/running.
- Missing preset outputs can auto-start a background batch job.
- Before/After now has inline previous/next controls and an index/filename counter.
- The manual geometry editor is separated into a full-screen workspace instead of cramped inline controls.
- Version dropdowns hide internal names and can switch tile image, comparison source, manual source, and download target.

## Findings

### P0: None Currently Identified

No immediate data-loss or deployment-blocking UX issue was found in this audit.

### P1: Preview Still Mixes Too Many Modes

`/preview` currently combines batch generation, job monitoring, Before/After review, manual adjustment, pipeline settings, photo selection, version management, per-photo download, and export handoff in one linear page.

Risk: users who only want to review generated photos must pass through manual-edit controls, while users who want to generate may not understand why manual adjustment appears before pipeline settings.

Recommended direction: split the visible workflow into mode tabs or sections with stronger entry points: `批次產生`, `審片比較`, and `單張微調`. Keep the current implementation underneath; change the information architecture first.

### P1: Batch Output Identity Is Too Ambiguous

Processed outputs are selected and displayed mainly by color preset, for example `批次：展示間白`. The visible label does not include denoise strength, lens correction, level correction, or aspect ratio. The auto-generation guard also keys missing work primarily by project, preset, and missing photo IDs.

Risk: two outputs with the same style but different denoise/geometry options are not distinguishable to the user. A user can change denoise or correction settings and still see an old preset output that looks like it represents the new settings.

Recommended direction: introduce a visible processing profile label such as `展示間白 / 中度降噪 / 廣角+水平 / 原始比例`, and consider storing generated versions by full processing profile rather than preset only.

### P1: Source Of Before/After Needs Stronger Explanation

Before is intentionally the original photo, while After can be a live manual preview, a selected batch preset, a manual version, or even the original when no generated output exists yet.

Risk: users may interpret a weak After as failed AI processing even when After is only a manual preview or original fallback.

Recommended direction: show an explicit source strip near the comparison viewer: `Before: 原圖` and `After: 目前微調 / 批次展示間白 / 手動版本 vN / 尚未產生`. Keep the existing warning, but make source state always visible, not only when output is missing.

### P1: Manual Apply-To-Selected Needs A Confirmation Summary

`產生已選版本` applies the active adjustment parameters to every selected photo, using each photo's selected source mapping.

Risk: this is powerful but easy to misuse. A user may accidentally apply one photo's color/geometry edits to a large selection.

Recommended direction: before starting multi-photo adjustment jobs, show a compact confirmation summary with count, adjustment source behavior, and a clear warning that the active settings will be applied to all selected photos.

### P2: Auto-Saved Draft State Is Invisible

Slider and rotation edits are auto-saved as per-photo drafts, but save failures only go to console and the UI does not expose `saved`, `saving`, or `failed` state.

Risk: users cannot tell whether draft edits will survive refresh, and silent failures can create mistrust.

Recommended direction: add a small draft status near `手動微調`: `已儲存草稿`, `儲存中`, or `草稿儲存失敗` with retry on next change.

### P2: Job Status Is Useful But Not Action-Oriented

The job queue shows progress and per-photo states, but does not provide next actions after success or failure.

Risk: after a job finishes, users still need to infer that the comparison output changed or that they should review/export.

Recommended direction: after success, show `開始審片` or keep focus near Before/After. After failure, expose retry with the same processing payload and failed photo list.

### P2: Mobile Layout Still Needs Real Device QA

The comparison viewer uses large minimum heights and the sticky action bar adds large bottom padding on small screens. Inputs generally avoid iOS text zoom because most controls are range inputs, selects, or buttons, but the actual touch density still needs verification.

Risk: on iPhone Safari, the sticky action bar, large Before/After viewer, and geometry editor controls may compete for vertical space.

Recommended direction: run real iPhone Safari QA with a 10 to 30 photo project, including comparison navigation, slider dragging, geometry editor, select dropdowns, and export navigation.

### P2: Comparison Viewer Needs Keyboard And Gesture Polish

The comparison slider is pointer-driven and the new photo navigation buttons are clickable, but there is no keyboard operation for the divider or photo navigation.

Risk: desktop power users and accessibility users have slower review flow.

Recommended direction: support arrow keys when the comparison viewer is focused: left/right for previous/next photo, modifier plus left/right for divider movement, and visible focus states.

### P2: Photo Card Actions Are Dense On Mobile

Each photo card includes open original, version select, and download version. The font size is small and the selected/active states compete visually with the checkbox and hover overlay.

Risk: mobile users may tap the card when they meant to select, change version, or download.

Recommended direction: promote the active selection and version state into a clearer card header/footer, and reserve secondary links for an overflow/action row.

### P3: Geometry Editor Accessibility Is Basic

The geometry editor uses a modal role and has cancel/done buttons, but it does not visibly manage focus, Escape close, or keyboard nudging for crop/rotation.

Risk: acceptable for the current prototype, but it will limit reliability for keyboard users and complicated edits.

Recommended direction: add focus trapping, Escape-to-cancel, and small keyboard nudge support once geometry editing becomes a primary daily workflow.

### P3: Preview API Debounce Protects State But Not Network Load

Manual preview requests are debounced and stale responses are ignored, but in-flight requests are not cancelled.

Risk: fast slider movement can still create avoidable backend work, especially on large projects or slow devices.

Recommended direction: add request cancellation or a latest-only backend strategy if preview latency becomes visible during real-photo testing.

## Priority Plan

1. Add persistent source/profile labels to Before/After and photo versions.
2. Separate `/preview` into review/generate/edit modes without changing backend behavior.
3. Add confirmation for apply-to-selected manual adjustments.
4. Add draft save status.
5. Run and record iPhone Safari QA with real photos.
6. Add keyboard shortcuts and accessibility polish for comparison and geometry editor.

## Not Yet Closed

- iPhone Safari mobile layout validation.
- Real-photo showroom white neutrality smoke test.
- Individual processed download smoke test.
- Visual QA for denoise strength on representative indoor, outdoor, low-light, and dealership photos.
