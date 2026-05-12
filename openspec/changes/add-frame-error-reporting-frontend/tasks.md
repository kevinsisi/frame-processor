# Tasks — Frontend Error Reporting

## Audit

- [ ] 確認 `web/src/components/` 是否已有 toast component；若有，直接重用。
- [ ] 確認既有 useEffect 是否有 cleanup race（poll 在 unmount 後仍 reject 該不該觸發 toast）。

## Toast infra

- [ ] 若無既有 toast：新增 `web/src/components/Toast.tsx` + `ToastContainer`，支援 info / warning / error 三種 variant、3-5s auto-dismiss、手動 dismiss。
- [ ] 新增 `web/src/hooks/useToast.ts` 或 `ToastContext` 把 push/dismiss API 接出。
- [ ] 在 `App.tsx`（或現有 root）掛 `ToastContainer`。

## Error reporting util

- [ ] 新增 `web/src/utils/errorReporting.ts`：
  - `reportError(context: string, error: unknown, options?: { silent?: boolean; toastMessage?: string }): void`
  - 內部 console.warn 一律走，附加 context label
  - 非 silent 時呼叫 toast push（預設使用者可讀的 message，可用 toastMessage 覆寫）

## 替換 Preview.tsx

- [ ] `:354 save adjustment draft failed` → `reportError("adjustment-draft", err, { toastMessage: "暫存草稿失敗" })`
- [ ] `:383 adjustment preview failed` → 對應 toast message
- [ ] `:417 base orientation preview failed` → 對應 toast message
- [ ] `:546 poll processing job failed` → `silent: true`（背景 poll 不打擾使用者，但仍寫 console）
- [ ] `:888 poll adjustment job failed` → `silent: true`
- [ ] 跑 `npm run typecheck` 與 `npm run build` 確認沒 type 漂移。

## Test

- [ ] 新增 `web/scripts/test-error-reporting.cjs`，沿用既有 `.cjs` sandbox 風格：mock console.warn 與 toast hook，驗證 silent / non-silent 兩條路徑。
- [ ] `package.json` 加 `test:error-reporting`。

## Verification

- [ ] 本機觸發 5 種錯誤情境（例如後端關掉跑 preview）肉眼確認 toast 顯示與訊息正確。
- [ ] 背景 poll 失敗時 toast 不會洗版（silent 行為正確）。
- [ ] DevTools console 內仍看得到完整 stack（不要把 error 吞掉）。
- [ ] 沒有 production console.warn 殘留 in `web/src/pages/Preview.tsx`。
