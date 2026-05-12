# Proposal: Migrate Frontend ESLint to v9 Flat Config

## Summary

`web/` 已經安裝 ESLint 9.x，但 `web/` 還在用舊式 `.eslintrc.*` 配置，`npm run lint` 開機就炸：

```
ESLint couldn't find an eslint.config.(js|mjs|cjs) file.
From ESLint v9.0.0, the default configuration file is now eslint.config.js.
```

把 ESLint 配置從 legacy `.eslintrc` 形態遷到 v9 flat config，恢復 lint 可用，並把 lint 加進 CI 防止往後又破。

## Motivation

- `npm run lint` 是 `package.json` 已定義的 npm script，但目前直接 fail，等於沒有自動化 lint。code review 全靠 typecheck 與肉眼。
- `--max-warnings 0` 想擋住所有 warning 是好的標準，但因為 lint 整個沒在跑，這個標準目前沒生效。
- ESLint v9 flat config 是現在的官方方向，回頭裝 ESLint 8 沒意義，遲早要遷。
- 6+ 個前端開發 / 重構 OpenSpec（adjustment-panel、batch-version-control 等）若都不過 lint，技術債只會繼續累積。

## Scope

- 新增 `web/eslint.config.js` 採用 flat config，覆蓋既有 `.eslintrc.*` 設定（若存在；如果已被刪除就直接從零建）。
- 對齊既有 `@typescript-eslint`、`eslint-plugin-react-hooks`、`eslint-plugin-react-refresh` 三個 plugin。
- TypeScript-aware lint（parser project 指向 `web/tsconfig.json`）。
- 修掉所有 v9 + 新規則跑出來的 warning / error，讓 `npm run lint --max-warnings 0` 一次過。
- 把 lint step 加進 `.github/workflows/ci.yml`，CI fail 才能擋未來 regression。

## Non-Goals

- 不引入 Prettier 或重新格式化整個 codebase；只動 lint 設定與最小 surface 的修正。
- 不換 lint runner（biome / oxlint 等）；繼續用 ESLint。
- 不調整 lint rule 嚴格度；只還原 v8 + 既有 plugin 等價的設定。後續若要加新規則走另一個 change。
- 不替換 typescript-eslint 主版本以外的相依升級。

## References

- ESLint v9 migration guide: https://eslint.org/docs/latest/use/configure/migration-guide
- Pre-existing 問題紀錄：`reference_frame_processor.md § ESLint v9 broken`
