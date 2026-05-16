# Tasks — ESLint v9 Flat Config Migration

Note: v0.4.10 added a minimal `web/eslint.config.js` so `npm run lint` can run during the hotfix release. The full migration below remains open until type-aware lint, recommended/react-refresh rules, CI wiring, and related fixes are completed.

Status note (2026-05-16): `web/eslint.config.js` exists and `npm run lint --prefix web` currently exits 0. Remaining work is full rule coverage/type-aware config and adding lint to CI.

## Configuration

- [x] 盤點目前是否還有 `web/.eslintrc.*` 殘留檔；目前沒有殘留檔。
- [x] 建立 `web/eslint.config.js` minimal flat config，已匯入：
  - `@typescript-eslint/eslint-plugin` + `@typescript-eslint/parser`
  - `eslint-plugin-react-hooks`
- [ ] 擴充 `web/eslint.config.js` full flat config，匯入：
  - `eslint-plugin-react-refresh`
  - `eslint` recommended preset
- [ ] flat config parserOptions 指向 `web/tsconfig.json`（type-aware lint）。
- [x] 確認 ignore：目前 config ignore `dist/`、`node_modules/`。
- [ ] 決定 `scripts/*.cjs` 是否要 lint，決定後寫進 config。
- [ ] 對齊既有 lint 行為：v8 時的 default rule 設定要不要保留？預期維持與 v8 等價。

## 修 lint 結果

- [x] `npm run lint --prefix web` 目前退出碼 = 0（2026-05-16）。
- [ ] 擴充 full flat config 後逐一檢視 error / warning：
  - 修純語法層問題（unused imports、wrong any、missing deps in hook effects 等）。
  - 確認沒有意外開啟超嚴格 rule（例如 `no-explicit-any` 預設改為 error）；如有則明確 ignore 並在 config 註明原因。
- [x] 目前 minimal config 下 `npm run lint --prefix web` (`eslint . --ext ts,tsx --max-warnings 0`) 退出碼 = 0。

## CI

- [ ] `.github/workflows/ci.yml` 新增 `- run: npm run lint --prefix web` step（或對應 working-directory 設定）。
- [ ] CI lint step 失敗時整個 workflow fail。
- [ ] 確認 ci.yml 的 node setup step 也安裝 web `node_modules`（已有 npm ci? 確認）。

## Verification

- [ ] 本機 `npm run lint` 通過。
- [ ] 本機 `npm run typecheck` 仍通過（lint config 不影響 tsc）。
- [ ] 本機 `npm run build` 仍通過。
- [ ] CI run on `main` 顯示 lint step 綠燈。
- [ ] 更新 `reference_frame_processor.md` 移除「ESLint v9 broken」段落或改為「已修復 (commit X)」。
