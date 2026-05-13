## ADDED Requirements

### Requirement: AI batch processing actions use explicit "AI" vocabulary

All user-facing labels, buttons, and hints related to AI batch processing SHALL use the explicit prefix 「AI」 to differentiate them from manual adjustment workflow vocabulary.

#### Scenario: Pipeline panel main action label
- **WHEN** the user views the Preview page's pipeline panel main action button
- **THEN** the button label reads 「開始 AI 處理已選 N 張」 (where N is the selected photo count)
- **AND** does NOT use the ambiguous label 「開始產生」

#### Scenario: Color preset selector label on Upload page
- **WHEN** the user views the Upload page's color preset section
- **THEN** the section title reads 「AI 色調風格」
- **AND** the hint text explicitly states that this preset is for AI batch processing and is unrelated to manual adjustment presets

#### Scenario: Pipeline panel sub-label for color preset
- **WHEN** the user views the Preview page's pipeline panel color preset dropdown
- **THEN** the dropdown's label reads 「AI 色調風格」 (not the bare 「色調風格」)

### Requirement: Manual adjustment actions use non-AI vocabulary

All user-facing labels, buttons, and hints related to manual adjustment SHALL avoid the words 「產生」, 「處理」, 「批次」 (which are reserved for AI batch processing) and use 「套用」, 「微調」, 「手動 v」 instead.

#### Scenario: AdjustmentPanel action button labels
- **WHEN** the user views the AdjustmentPanel action buttons
- **THEN** the primary action is labeled 「套用微調到目前照片」 (not 「產生目前版本」)
- **AND** the secondary action is labeled 「套用微調到已選照片」 (not 「產生已選版本」)
- **AND** the reset action is labeled 「清空目前照片的微調」 (not 「重設」)

#### Scenario: Preset management vocabulary
- **WHEN** the user views the preset management modal
- **THEN** preset-related labels use 「Preset」 / 「載入」 / 「儲存」 / 「刪除」 with no overlap with AI vocabulary
- **AND** the modal explicitly states that 「刪除 preset」 does not affect photos

### Requirement: Action consequence hints accompany every state-changing button

Each user-facing button that creates, deletes, archives, or replaces a photo version SHALL have an accompanying inline hint describing what the action will create or remove and what it will NOT affect.

#### Scenario: Apply button hint
- **WHEN** the user views the 「套用微調到目前照片」 button
- **THEN** an adjacent hint reads similar to 「會新增 manual v<N+1>。舊版本不會被覆蓋。」

#### Scenario: AI processing button hint
- **WHEN** the user views the 「開始 AI 處理已選 N 張」 button
- **THEN** an adjacent hint reads similar to 「會新增 AI v<N+1>。已存在的 AI 版本與手動微調版本不影響。每張數十秒～數分鐘。」

#### Scenario: Clear adjustments button hint
- **WHEN** the user views the 「清空目前照片的微調」 button
- **THEN** an adjacent hint reads similar to 「會刪除已產生的手動 v<N> 檔案，這張回到「沒微調」狀態（仍顯示 AI 版本）。」

#### Scenario: Delete preset hint inside modal
- **WHEN** the user views the delete button inside the preset management modal
- **THEN** the modal displays the disclaimer 「刪除 preset 只移除 template，不會動到任何照片。」
