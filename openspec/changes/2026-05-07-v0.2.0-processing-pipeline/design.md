# v0.2.0 — Design Notes

## 為何把 ROADMAP v0.2 / v0.3 / v0.4 / v0.5 合併

ROADMAP 原本拆四個 release，背後假設是「先簡單 Pillow，再逐步加 AI」。實際走過 v0.1 walking skeleton 後重評估：

- 四個獨立 release 對使用者沒有意義：色調沒水平校正會歪、沒裁剪留多餘背景、廣角不修車身彎弓、不降噪夜拍照都是雜訊
- worker pipeline、ProcessingJob schema、FE 處理 UI 是同一套基礎建設，分四次做要重複改四次 schema / FE / docker
- YOLOv8n 在 CPU 上 ~150ms/張、NAFNet-width32 在 CPU 上 ~3-8s/張（tile 切割），對 < 30 張的 batch 在 worker 內可接受

合併後共用同一個 `ProcessingJob` 與同一個 worker job，pipeline 內每階段是可選 step。

## Pipeline 順序：denoise → lens_distort → level → crop → grade

固定這個順序，不開放使用者調換：

1. **denoise 最先**：geometric ops（warp、resize）會放大噪點 pattern，先洗掉再做幾何
2. **lens_distort 次之**：把廣角桶形修平，後面的 level / crop 才能對得到真水平 / 真主體
3. **level_correct 第三**：水平校正需要無 fisheye 的圖才能找到真地平線
4. **auto_crop 第四**：YOLO 在已校正的圖上偵測車輛 bbox 才準
5. **color_grade 最後**：純像素操作，與幾何無關，最後做不影響先前所有步驟

## 為何水平校正改用 Gemini Vision 而不是 Hough Line

第一版用 OpenCV Canny + HoughLinesP 找主水平線並中位數估角，但實際車照常見：

- 車身有多條斜線（A 柱、車頂線、引擎蓋反光），Hough 中位數會被斜線拉偏
- 展示間 / 室內地板紋路會出現假水平線
- 室外停車場的停車格線會誤判
- ±5° 上限讓「歪 15° 的手機直拍」根本不會校正

改用 Gemini Vision：
- 用語意理解「真正的地平線」（地面、長水平車身線、建築物水平線）
- 對歪 30°、45° 的照片仍能給出正確角度
- 缺點：每張照片一次 API call（成本 + 延遲），但對 30 張 batch 仍在 30s 級別可接受
- 沒有 `GEMINI_API_KEY` 就 raise（不靜默 fallback 到別的演算法 — 違反「不要替代使用者意圖」原則）

## 為何加入 lens distortion correction

ROADMAP 沒涵蓋，但晴晴拍車常用：
- iPhone 主鏡頭 26mm + 廣角 13mm、Samsung 廣角
- 行車記錄器
- DSLR 24mm

這些焦段會有明顯桶形畸變：直立柱子彎弓、車身輪廓變形。
OpenCV `cv2.undistort` Brown-Conrady 模型可以反向矯正，但需要 (k1, k2) 係數。沒有 EXIF 提供精確相機參數，採用通用「中度廣角」預設 (k1=-0.08, k2=0.02)，可以從 settings 調整。

`getOptimalNewCameraMatrix(alpha=0)` 把矯正後仍然有效的區域裁出來，避免外擴黑邊。

未來可選改進：
- 從 EXIF FocalLength + 相機 model 查 lensfun 資料庫拿精確係數
- 使用者上傳「校正樣本」自動估係數

## 為何選 YOLOv8n 而不是 OpenCV-only saliency

| 選項 | 優 | 劣 |
|------|----|----|
| OpenCV saliency / 最大輪廓 | 沒額外依賴、< 50ms | 雜亂背景（停車場、展間）會誤判 |
| YOLOv8n | car/truck class 訓練好、~150ms CPU、6MB 權重 | 加 ultralytics + torch（已經因 NAFNet 拉了 torch） |
| YOLOv8s/m | 更準 | 慢 3–5×、權重 20–80MB |

NAFNet 已經把 torch 拉進來了，YOLOv8n 邊際成本只有 6MB 權重 + ultralytics SDK，划算。

## 為何 NAFNet 而不是 Real-ESRGAN / SCUNet

- NAFNet (ECCV 2022) 是當前 SIDD denoising 的 SOTA，相同 PSNR 下推理快 3-5×
- Real-ESRGAN 是 super-resolution，目標不同（可同時輕微 denoise，但會把照片放大）
- SCUNet 表現接近 NAFNet 但實作較複雜
- NAFNet 架構簡單（無 activation、無 normalization 層），inline 重寫只要 ~150 行

## 為何 NAFNet inline 而不是用 basicsr 套件

- basicsr 套件巨型（拖入 mmcv、scipy、tb-nightly 等），對只用 forward 推理很冗
- NAFNet 架構單純，inline ~150 行 PyTorch 即可，不影響相依
- 權重 checkpoint 用 `torch.load` 直讀官方格式（state_dict 在 `params` key 下）

## 為何 NAFNet 強度用 alpha-blend 而不是模型參數

- NAFNet 訓練好的模型沒有「強度」hyper-parameter
- 重訓不同強度的多個 checkpoint 不切實際
- alpha-blend 簡單有效：`out = α * denoised + (1-α) * original`，使用者直覺、執行成本極低
- 0.4 / 0.7 / 1.0 對應「保留質感 / 折衷 / 最強降噪」

## 為何 Gemini Vision 而不是其他 VLM

- 已驗證：Gemini Flash 對「估角度」這類數值任務 zero-shot 能力可靠
- API 便宜（Flash 比 Pro 便宜 ~5×）、延遲低（~1-2s/張）
- Anthropic Claude Vision、OpenAI GPT-4o 也行，但晴晴 / 此 stack 已有 Google AI Studio key

## 為何 `auto_crop_aspect` 是 Optional

- `null` = 跳過 crop（保留原始 aspect）
- 給的值就按該 aspect 裁
- 比起 `ORIGINAL` enum 值更直覺

## 為何 zip_export 在有 processed 時優先打包 processed

- 使用者跑完處理 → 按「匯出 zip」→ 期望拿到處理後照片
- 但如果某些 photo 還沒處理（部分選取 / 部分失敗），fallback 到原圖

## 為何 ProcessingJob 不存 per-photo 結果，只存 progress / total

- per-photo 結果都已經寫到 `Photo.processed_paths` 了，重複存沒意義
- 進度條只需要 `progress / total` 兩個整數
- worker 失敗某張 → 整個 job 設 failed，並把錯誤訊息塞 `error`（v0.2.0 簡化處理；v0.2.1 可改成 per-photo error）

## 為何 OpenCV 而不是 scikit-image / ImageMagick

- OpenCV Hough / undistort / warpAffine 是工業標準
- scikit-image 也可，但 OpenCV 加上去成本低（torch 已經有 numpy 生態系）
- ImageMagick 是 CLI，不適合 in-process pipeline
