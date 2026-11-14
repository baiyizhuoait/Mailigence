import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { NETEASE_IMAP_MAP, PROVIDER_PRESETS, type EmailAccount } from "../types";

interface Props {
  onClose: () => void;
  onCreated: (account: EmailAccount) => void;
  /** Which OAuth providers are configured (from /api/health). */
  oauthConfig?: { google: boolean; microsoft: boolean };
}

type Step = "form" | "testing" | "error";

/** Provider-specific "where do I find the app password" steps. */
const CONNECT_GUIDE: Record<string, { zh: string[]; en: string[] }> = {
  gmail: {
    zh: [
      "在 Google 账号中开启「两步验证」——这是应用专用密码的前提。",
      "打开「应用专用密码」页面（见下方链接），新建一个密码。",
      "复制生成的 16 位密码，粘贴到下方「应用密码」；不要填 Google 登录密码。",
      "企业/学校账号若看不到该页面，说明管理员已禁用，请改用 OAuth 登录。",
    ],
    en: [
      "Turn on 2-Step Verification — it is required for app passwords.",
      "Open the App Passwords page (link below) and create a password.",
      "Paste the 16-character password into “App password” below — not your Google password.",
      "If a work/school account cannot see that page, the admin disabled it; use OAuth instead.",
    ],
  },
  outlook: {
    zh: [
      "个人 Outlook / Hotmail 账户已停用 IMAP 密码登录，请使用下方「OAuth2 授权」。",
      "若 OAuth 未配置，需要管理员在 backend/.env 配置 Microsoft OAuth 凭据并重启。",
      "企业 Microsoft 365 租户若仍允许应用密码，可在安全设置中创建后粘贴到下方（多数租户已禁用）。",
      "不要使用普通登录密码，连接会直接失败。",
    ],
    en: [
      "Personal Outlook / Hotmail accounts no longer allow IMAP password login — use OAuth below.",
      "If OAuth is not configured, an admin must set Microsoft OAuth credentials in backend/.env and restart.",
      "Some Microsoft 365 tenants still allow app passwords; create one in security settings and paste it below.",
      "Don’t use your normal password — the connection will fail immediately.",
    ],
  },
  qq: {
    zh: [
      "登录 QQ 邮箱网页版，进入「设置 → 账号」。",
      "找到「POP3/IMAP/SMTP…服务」，开启 IMAP/SMTP 服务。",
      "按提示完成短信验证，生成 16 位「授权码」（只显示一次，请立即复制）。",
      "把授权码粘贴到下方「应用密码」，不要填 QQ 登录密码。",
    ],
    en: [
      "Sign in to QQ Mail on the web and open Settings → Account.",
      "Find the POP3/IMAP/SMTP services and enable IMAP/SMTP.",
      "Complete SMS verification to generate a 16-character authorization code (shown once).",
      "Paste the code into “App password” below — not your QQ password.",
    ],
  },
  netease: {
    zh: [
      "登录网易邮箱网页版，进入「设置 → POP3/SMTP/IMAP」。",
      "开启「IMAP/SMTP 服务」。",
      "点击「新增授权密码」，完成手机验证并复制授权密码（只显示一次）。",
      "把授权密码粘贴到下方「应用密码」，不要填登录密码。",
    ],
    en: [
      "Sign in to NetEase Mail on the web and open Settings → POP3/SMTP/IMAP.",
      "Enable the IMAP/SMTP service.",
      "Click “Add authorization password”, pass phone verification and copy the code (shown once).",
      "Paste the authorization password into “App password” below — not your login password.",
    ],
  },
  imap: {
    zh: [
      "在邮箱服务商帮助中心确认已开启 IMAP 访问。",
      "本工具只支持 SSL 加密，端口通常为 993；仅提供 143 + STARTTLS 的服务商暂不支持。",
      "若开启了两步验证，请先生成「应用专用密码」。",
      "在下方填写服务器地址与端口后，点击「验证并保存」。",
    ],
    en: [
      "Check your provider's help center and enable IMAP access.",
      "This tool only supports SSL (usually port 993); providers that only offer 143 + STARTTLS are not supported yet.",
      "If 2FA is enabled, generate an app-specific password first.",
      "Fill in the server and port below, then click “Validate & save”.",
    ],
  },
};

const GUIDE_FALLBACK = {
  zh: [
    "在服务商安全设置中开启 IMAP 访问。",
    "若开启了两步验证，请创建应用专用密码。",
    "本工具只支持 SSL（通常端口 993）。",
    "把应用密码粘贴到下方「应用密码」，再点「验证并保存」。",
  ],
  en: [
    "Enable IMAP access in your provider's security settings.",
    "If 2FA is on, create an app-specific password.",
    "This tool supports SSL only (usually port 993).",
    "Paste the app password into “App password” below, then click “Validate & save”.",
  ],
};

