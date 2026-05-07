# v0.2.0 — Design Notes

## 為何 v0.2 把 v0.4（自動裁剪）+ v0.5（水平校正）合進來

ROADMAP 原本拆三個 phase，每個都單獨 ship 才合理嗎？答案：不合理。

- 處理 pipeline 的成本是「worker 整套架構 + UI before/after + DB schema」，不是個別演算法。把這一坨基礎設施只交付一個 color grade preset，UI 顯不出來「批次後製」的價值。
- 水平校正 + 自動裁剪用 OpenCV 的 heuristic 都很輕（Hough、Sobel），不會把 v0.2 的 CPU / image size 撐爆。
- YOLO 級別的自動裁剪還是留 v0.4，因為它要新增模型權重 + GPU runtime，跟 NAFNet 一起做更省事。

合併後的 v0.2 = 「跑得起來的第一條完整 pipeline」，三個演算法都是 stub-quality 但端到端能用。後續 phase 各自升級。

## Pipeline 順序：level → crop → grade

```
原圖 (PIL)
   ↓ level_correct（旋轉到水平）
   ↓ auto_crop（按 target aspect 找最高能量 sub-window）
   ↓ color_grade（白平衡 / 暖 / 冷 任一 preset）
   ↓ 輸出 jpg quality=92 → <storage>/projects/<pid>/processed/<photo_id>.<preset>.jpg
```

**為何這個順序**：
- 水平校正一定要先做，因為旋轉後尺寸會稍變（即使 expand=False 也有黑邊），裁剪要在旋轉後的座標系內找構圖。
- color grade 最後做，因為它跟構圖無關，純色彩運算；放最後也不影響 crop 邊緣。

## 為何 auto_crop 用 energy-based 而不是 center crop

- 車輛照片車身通常不在正中央（攝影師會找構圖角度）。Center crop 可能把車輪切掉。
- Energy-based（Sobel 邊緣強度）對車身金屬反光、輪框細節、車牌邊緣很敏感，會自然把 crop window 拉到車身。
- 缺點：背景有強紋理（牆磚、樹葉）會干擾。v0.4 換 YOLO 主體偵測後解決。
- 實作用 numpy integral image（cumsum）算 sliding window sum，O(W*H) 而不是 O(W*H*k1*k2)。

## 為何 level_correct 設 ±5° 閾值

- 真實傾斜照片大部分是 ±0.5°~±3°（手持快拍）。
- 超過 ±5° 通常是 Hough 抓到斜的車身底盤線、欄杆、或特殊角度，視為誤判更安全。
- 寧可少做也不要轉錯，因為轉錯比沒轉慘（看起來像故意 dutch angle）。

## Color grade 為何用 numpy 而不是純 Pillow operations

- Pillow 的 `ImageEnhance` / `ImageOps` 對「按通道乘係數」「條件式 gamma（只調暗部）」這類運算表達力有限。
- 用 `np.asarray(img) / 255.0` 進浮點空間做運算，再寫回 uint8，邏輯清楚。
- 對 5–25MB JPEG（解析度 ~6000×4000）一張處理時間在 1.5–3 秒；可接受。
- 之後若要加 LUT、tone curve 也是 numpy 自然延伸。

## DB：為何用 `Photo.processed_paths` JSONB 而不是 `ProcessedPhoto` 子表

考量過兩個方案：

| 方案 | 優點 | 缺點 |
|------|------|------|
| JSONB on Photo | 簡單，查詢直接 join photos | 同 preset 重跑會覆蓋；無歷史 |
| ProcessedPhoto 子表 | 可保留多次處理歷史；可查 job-by-job 結果 | schema 多一張表，FE / API 都要多一層 |

v0.2 選 JSONB：
- 晴晴的工作流是「跑一次、看結果、有問題重跑覆蓋」，不需要保留歷史。
- v0.6 加「組合 preset bundle」時若需要區分 (preset, level, crop) 三軸再升級成子表。
- 重跑時 worker 直接覆蓋 `processed_paths[preset]` 對應的檔案路徑與 DB 值。

