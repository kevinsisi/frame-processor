# Proposal: Tighten processed_paths Typing

## Summary

`Photo.processed_paths` 在 DB 是 JSONB，在 Pydantic schema (`PhotoOut.processed_paths`) 型別為 `dict[str, str]`。實際上 key 必須是 `ColorGradePreset.value`（小寫，如 `"showroom_white"`）— 任何 writer 寫成 `preset.name`（大寫）或新增 enum 沒同步就會 silent miss。把 key 從 `str` 收緊到 `Literal[...]` / pydantic validator，把這層 invariant 從「靠約定」升到「型別/驗證強制」。

## Motivation

- `services/processing_versions.py:86, 121` 兩處都用 `preset.value`，目前正確；但 enum 多一個值或 refactor 換寫法時沒有任何 lint / runtime 保護。
- 一旦寫錯 key，FE 卡片版本下拉與 `_photo_out` 的 `processed_paths` 透傳會吞掉錯誤值；使用者層級表現就是「該版本下載按鈕消失」，debug 起來成本高。
- 同 schema 的 `dict | None` 寬鬆程度太低（前面 audit 也提到 `adjustment_params: dict | None`），先解決 `processed_paths` 這個明確的 case。

## Scope

- 後端 `api/schemas.py`：`processed_paths` 改成 `dict[ColorGradePreset, str]` 或維持 `dict[str, str]` + pydantic validator 限制 key ∈ `{p.value for p in ColorGradePreset}`。權衡見下方。
- 加 `model_validator` 同步驗證 `processed_paths` key 都是合法 preset value 字串。
- 對應 worker / service writer (`services/processing_versions.py`、`services/photo_processor.py`、`services/storage.py`) 確認所有寫入點都經過 `preset.value`，或建立統一 `_write_processed_path(photo, preset, abs_path)` helper。
- 前端 `web/src/types.ts` 的 `processed_paths: Record<string, string>` 收緊到 `Partial<Record<ColorGradePreset, string>>`。
- 新增 pure-function 測試覆蓋 validator 行為（非法 key、空 dict、所有 enum 值都齊）。

## Trade-off：Literal 還是 validator？

| | `dict[ColorGradePreset, str]` | `dict[str, str]` + validator |
|---|---|---|
| 序列化 | Pydantic 會把 key 自動 dump 成 enum value | 字串直接 dump |
| 反序列化 | 嚴格，沒列舉值會 422 | 自訂錯誤訊息 |
| FE 互操作 | TS 看到的 type 是 `Partial<Record<ColorGradePreset, string>>` | 同樣 |
| 重構成本 | 多處 type narrowing 要改 | 較少 |

**初步傾向**：`dict[ColorGradePreset, str]`（更嚴格、序列化會自動處理）。實作時若發現某處 `processed_paths` 確實會出現 `"adjusted"` 這類非 preset 值（FE PhotoGrid.tsx 有 `if (preset === "adjusted") continue;`），改用 validator 保留彈性。

## Non-Goals

- 不改 DB schema（JSONB 結構不變）。
- 不處理 `adjustment_params: dict | None` 的型別問題（另開 change，先處理單純的 `processed_paths`）。
- 不引入 runtime migration（既有資料假設都合法；不合法的 row 在驗證時 422，那是 dev 應該知道的情境）。

## References

- `api/schemas.py:65` 既有 `processed_paths: dict[str, str]`
- `services/processing_versions.py:86, 121` writer pattern
- `web/src/components/PhotoGrid.tsx:224` reader pattern（含 `adjusted` special case）
- `models/enums.py::ColorGradePreset`