const GUIDE_LINK: Record<
  string,
  { zh: string; en: string; url: string }
> = {
  gmail: {
    zh: "Google 应用专用密码",
    en: "Google App Passwords",
    url: "https://myaccount.google.com/apppasswords",
  },
  outlook: {
    zh: "Microsoft 安全设置",
    en: "Microsoft security settings",
    url: "https://account.microsoft.com/security",
  },
  qq: {
    zh: "QQ 邮箱帮助中心",
    en: "QQ Mail help center",
    url: "https://service.mail.qq.com/",
  },
  netease: {
    zh: "网易邮箱帮助中心",
    en: "NetEase Mail help center",
    url: "https://help.mail.163.com/",
  },
};

export function AddAccountModal({ onClose, onCreated, oauthConfig }: Props) {
  const { t, lang } = useI18n();
  const [platform, setPlatform] = useState("gmail");
  const [emailLocal, setEmailLocal] = useState("");
  const [emailDomain, setEmailDomain] = useState("gmail.com");
  const [credential, setCredential] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [imapServer, setImapServer] = useState("");
  const [imapPort, setImapPort] = useState(993);
  // SMTP only matters from Stage 5 (sending); kept for the create payload.
  const [smtpServer] = useState("");
  const [smtpPort, setSmtpPort] = useState(465);
  const [step, setStep] = useState<Step>("form");
  const [error, setError] = useState("");
  // Open by default so a first-time user sees the steps before typing a
  // password; collapses only if they explicitly close it.
  const [guideOpen, setGuideOpen] = useState(true);

  // Escape closes the modal.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Re-open the guide when switching providers.
  useEffect(() => {
    setGuideOpen(true);
  }, [platform]);

  const preset = PROVIDER_PRESETS.find((p) => p.platform === platform)!;
  const isCustom = platform === "imap";
  // For preset platforms the email is local@domain; for custom IMAP the user
  // types the full address into emailLocal.
  const email = isCustom ? emailLocal : `${emailLocal}@${emailDomain}`;

  const effectiveImap = isCustom
    ? imapServer
    : platform === "netease"
      ? NETEASE_IMAP_MAP[emailDomain] || ""
      : preset.imap_server;
  const effectiveSmtp = isCustom ? smtpServer : preset.smtp_server;

  function onPlatformChange(p: string) {
    setPlatform(p);
    const ps = PROVIDER_PRESETS.find((x) => x.platform === p)!;
    setImapPort(ps.imap_port);
    setSmtpPort(ps.smtp_port);
    if (ps.domains.length > 0) {
      // Coming from custom IMAP (emailLocal may contain a full address): keep
      // only the part before '@' so it becomes the local part for the new domain.
      const local = emailLocal.split("@")[0];
      setEmailLocal(local);
      setEmailDomain(ps.domains.includes(emailDomain) ? emailDomain : ps.domains[0]);
    } else {
      // Going to custom IMAP: stitch local@domain into a full address.
      if (emailDomain && emailLocal) {
        setEmailLocal(`${emailLocal}@${emailDomain}`);
      }
      setEmailDomain("");
    }
  }

  async function handleTest() {
    setError("");
    if (!email || !credential) {
      setError(t("modal.errorEmptyFields"));
      return;
    }
    if (isCustom && !imapServer) {
      setError(t("modal.errorCustomImap"));
      return;
    }
    setStep("testing");
    try {
      await api.testConnection({
        auth_type: "app_password",
        platform,
        email,
        credential,
        imap_server: effectiveImap,
        imap_port: imapPort,
        smtp_server: effectiveSmtp,
        smtp_port: smtpPort,
      });
      // Passed -> create
      const account = await api.createAccount({
        auth_type: "app_password",
        platform,
        email,
        credential,
        display_name: displayName,
        imap_server: effectiveImap,
        imap_port: imapPort,
        smtp_server: effectiveSmtp,
        smtp_port: smtpPort,
      });
      onCreated(account);
    } catch (e) {
      setStep("error");
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleOAuth() {
    setError("");
    try {
      const provider = platform === "outlook" ? "microsoft" : "google";
      const { authorization_url } = await api.oauthStart(provider, platform);
      window.location.href = authorization_url;
    } catch (e) {
      setStep("error");
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <header className="modal-head">
          <h2>{t("modal.title")}</h2>
          <button className="icon-btn" onClick={onClose} aria-label={t("misc.close")}>
            ✕
          </button>
        </header>

        <div className="modal-body">
          <label className="field">
            <span>{t("modal.platform")}</span>
            <select
              value={platform}
              onChange={(e) => onPlatformChange(e.target.value)}
            >
              {PROVIDER_PRESETS.map((p) => (
                <option key={p.platform} value={p.platform}>
                  {p.label}
                  {p.supports_oauth ? t("modal.oauthSupported") : ""}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>{t("modal.email")}</span>
            {preset.domains.length > 0 ? (
              <div className="email-split">
                <input
                  type="text"
                  value={emailLocal}
                  onChange={(e) => setEmailLocal(e.target.value.replace(/@.*/, ""))}
                  placeholder={t("modal.account")}
                  autoCapitalize="none"
                  autoCorrect="off"
                />
                <span className="email-at">@</span>
                {preset.domains.length === 1 ? (
                  <span className="email-domain-fixed mono">{preset.domains[0]}</span>
                ) : (
                  <select
                    className="email-domain-select"
                    value={emailDomain}
                    onChange={(e) => setEmailDomain(e.target.value)}
                  >
                    {preset.domains.map((d) => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                )}
              </div>
            ) : (
              <input
                type="email"
                value={emailLocal}
                onChange={(e) => setEmailLocal(e.target.value)}
                placeholder="you@example.com"
                autoCapitalize="none"
                autoCorrect="off"
              />
            )}
          </label>

          {/* Self-service onboarding: visible before the password input */}
          <details
            className="connect-guide"
            open={guideOpen}
            onToggle={(e) => setGuideOpen(e.currentTarget.open)}
          >
            <summary>
              <span>{t("modal.guide.title", { platform: preset.label })}</span>
              {!guideOpen && (
                <span className="connect-guide-toggle">
                  {t("modal.guide.open")}
                </span>
              )}
            </summary>
            <ol>
              {(CONNECT_GUIDE[platform] ?? GUIDE_FALLBACK)[
                lang === "zh" ? "zh" : "en"
              ].map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ol>
            <p className="connect-guide-note">{t("modal.guide.final")}</p>
            <div className="connect-guide-foot">
              {effectiveImap && (
                <span className="mono dim">
                  {t("modal.guide.imapLine", {
                    server: `${effectiveImap}:${imapPort}`,
                  })}
                </span>
              )}
              {GUIDE_LINK[platform] && (
                <a
                  href={GUIDE_LINK[platform].url}
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  {GUIDE_LINK[platform][lang === "zh" ? "zh" : "en"]} ↗
                </a>
              )}
            </div>
          </details>

          <label className="field">
            <span>{t("modal.appPassword")}</span>
            <input
              type="password"
              value={credential}
              onChange={(e) => setCredential(e.target.value)}
              placeholder={t("modal.appPasswordHint")}
            />
            <small className="hint">
              {t("modal.appPasswordHelp")}
            </small>
          </label>

          <label className="field">
            <span>{t("modal.displayName")}</span>
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder={t("modal.displayNamePlaceholder")}
            />
          </label>

          {isCustom && (
            <div className="field-row">
              <label className="field">
                <span>{t("modal.imapServer")}</span>
                <input value={imapServer} onChange={(e) => setImapServer(e.target.value)} />
              </label>
              <label className="field narrow">
                <span>{t("modal.port")}</span>
                <input
                  type="number"
                  value={imapPort}
                  onChange={(e) => setImapPort(Number(e.target.value))}
                />
              </label>
            </div>
          )}

          {!isCustom && effectiveImap && (
            <p className="preset-line">
              <span className="mono">{effectiveImap}:{imapPort}</span>
              <span className="dim">{t("modal.imapPreset")}</span>
            </p>
          )}

          {preset.supports_oauth &&
            (oauthConfig?.[platform === "outlook" ? "microsoft" : "google"] ? (
              <button className="btn ghost full" onClick={handleOAuth} disabled={step === "testing"}>
                {t("modal.useOAuth")}
              </button>
            ) : (
              <p className="hint">
                {platform === "outlook"
                  ? t("modal.oauthNotConfiguredOutlook")
                  : t("modal.oauthNotConfiguredGoogle")}
              </p>
            ))}

          {step === "error" && error && (
            <div className="alert error">{error}</div>
          )}
        </div>

        <footer className="modal-foot">
          <button className="btn ghost" onClick={onClose}>
            {t("modal.cancel")}
          </button>
          <button className="btn primary" onClick={handleTest} disabled={step === "testing"}>
            {step === "testing" ? t("modal.saving") : t("modal.save")}
          </button>
        </footer>
      </div>
    </div>
  );
}