JSONB 結構（key = preset name, value = relative path）：
```json
{
  "showroom_white": "projects/<pid>/processed/<photo_id>.showroom_white.jpg",
  "outdoor_warm": "projects/<pid>/processed/<photo_id>.outdoor_warm.jpg"
}
```

## 為何 ProcessingJob 不重用 ExportStatus enum

- 語意上 export 與 processing 是兩個不同的工作流；雖然狀態機相同（pending/running/done/failed）但日後可能分歧（processing 可能加 `partial_done` / `cancelled`）。
- PG ENUM 重新命名比拆開麻煩，現在分開省得未來 migration 痛苦。
- `models/enums.py` 加 `ProcessingJobStatus` 與 `ExportStatus` 並列。

## 為何 thumbnail 走 lazy generation 而不是上傳時同步生成

- 上傳是 web request 時間敏感；批次上傳 50 張同步生成 thumbnail 會讓 request 時長 +30s。
- Lazy 在第一次 `GET /photos/{id}/thumbnail` 時生成 + 落地；之後直接 sendfile。
- 缺點：第一張 grid 載入慢一拍。可接受（批次處理一次完成後 thumbnail cache 也跟著熱了）。

## 為何 OpenCV 用 `opencv-python-headless`

- Production container 沒有 X server，`opencv-python` 會 import 失敗（試圖載 GUI lib）。
- `headless` 變體去掉 `cv2.imshow` / `cv2.namedWindow` 那些 GUI binding，但保留 image processing primitives。
- runtime native deps：`libgl1` + `libglib2.0-0`（minimum set for headless）。

## Frontend：BeforeAfter slider 為何不引第三方 lib

- 同一張照片左右對比，純 CSS `clip-path: inset(...)` 加一個 input range 拖拉條就夠。
- 引入 `react-compare-slider` 之類的會多 ~20KB 還少不了客製樣式。
- 自寫 < 100 行可控制 design language 與 token。

## Frontend tone：延續 v0.1.1 editorial dark

- v0.1.1 已建立 design tokens（`web/src/styles/tokens.css` — 待確認），所有新 component 沿用既有 spacing / color token，不引第二套設計語言。
- StylePicker 邊界從 v0.1 「read-only chip」變成「actionable card」，加上選擇後的 outline glow 表示「將要處理」。
- 處理中狀態：grid 上覆 progress overlay + spinner；完成後 thumbnail crossfade 到 processed 版本。

## 已知妥協

- **Auto crop 對車身底盤橫線可能誤判為構圖中心** — energy 算法不知道「下方欄杆紋理」與「主體」差異。v0.4 YOLO 修。
- **Color grade 是固定係數，不適配場景** — SHOWROOM 對戶外照可能過暗；OUTDOOR 對白底可能過暖。三個 preset 是常用啟動值，不是萬用。晴晴可選最接近的。
- **每個 preset 重跑會覆蓋** — 若需要 A/B 比較不同次跑出來的結果，v0.2 不支援。
- **沒有處理進度 SSE** — FE polling `/processing-jobs/{id}` 每 1.5 秒一次；50 張照片總共 ~30 次 poll，可接受。

## 未來注意點

- **Preset 名稱永遠走 enum** — `models/enums.py:ColorGradePreset`；router / FE 都拒絕字串散落。
- **Pipeline contract** — `process_photo(photo, preset, *, level_correct, auto_crop_aspect) -> ProcessedResult` 將是 v0.3+ 加 denoise 的延伸介面（多一個 `denoise: bool` 參數，邏輯插在 level 之前）。
- **OpenCV import 開銷** — `import cv2` 約 0.3s；worker 啟動時就 warmup，不要在 hot path 第一次 import。
