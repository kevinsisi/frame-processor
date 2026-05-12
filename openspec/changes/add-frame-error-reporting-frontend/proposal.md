# Proposal: Frontend Error Reporting — Replace console.warn With User-Visible Surface

## Summary

`web/src/pages/Preview.tsx` 有 5 處 `console.warn(...)` 在錯誤路徑上（adjustment draft 存檔失敗、preview 失敗、輪詢 job 失敗等）。使用者看不到任何提示，瀏覽器 DevTools console 又是工程才會打開。建立統一 `errorReporting` util + 簡單 toast，把這些情境變成使用者可見的訊息，並把所有 `console.warn` 改走這個入口。

## Motivation

- 晴晴實際使用 Preview 時遇到 batch 偶發失敗，自己也說不上來「為什麼按了沒反應」。debug 時還要請她「打開 F12 看一下 console」極差體驗。
- 5 個 warn 點分散在不同 useEffect / fetch handler，行為各自為政；換成一個共用 `reportError(context, error)` 至少有一致格式。
- 未來如果要接 Sentry / 自架 log，集中入口才有 instrumentation 點。

## Scope

- 新增 `web/src/utils/errorReporting.ts`：
  - `reportError(context: string, error: unknown, options?: { silent?: boolean })` 函式
  - 預設行為：寫 `console.warn` + 經由 toast / 全域 error banner 顯示給使用者
  - `silent: true` 模式僅 console，給內部判斷可忽略的失敗（例如背景 poll 失敗預期不通知）
- 新增 `web/src/components/Toast.tsx`（或沿用既有 component 若存在）：簡易 toast container + dismissable item，3-5s 自動消失。
- 新增 `web/src/hooks/useToast.ts` 或 context provider 把 toast 狀態接出。
- `Preview.tsx` 5 處 `console.warn` 替換為 `reportError(...)` 對應呼叫；對使用者重要的失敗（adjustment 存檔 / preview 渲染）顯示 toast，背景 poll 走 `silent`。
- 補一支 `web/scripts/test-error-reporting.cjs` 驗證 `reportError` 對 `silent` 與非 silent 路徑的行為差異（toast hook mock）。

## Non-Goals

- 不接外部 error tracking 服務（Sentry / LogRocket）。
- 不重做整個錯誤處理框架；先處理 Preview 已知 5 點。
- 不把所有 `try/catch` 都改 — 只動目前 `console.warn` 那些。
- 不引入新狀態管理庫；toast 用 React context 就好。

## References

- 既有 5 個 warn 點：
  - `web/src/pages/Preview.tsx:354` save adjustment draft failed
  - `web/src/pages/Preview.tsx:383` adjustment preview failed
  - `web/src/pages/Preview.tsx:417` base orientation preview failed
  - `web/src/pages/Preview.tsx:546` poll processing job failed
  - `web/src/pages/Preview.tsx:888` poll adjustment job failed
- 既有 toast / 全域訊息？需要先在 `web/src/components/` 確認是否已有可重用元件，沒有再新建。
