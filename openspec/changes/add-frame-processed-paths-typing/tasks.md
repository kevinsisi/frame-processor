# Tasks — Tighten processed_paths Typing

## Audit

- [ ] grep 所有 `processed_paths` 讀寫點，列出每個 caller 的預期 key 集合。
  - writer：`services/processing_versions.py`、`services/photo_processor.py`、worker jobs
  - reader：`api/routers/projects.py::_photo_out`、FE `PhotoGrid.tsx`、Export 流程
- [ ] 確認 `"adjusted"` key 是否真的存在於 DB（FE 有 `if (preset === "adjusted") continue` 的 guard 暗示曾經存在）。
- [ ] 列出 `ColorGradePreset` 所有合法 value，建為「allowed keys」白名單。

## 後端

- [ ] 決定走 `dict[ColorGradePreset, str]` 還是 `dict[str, str] + validator`（依 audit 結果）。
- [ ] `api/schemas.py:65 PhotoOut.processed_paths` 套用新型別。
- [ ] 加 `@model_validator(mode="after")` 或 `@field_validator("processed_paths")` 檢查所有 key 都在白名單。
- [ ] 加共用 helper 例如 `services/processed_paths.py::set_path(photo, preset, abs_path)` 收斂所有 writer，避免散落 `photo.processed_paths[preset.value] = ...` 重複 code。
- [ ] 全 writer 改走 helper。
- [ ] 跑 `pytest -q` 確認既有測試還綠。

## 前端

- [ ] `web/src/types.ts`：`processed_paths: Record<string, string>` → `Partial<Record<ColorGradePreset, string>>` 或保留 `Record<string, string>` 但補 `// invariant: keys are ColorGradePreset.value`。
- [ ] 確認 `PhotoGrid.tsx` `Object.keys(photo.processed_paths)` 仍能正常 narrow。
- [ ] `npm run typecheck` 通過。

## 測試

- [ ] 新增 `tests/test_processed_paths_schema.py`：合法 / 非法 key 驗證、空 dict 驗證、validator 錯誤訊息含 key 名稱。
- [ ] 若採 helper：測試 helper 拒絕非 `ColorGradePreset` 物件。

## 文件

- [ ] CLAUDE.md 補一行 invariant：「`processed_paths` key MUST be `ColorGradePreset.value`」。
- [ ] ARCHITECTURE.md storage layout 段落更新 key 規則。

## Verification

- [ ] `pytest -q` 全綠（含新測試）。
- [ ] `npm run typecheck` + `npm run build` 全綠。
- [ ] 本機 smoke：建立新 batch、archive 舊版、recompute cache，確認 `processed_paths` 仍正確讀寫。
