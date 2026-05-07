import { useEffect, useState } from "react";

import { api, settingsAdminTokenAvailable } from "@/api/client";
import type { Settings } from "@/types";

import "./Settings.css";

const SETTINGS_TOKEN_STORAGE_KEY = "frame-processor:settings-token";

const SOURCE_LABEL: Record<Settings["gemini_api_keys"]["source"], string> = {
  db: "已在系統內管理",
  env: "使用主機環境設定（備援）",
  none: "未設定",
};

type BusyState = null | "save" | "sync" | "clear";

type FlashMessage = {
  kind: "ok" | "error";
  text: string;
};

export default function SettingsPage() {
  const [data, setData] = useState<Settings | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [textarea, setTextarea] = useState("");
  const [replace, setReplace] = useState(true);
  const [managerUrl, setManagerUrl] = useState("");
  const [settingsToken, setSettingsToken] = useState(() =>
    settingsAdminTokenAvailable
      ? ""
      : (localStorage.getItem(SETTINGS_TOKEN_STORAGE_KEY) ?? ""),
  );
  const [busy, setBusy] = useState<BusyState>(null);
  const [flash, setFlash] = useState<FlashMessage | null>(null);

  const refresh = async () => {
    try {
      const next = await api.getSettings();
      setData(next);
      setManagerUrl(next.key_manager_url ?? "");
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const handleSave = async () => {
    setBusy("save");
    setFlash(null);
    if (!settingsAdminTokenAvailable) {
      localStorage.setItem(SETTINGS_TOKEN_STORAGE_KEY, settingsToken);
    }
    try {
      const out = await api.updateGeminiKeys(
        { raw: textarea, replace },
        settingsToken,
      );
      setFlash({
        kind: "ok",
        text: `已儲存 · 接受 ${out.accepted_count} / 拒絕 ${out.rejected_count} · 目前共 ${out.stored_count} 把金鑰`,
      });
      setTextarea("");
      await refresh();
    } catch (err) {
      setFlash({
        kind: "error",
        text: `儲存失敗：${err instanceof Error ? err.message : String(err)}`,
      });
    } finally {
      setBusy(null);
    }
  };

  const handleSync = async () => {
    setBusy("sync");
    setFlash(null);
    if (!settingsAdminTokenAvailable) {
      localStorage.setItem(SETTINGS_TOKEN_STORAGE_KEY, settingsToken);
    }
    try {
      const out = await api.syncKeysFromManager(
        {
          trusted_only: true,
          replace: false,
        },
        settingsToken,
      );
      setFlash({
        kind: "ok",
        text: `從金鑰管理服務抓取 ${out.fetched} 把 · 新匯入 ${out.imported} · 略過重複 ${out.skipped} · 目前共 ${out.stored_count} 把金鑰`,
      });
      await refresh();
    } catch (err) {
      setFlash({
        kind: "error",
        text: `同步失敗：${err instanceof Error ? err.message : String(err)}`,
      });
    } finally {
      setBusy(null);
    }
  };

  const handleClear = async () => {
    setBusy("clear");
    setFlash(null);
    if (!settingsAdminTokenAvailable) {
      localStorage.setItem(SETTINGS_TOKEN_STORAGE_KEY, settingsToken);
    }
    try {
      await api.clearGeminiKeys(settingsToken);
      setFlash({ kind: "ok", text: "已清空系統內金鑰，將回到主機環境設定備援。" });
      await refresh();
    } catch (err) {
      setFlash({
        kind: "error",
        text: `清空失敗：${err instanceof Error ? err.message : String(err)}`,
      });
    } finally {
      setBusy(null);
    }
  };

  return (
    <main className="settings page">
      <section className="settings__hero">
        <div className="settings__kicker">SYSTEM SETTINGS</div>
        <h1 className="settings__title">
          Gemini Vision <em>金鑰管理</em>
        </h1>
        <p className="settings__lede">
          水平校正會使用這組 Gemini key pool。可批次貼上金鑰；清空後會回到 deploy host 的
          <code>GEMINI_API_KEY</code>。key-manager 只是可選同步來源，不是必要依賴。
        </p>
      </section>

      {loadError && (
        <div className="settings__notice settings__notice--error" role="alert">
          無法載入設定 · {loadError}
        </div>
      )}

      {data && (
        <section className="settings__panel">
          <div className="settings__panel-head">
            <h2>目前狀態</h2>
          </div>
          <dl className="settings__kv">
            <dt>模型</dt>
            <dd className="mono">{data.gemini_model}</dd>
            <dt>管理 Token</dt>
            <dd>{data.settings_admin_configured ? "已設定" : "未設定"}</dd>
            <dt>金鑰數量</dt>
            <dd className="mono">{data.gemini_api_keys.count}</dd>
            <dt>金鑰來源</dt>
            <dd>{SOURCE_LABEL[data.gemini_api_keys.source]}</dd>
            <dt>後 4 碼</dt>
            <dd className="mono settings__suffixes">
              {data.gemini_api_keys.masked_suffixes.length === 0
                ? "—"
                : data.gemini_api_keys.masked_suffixes.map((suffix) => (
                    <span key={suffix} className="settings__suffix-pill">
                      ...{suffix}
                    </span>
                  ))}
            </dd>
          </dl>
        </section>
      )}

      {data && !data.settings_admin_configured && (
        <div className="settings__notice settings__notice--error" role="alert">
          後端尚未設定 <code>SETTINGS_ADMIN_TOKEN</code>，目前只能查看狀態，不能匯入、清空或同步金鑰。
        </div>
      )}

      {!settingsAdminTokenAvailable && (
        <section className="settings__panel">
          <div className="settings__panel-head">
            <h2>管理權限</h2>
            <p className="settings__hint">
              修改金鑰需要 deploy host 的 <code>SETTINGS_ADMIN_TOKEN</code>。
              Token 只存在此瀏覽器，不會回傳到狀態 API。
            </p>
          </div>
          <label className="settings__field">
            <span>Settings Admin Token</span>
            <input
              type="password"
              className="settings__input mono"
              value={settingsToken}
              onChange={(event) => setSettingsToken(event.target.value)}
              spellCheck={false}
              autoComplete="off"
            />
          </label>
        </section>
      )}

      <section className="settings__panel">
        <div className="settings__panel-head">
          <h2>批次匯入 Gemini 金鑰</h2>
          <p className="settings__hint">
            支援逗號或換行分隔；可直接貼 <code>GEMINI_API_KEY=AIza...</code> 或
            <code>export GEMINI_API_KEY=AIza...</code>。
          </p>
        </div>
        <textarea
          className="settings__textarea mono"
          rows={8}
          placeholder={"AIzaSy...,AIzaSy...\n# 或一行一把金鑰\nAIzaSy..."}
          value={textarea}
          onChange={(event) => setTextarea(event.target.value)}
          spellCheck={false}
        />
        <div className="settings__row">
          <label className="settings__check">
            <input
              type="checkbox"
              checked={replace}
              onChange={(event) => setReplace(event.target.checked)}
            />
            <span>取代既有金鑰（取消勾選＝合併）</span>
          </label>
          <div className="settings__actions">
            <button
              type="button"
              className="cta cta--primary"
              onClick={handleSave}
              disabled={
                busy !== null ||
                textarea.trim().length === 0 ||
                (!settingsAdminTokenAvailable && settingsToken.trim().length === 0) ||
                data?.settings_admin_configured === false
              }
            >
              {busy === "save" ? "儲存中..." : "儲存"}
            </button>
            <button
              type="button"
              className="cta cta--quiet"
              onClick={handleClear}
              disabled={
                busy !== null ||
                data?.gemini_api_keys.source !== "db" ||
                (!settingsAdminTokenAvailable && settingsToken.trim().length === 0) ||
                data?.settings_admin_configured === false
              }
            >
              {busy === "clear" ? "清空中..." : "清空系統內金鑰"}
            </button>
          </div>
        </div>
      </section>

      {managerUrl ? (
        <section className="settings__panel">
          <div className="settings__panel-head">
            <h2>可選：從金鑰管理服務同步</h2>
            <p className="settings__hint">
              這只是可選捷徑；frame-processor 不依賴 key-manager。來源由後端
              <code>KEY_MANAGER_URL</code> 控制，避免瀏覽器提供任意內網 URL。
            </p>
          </div>
          <div className="settings__row settings__row--top">
            <label className="settings__field">
              <span>金鑰管理服務 URL</span>
              <input
                type="url"
                className="settings__input mono"
                value={managerUrl}
                readOnly
                spellCheck={false}
              />
            </label>
            <div className="settings__actions">
              <button
                type="button"
                className="cta cta--primary"
                onClick={handleSync}
                disabled={
                  busy !== null ||
                  (!settingsAdminTokenAvailable && settingsToken.trim().length === 0) ||
                  data?.settings_admin_configured === false
                }
              >
                {busy === "sync" ? "同步中..." : "同步"}
              </button>
            </div>
          </div>
        </section>
      ) : (
        <div className="settings__notice settings__notice--info" role="status">
          未設定 <code>KEY_MANAGER_URL</code>。這是正常狀態；請直接貼上 Gemini API key 匯入。
        </div>
      )}

      {flash && (
        <div
          className={`settings__notice settings__notice--${flash.kind}`}
          role={flash.kind === "error" ? "alert" : "status"}
        >
          {flash.text}
        </div>
      )}
    </main>
  );
}
