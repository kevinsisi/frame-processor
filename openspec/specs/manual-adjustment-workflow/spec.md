# manual-adjustment-workflow Specification

## Purpose
TBD - created by archiving change preset-ux-redesign. Update Purpose after archive.
## Requirements
### Requirement: Apply manual adjustments to current photo

The system SHALL allow users to render the current AdjustmentPanel slider values into a new `manual-v<N>.jpg` for the currently active photo without modifying any other photo or version.

#### Scenario: Apply creates new manual version
- **WHEN** the user clicks 「套用微調到目前照片」 with non-default slider values
- **THEN** the system creates a new `manual-v<N>` for the active photo and selects it in the version dropdown
- **AND** previous AI and manual versions of the same photo remain unchanged and selectable

#### Scenario: Apply does not affect other photos
- **WHEN** the user clicks 「套用微調到目前照片」 with 12 photos selected
- **THEN** only the currently active photo gets a new manual version
- **AND** the other 11 selected photos have no version changes

### Requirement: Apply manual adjustments to selected photos

The system SHALL allow users to render the current AdjustmentPanel slider values into new `manual-v<N>.jpg` files for every currently selected photo, each as an independent new version.

#### Scenario: Apply-to-selected creates one version per selected photo
- **WHEN** the user clicks 「套用微調到已選照片」 with 12 photos selected
- **THEN** each of the 12 photos receives a new `manual-v<N>` rendered with the current slider values
- **AND** previous versions on each photo remain on disk and selectable

#### Scenario: Apply-to-selected with one photo behaves like apply-to-current
- **WHEN** the user has exactly one photo selected and clicks 「套用微調到已選照片」
- **THEN** the behavior is identical to 「套用微調到目前照片」 on that photo

### Requirement: Clear current photo's manual adjustments

The system SHALL allow users to clear all manual adjustments on the active photo via a dedicated 「清空目前照片的微調」 action that resets slider draft state, hard-deletes every existing `photo_adjustment_versions` row (and corresponding disk file) for that photo, clears the `processed_paths["adjusted"]` cache entry, and switches the active version selector back to the latest non-archived AI version (or original if none).

#### Scenario: Clear deletes manual versions and resets selector
- **WHEN** the user clicks 「清空目前照片的微調」 on a photo with `manual-v1` and `manual-v2` and `AI v1` (展間白)
- **THEN** the system deletes both `manual-v1` and `manual-v2` (DB row + disk file)
- **AND** the photo's `photo_adjustments` row is reset to default values
- **AND** the photo's `processed_paths["adjusted"]` cache entry is removed
- **AND** the active version selector switches to `AI v1`
- **AND** Before/After re-renders to show the AI v1 image as "After"

#### Scenario: Clear when no AI version exists falls back to original
- **WHEN** the user clicks 「清空目前照片的微調」 on a photo with manual versions but no AI version
- **THEN** the active version selector switches to 「原圖」

#### Scenario: Clear hard-deletes disk files
- **WHEN** the system clears manual adjustments for a photo
- **THEN** the corresponding `manual-v<N>.jpg` files on disk are deleted
- **AND** disk delete failures are logged but do not abort the operation (DB transaction commits first)

### Requirement: Clear selected photos' manual adjustments

The system SHALL allow users to clear manual adjustments on every currently selected photo via 「清空已選照片的微調」, handling mixed-state selections gracefully.

#### Scenario: Clear-selected with mixed state photos
- **WHEN** the user has 12 photos selected, of which 9 have manual versions and 3 do not, and clicks 「清空已選照片的微調」
- **THEN** the system clears manual adjustments for the 9 photos
- **AND** the 3 photos without manual adjustments are no-op (not an error)
- **AND** the toast / response reports `cleared_count = 9`

#### Scenario: Clear-selected is atomic per photo
- **WHEN** the clear operation fails midway for a single photo
- **THEN** the DB transaction for that photo rolls back, leaving its state unchanged
- **AND** photos already cleared in earlier iterations are not rolled back (each photo is its own unit)

### Requirement: Load preset copies values without binding

The system SHALL allow users to load a saved `AdjustmentPreset` by selecting it from the preset dropdown, which copies the preset's slider values into the active photo's draft AdjustmentPanel state without creating any reference between the photo and the preset.

#### Scenario: Loading preset fills sliders on active photo only
- **WHEN** the user selects 「晴晴常用調」 from the preset dropdown with `photo_a` active
- **THEN** `photo_a`'s draft sliders update to the preset's values
- **AND** no `manual-v<N>` file is created (apply must be pressed separately)
- **AND** no other photo's state changes

#### Scenario: Loaded preset is not tracked after load
- **WHEN** the user loads `preset_X` onto `photo_a` and later modifies a slider
- **THEN** `photo_a` does not retain a reference to `preset_X` (no `applied_preset_id` is set)
- **AND** subsequent deletion of `preset_X` has no effect on `photo_a`

### Requirement: Save current sliders as new preset

The system SHALL allow users to save the active photo's current draft slider values as a new `AdjustmentPreset` row via 「儲存目前數值」.

#### Scenario: Save creates new preset row
- **WHEN** the user clicks 「儲存目前數值」 and provides a name 「展廳暖白」
- **THEN** a new `adjustment_presets` row is created with the current slider values and the given name
- **AND** the preset becomes available in the load dropdown for the current project

### Requirement: Delete preset removes template only

The system SHALL allow users to delete a saved `AdjustmentPreset` via the 「⚙ 管理」 modal, with the explicit guarantee that deletion only removes the preset row and has no effect on any photo, version, or rendered file.

#### Scenario: Delete preset does not modify photos
- **WHEN** the user deletes `preset_X` from the management modal
- **AND** photos `photo_a`, `photo_b` had previously loaded `preset_X`'s values and rendered `manual-v<N>`
- **THEN** the `adjustment_presets` row for `preset_X` is removed
- **AND** `photo_a`, `photo_b` and their `manual-v<N>` files remain unchanged
- **AND** the active version selector on those photos is not modified

#### Scenario: Delete preset shows explicit no-photo-impact disclaimer
- **WHEN** the user opens the 「⚙ 管理」 modal
- **THEN** the modal displays a visible disclaimer stating that deleting a preset does not affect any photo
- **AND** instructs the user to use 「清空照片微調」 actions if they want to remove the effect from photos

