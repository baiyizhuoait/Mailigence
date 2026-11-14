import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import type { SystemStatus } from "../types";

/** "135m" / "1h 35m" / "2d 4h" — compact enough for a status tile. */
function fmtUptime(seconds: number): string {
  const mins = Math.max(0, Math.floor(seconds / 60));
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ${mins % 60}m`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

/**
 * Settings ▸ System status.
 *
 * The "it proves itself stable" panel: DB round-trip, version/uptime, last
 * sync, IDLE listeners, recent failures and where AI runs (local vs cloud).
 * Purely read-only; every number comes from /api/system/status.
 */
export function SystemStatusPanel() {
  const { t } = useI18n();
  const [data, setData] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const rel = useCallback(
    (iso: string | null): string => {
      if (!iso) return t("settings.system.never");
      const mins = (Date.now() - new Date(iso).getTime()) / 60000;
      if (!Number.isFinite(mins) || mins < 1) return t("time.justNow");
      if (mins < 60) return t("time.minutesAgo", { n: Math.floor(mins) });
      if (mins < 1440) return t("time.hoursAgo", { n: Math.floor(mins / 60) });
      return t("time.daysAgo", { n: Math.floor(mins / 1440) });
    },
    [t],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await api.getSystemStatus());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const healthy = data?.status === "ok";
  const failures =
    (data?.failed_24h.import_jobs ?? 0) + (data?.failed_24h.sync_errors ?? 0);

  return (
    <section className="settings-section sys-section">
      <div className="sys-head">
        <div>
          <h3 className="settings-section-title">{t("settings.system")}</h3>
          <p className="settings-hint">{t("settings.system.sub")}</p>
        </div>
        <div className="sys-head-actions">
          {data && (
            <span className={`sys-badge ${healthy ? "ok" : "warn"}`}>
              <span className={`sys-dot ${healthy ? "ok" : "warn"}`} />
              {healthy ? t("sys.running") : t("sys.degraded")}
            </span>
          )}
          <button className="btn small ghost" onClick={load} disabled={loading}>
            {loading ? t("settings.system.checking") : t("settings.system.refresh")}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert error">
          {t("settings.system.loadFailed")}
          {error}
        </div>
      )}

      {data && (
        <>
          <div className="sys-grid">
            <div className={`sys-cell ${data.database.ok ? "ok" : "warn"}`}>
              <span className="sys-cell-label">
                <span className={`sys-dot ${data.database.ok ? "ok" : "warn"}`} />
                {data.database.ok
                  ? t("settings.system.dbOk")
                  : t("settings.system.dbFail")}
              </span>
              <span className="sys-cell-value mono">
                {t("settings.system.latency", { ms: data.database.latency_ms })}
              </span>
            </div>

            <div className="sys-cell">
              <span className="sys-cell-label">{t("settings.system.version")}</span>
              <span className="sys-cell-value mono">
                v{data.version}
                {" · "}
                {t("settings.system.uptime")} {fmtUptime(data.uptime_seconds)}
              </span>
              {data.demo_mode && (
                <span className="sys-cell-note">{t("settings.system.demo")}</span>
              )}
            </div>

            <div className="sys-cell">
              <span className="sys-cell-label">{t("settings.system.lastSync")}</span>
              <span className="sys-cell-value">{rel(data.last_sync_at)}</span>
              <span className="sys-cell-note">
                {t("settings.system.accounts", { n: data.accounts.total })}
              </span>
            </div>

            <div className={`sys-cell ${data.idle.errors ? "warn" : ""}`}>
              <span className="sys-cell-label">{t("settings.system.idle")}</span>
              <span className="sys-cell-value">
                {t("settings.system.idleValue", {
                  running: data.idle.running,
                  polling: data.idle.polling_only,
                })}
              </span>
              {data.idle.errors > 0 && (
                <span className="sys-cell-note warn">
                  {t("settings.system.idleErrors", { n: data.idle.errors })}
                </span>
              )}
            </div>

            <div className={`sys-cell ${failures ? "warn" : "ok"}`}>
              <span className="sys-cell-label">{t("settings.system.fail24h")}</span>
              <span className="sys-cell-value">
                {failures
                  ? t("settings.system.failCount", { n: failures })
                  : t("settings.system.failNone")}
              </span>
            </div>

            <div className={`sys-cell ${data.ai.local ? "ok" : ""}`}>
              <span className="sys-cell-label">AI</span>
              <span className="sys-cell-value">
                {!data.ai.configured
                  ? t("settings.system.aiOff")
                  : data.ai.local
                    ? t("settings.system.aiLocal")
                    : t("settings.system.aiCloud")}
              </span>
              {data.ai.configured && data.ai.model && (
                <span className="sys-cell-note mono">{data.ai.model}</span>
              )}
            </div>
          </div>

          {data.failed_24h.items.length > 0 && (
            <ul className="sys-fail-list">
              {data.failed_24h.items.map((item, idx) => (
                <li key={`${item.kind}-${item.id ?? item.account_id ?? idx}`}>
                  <span className="sys-fail-kind">{item.kind}</span>
                  <span className="sys-fail-error">{item.error || "—"}</span>
                  <span className="sys-fail-at mono">{rel(item.at)}</span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
