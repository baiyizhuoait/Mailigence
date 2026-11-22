English | [简体中文](./README.md)

# Mailigence — Multi-Account Email Dashboard with AI Analysis

[![CI](https://github.com/baiyizhuoait/Mailigence/actions/workflows/ci.yml/badge.svg)](https://github.com/baiyizhuoait/Mailigence/actions/workflows/ci.yml)

> Turn scattered inboxes into one intelligent action list.

Mailigence is a self-hosted email aggregation and AI analysis tool. It brings Gmail / Outlook / QQ Mail / 163 — any IMAP-capable mailbox — into one interface, and uses AI (or pure rule-based logic) to automatically handle **classification, priority ranking, a to-do queue, schedule extraction, and a daily digest**. One look in the morning and you know exactly what today needs.

<p align="center">
  <img src="docs/screenshots/dashboard.png" alt="Mailigence dashboard: priority queue, AI daily briefing and schedule" width="920">
</p>

<p align="center">
  <sub>Screenshots use the built-in demo dataset and contain no real email</sub>
</p>

## ⏱️ Understand it in 30 seconds

1. **Connect** — Gmail / Outlook / QQ / 163 via app-specific password or OAuth2; any IMAP mailbox works.
2. **Classify** — AI (or a zero-cost rules-only mode) tags every email with a category, a priority and a suggested action; ads are archived automatically.
3. **Act** — The dashboard keeps only "the few emails that truly need handling today", alongside an AI daily briefing and an auto-extracted schedule.
4. **Save time** — The "time saved today" card uses `auto-classified mails × 15s + queue items handled × 45s`, so the minutes you save are visible every day.

| Priority queue (with time estimates) | The same UI on mobile |
|---|---|
| <img src="docs/screenshots/queue.png" width="430"> | <img src="docs/screenshots/mobile.png" width="250"> |

<p>
  <img src="https://img.shields.io/badge/stack-FastAPI%20%2B%20React%20%2B%20PostgreSQL-4a9eff" alt="stack">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
  <img src="https://img.shields.io/badge/PRs-welcome-orange" alt="prs">
</p>

## ✨ Features

### 🤖 AI Intelligence
- **AI-powered analysis** — Every email is automatically classified (work / meetings / finance / notifications / ads…), scored by priority, and given a suggested action. A pure rule-based mode is also available for zero-cost, fully offline operation
- **AI memory system** — Tell the AI your preferences in the chat box on the Settings page (e.g. "always treat Amazon promos as ads", "pin my boss's emails to the top"), and it distills them into memories that are applied to every subsequent analysis — it gets smarter the more you use it
- **Dynamic categories** — No manual setup needed: the AI automatically discovers and creates new categories as they appear in your mail. You can also add / rename / delete categories yourself; deleting a category re-queues its emails for re-classification
- **Schedule extraction** — AI pulls meetings, deadlines, and appointments from email bodies — understanding natural phrases like "tomorrow", "next Monday" or "3pm" — and groups them into Today / Tomorrow / This Week / Upcoming
- **AI config management** — Keep multiple provider configs side by side (cloud and local: DeepSeek, local Ollama, LM Studio…) and switch the active one with one click; model lists are auto-probed
- **AI reply drafts** — Generate 1-2 editable reply drafts while reading an email. QQ / 163 / app-specific-password accounts can send directly from the app (SMTP), Outlook goes through Microsoft Graph, and Gmail OAuth accounts require copying the body into the original mailbox to send
- **AI mail Q&A** — Ask natural-language questions across all mailboxes (e.g. "what events did school announce recently?"); answers are grounded in retrieved email snippets and come with clickable citation cards that jump to the message

### 🔍 Search
- **Full-text search** — A global top-bar search box available on every page, with 300ms debounced live preview and a dedicated results page with account / category / date filters; matched snippets are highlighted (`<mark>`)
- **Semantic search (optional)** — Enabling an embedding model adds vector recall to handle "related topic but no literal overlap" and cross-language queries; keyword + vector + structured filters are fused with RRF

### 📬 Reading & Handling
- **Multi-account aggregation** — Manage all your mailboxes (Gmail / Outlook / QQ Mail / 163 / any IMAP server) from one dashboard, with support for both app-specific passwords and OAuth2; importing history preserves the original read/unread state
- **Batch actions** — Select emails across accounts and mark as read / archive / star in one click, as efficiently as a mainstream mail client
- **Read full emails without logging in** — Open any email and read its complete body on demand (fetched from the server) inside a safe sandbox
- **To-do dashboard** — A bento layout combining an AI daily briefing, a schedule timeline, statistics, and a priority queue; handled emails automatically drop out of the queue, and older ones auto-archive
- **Priority queue** — Click an email in the queue to expand and read it directly, without jumping back to the inbox
- **Real-time sync** — IMAP IDLE pushes new emails instantly; servers without IDLE fall back to 2-minute polling; a background sweep re-scans missed / uncategorized emails every 60 seconds
- **Reply tracking** — Identifies emails that still need a reply, with one-click jump to respond

### 🎨 Personalization
- **11 accent colors + custom palette** — Amber / Blue / Green / Purple / Coral / Teal / Indigo / Pink / Orange / Cyan / Slate, or pick any color with the built-in palette
- **Custom colors** — Assign a color to every mailbox account and email category so you can tell sources and groupings apart at a glance
- **Dark / light themes & bilingual UI** — One-click dark/light switching, seamless Chinese / English switching

### 📊 Data & Control
- **Ad filtering** — Automatically detects marketing/promotional email, with a blocklist manager and one-click bulk cleanup from the ads panel
- **Analytics** — View email distribution, priority breakdown, and top senders by day / week / month

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+ · FastAPI · SQLAlchemy 2.0 (async) · psycopg 3 |
| Frontend | React 18 · TypeScript · Vite |
| Database | PostgreSQL 14+ |
| Email | IMAP (imaplib) · IMAP IDLE |
| AI | OpenAI-compatible / Anthropic / any local inference server (Ollama · LM Studio · vLLM · llama.cpp) · multi-config with one-click switching |

## 🚀 Quick Start

This repo offers two independent launch paths — pick either:

> Just want a look? Set `DEMO_MODE=1` in `.env.docker` and run `docker compose up -d`: it seeds 4 fictional mailboxes and ~70 already-classified emails and **connects to no real account**. The ⟲ button in the dashboard header resets it at any time.

| Path | Best for | Command / action |
|---|---|---|
| **Cross-platform Docker** (recommended) | macOS / Linux / Windows (needs Docker) | `docker compose up -d` |
| **Windows without Docker** | Windows (no Docker required) | double-click `start.bat` |

### Docker one-click start (cross-platform, recommended)

Requirements: **Docker 24+** (with the compose plugin).

No Python / Node.js / PostgreSQL install needed — one command brings up all three services (database + backend + frontend):

```bash
# 1. Clone the repo
git clone <repo-url> && cd Mailigence

# 2. Prepare environment variables (AI keys, OAuth, ... — leaving them empty
#    still works in pure-rules mode)
cp .env.docker.example .env.docker

# 3. Start everything (first run builds the images, give it a minute)
docker compose up -d
```

Then open:

- Frontend: **http://localhost:5173**
- Backend API: http://localhost:8000 (health: http://localhost:8000/api/health)
- Database: localhost:5432 (`mailigence` / `mailigence_dev_pw` / `mailigence`)

Notes:

- **Auto schema**: the backend container creates all tables, seeds built-in categories and applies incremental migrations on startup — no manual SQL.
- **Encryption key**: if `CREDENTIAL_ENCRYPTION_KEY` is left empty, the backend container generates one on **first start** and persists it to a named volume, so restarts never rotate it (rotating would make stored credentials undecryptable).
- **Persistence**: DB data and the encryption key live in the named volumes `mailigence_pgdata` and `mailigence_backend_env`.
- Logs: `docker compose logs -f backend`
- Stop (keep data): `docker compose down`
- Full reset (drops data, use with care): `docker compose down -v`
- If you previously ran the old DB-only compose file, run `docker compose down` first to avoid container-name conflicts.

### Experience it without a mailbox: demo mode

No real mailbox is needed for reviews or trials. With `DEMO_MODE=1` and a backend restart, the first start seeds **4 fictional mailboxes and ~70 already-classified emails** and disables every networked background task (IMAP IDLE, scheduled sync, AI analysis, embeddings) — so the dashboard, priority queue, schedule, search and reports are fully browsable **without an AI key**.

- All demo data is fictional; mailbox domains are `@demo.mailigence.local`, and no real server is ever contacted.
- The ⟲ button in the dashboard header calls `POST /api/demo/reset` to restore the initial data.
- In demo mode the "add mailbox / sync / import" endpoints return 403 — read-only, so no real credentials can be stored by accident.
- If the demo instance is public, also set `DEMO_ACCESS_TOKEN=<token>`: the first visit must carry `?token=<token>`, after which the browser keeps a 7-day cookie.
- To let visitors try AI Q&A / AI reply drafts, set `AI_API_KEY` (keep `AI_ANALYSIS_MODE=auto`). The app rate-limits by `DEMO_AI_IP_HOURLY_LIMIT` (per visitor per hour, default 20) and `DEMO_AI_DAILY_LIMIT` (per instance per day, default 300); over the limit returns 429, so a public instance's key cannot be drained.

### Windows — one-click start without Docker (start.bat / start.ps1)

No Docker required. Prerequisites: **Python 3.11 or 3.12** (3.13+ has no wheels for the pinned dependencies — use `MAILIGENCE_PYTHON` to point at a 3.11/3.12 interpreter), and **Node.js 18+** (tick "add to PATH" during install).

1. Double-click `start.bat` in the project root, or run `powershell -ExecutionPolicy Bypass -File start.ps1` from PowerShell
2. On first run the script automatically:
   - Detects PostgreSQL — prefers the bundled portable build at `\.pginstall\pgsql`, falls back to a system install
   - Runs `initdb` to initialize the data directory and starts the database on first launch
   - Creates the `mailigence` role and database if missing
   - Creates a Python venv and installs backend dependencies
   - Generates `backend\.env` with a fresh encryption key
   - Installs frontend dependencies
   - Starts the backend (:8000) + frontend (:5173) and opens the browser → http://localhost:5173

To stop: double-click `stop.bat` (run `.\stop.ps1 -StopDb` to also stop the database).

> **Portable PostgreSQL**: download
> `https://get.enterprisedb.com/postgresql/postgresql-16.6-1-windows-x64-binaries.zip`,
> unzip it and place the `pgsql` folder at `\.pginstall\pgsql`; the script picks it up automatically.

### Manual start (macOS / Linux / advanced)

Requirements: Python 3.11+, Node.js 18+, PostgreSQL 14+

### 1. Database

```bash
# Create the database and user (PostgreSQL example)
psql -U postgres -c "CREATE USER mailigence WITH PASSWORD 'mailigence_dev_pw';"
psql -U postgres -c "CREATE DATABASE mailigence OWNER mailigence;"
```

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   /   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then edit .env — see "Configuration" below
# Generate the encryption master key (required; used to encrypt mailbox credentials)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Start (tables are created automatically on first run; on Windows always use
# run.py — ProactorEventLoop is incompatible with psycopg)
python run.py
# or: uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

Open http://localhost:5173, add a mailbox account, and you're ready to go.

## ⚙️ Configuration (backend/.env)

See `.env.example`. Key settings:

```ini
# Database connection (the DB created above; psycopg driver, 127.0.0.1 avoids
# IPv6 resolution issues, and sslmode=disable stops the portable PostgreSQL
# build from crashing on SSLRequest under Windows)
DATABASE_URL=postgresql+psycopg://mailigence:mailigence_dev_pw@127.0.0.1:5432/mailigence?sslmode=disable

# Encryption master key — required; encrypts mailbox passwords and OAuth credentials
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CREDENTIAL_ENCRYPTION_KEY=

# ---- AI analysis (optional — without it the app runs in rules-only mode) ----
# Analysis mode: auto (AI first, falls back to rules) | ai_only | rules_only
AI_ANALYSIS_MODE=auto
# Provider: openai (OpenAI-compatible: OpenAI / DeepSeek / Kimi / Qwen / GLM / Ollama) | anthropic
AI_PROVIDER=openai
AI_API_KEY=
AI_BASE_URL=https://api.deepseek.com/v1     # example: DeepSeek
AI_MODEL=deepseek-chat

# ---- Semantic search (optional — without it, retrieval is keyword-only) ----
AI_EMBEDDING_MODEL=          # empty -> text-embedding-3-small (requires pgvector)
EMBEDDING_DIM=1536           # must match the embedding model (nomic-embed-text = 768)
```

## 🤖 AI Config Management (multiple profiles)

Settings → **AI email analysis** → **AI configs**: save **multiple cloud and local providers side by side**, switch between them at any time, and never overwrite each other.

### Basic workflow

1. **New config** — fill in:
   - **Name**: anything, e.g. `DeepSeek cloud` / `Local Ollama` / `Local LM Studio`
   - **Type**: `OpenAI-compatible` (OpenAI / DeepSeek / Kimi / Qwen / GLM / **Ollama / LM Studio / vLLM / llama.cpp / oneAPI** all use this) | `Anthropic` | `Rules only (no AI)`
   - **Base URL**: free text, e.g. `https://api.deepseek.com/v1` or `http://localhost:11434/v1`
   - **Model**: type it manually, or click **Probe model list** to fetch candidates from `{Base URL}/models` (click one to fill it in — still editable; a failed probe never blocks manual entry)
   - **API key**: required for cloud; **leave blank** for local servers without auth (Ollama / LM Studio)
2. **Save** — the first config becomes active automatically; for later ones press **Set as active** on the card
3. **Test connection** — the card's button requests `{Base URL}/models` (works for every type)
4. **Edit / Delete** — change connection details anytime; deleting the active config automatically activates the first remaining one
5. When creating a config, switching the type auto-fills the **last-used Base URL / model** for that type

> Base URL and model are **free text and never restricted by a dropdown** — probing is only a convenience. If an endpoint doesn't support it, just type the values.

### Analysis modes (global)

- **Smart mode (recommended)** — uses AI when configured, falls back to rules otherwise
- **AI-only mode** — always calls the AI provider
- **Rules-only mode** — no AI calls at all; pure keyword/header analysis, zero cost, zero dependencies

> Saved API keys are stored **encrypted** in the database; leaving the key blank while editing keeps the stored one. Config changes invalidate the analysis cache automatically.

### Common cloud endpoints

| Provider | Base URL | Model example |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Moonshot (Kimi) | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| Qwen (Tongyi) | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| Zhipu GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |
| Anthropic Claude | `https://api.anthropic.com/v1` | `claude-sonnet-4-...` |

### Local Ollama setup (free, offline, private)

1. **Install Ollama** from https://ollama.com/ (Windows installer, macOS drag-and-drop, or `curl -fsSL https://ollama.com/install.sh | sh` on Linux)
2. **Pull a model** (a mid-size one is plenty for email analysis):

   ```bash
   ollama pull qwen2.5:7b
   ollama list          # show installed models
   ```

3. **Verify the service**: Ollama listens on `http://localhost:11434` by default, and its **OpenAI-compatible endpoint** is `http://localhost:11434/v1`. Opening `http://localhost:11434/v1/models` in a browser should return JSON
4. **Create a config in Mailigence**:
   - Name: `Local Ollama`
   - Type: **OpenAI-compatible**
   - Base URL: `http://localhost:11434/v1`
   - Model: `qwen2.5:7b` (or probe to auto-fill)
   - API key: **leave blank** (no auth needed locally)
5. **Save → Set as active**: classification, priority, schedule extraction, reply drafts and chat Q&A all run on the local model — it works offline.

> **Local semantic search (optional)**: Ollama also exposes an OpenAI-compatible `/v1/embeddings`. Pull `ollama pull nomic-embed-text` and enter `nomic-embed-text` in "Semantic search model". Note its vector dimension is **768** (vs the default 1536 for text-embedding-3-small): on a fresh database set `EMBEDDING_DIM=768` in `backend/.env` before first startup; on an existing database, drop the embedding column and restart (vectors regenerate automatically).

> **Other local inference servers work the same way** — LM Studio (`http://localhost:1234/v1`), vLLM / llama.cpp server / oneAPI, anything exposing an OpenAI-compatible `/v1` endpoint. One "OpenAI-compatible" config covers all of them; no tool-specific setup needed.

### Local small / thinking model adaptation

**Symptoms**: with a small local model (especially "thinking" models such as the qwen3 family), reply-draft / chat Q&A generation is extremely slow (tens of seconds to minutes), or fails with an "unparseable reply draft" error, or returns empty output.

**Root cause**: thinking models called through the OpenAI-compatible `/v1/chat/completions` endpoint emit a long "reasoning" block first, exhausting the `max_tokens` budget — the actual answer (`content`) never gets produced (empty), or the JSON gets cut off, so parsing fails. The time is spent mostly on thinking.

**What the app does automatically**:

- Detects local Ollama (port 11434) and routes calls through its native `/api/chat` with `think: false` to disable reasoning (measured: ~46s → ~3.5s)
- Raises the token budget (drafts / Q&A: 2048) and timeout (120s), and simplifies the prompts
- Provides tolerant JSON parsing: repairs trailing commas and raw newlines inside strings, and accepts single-object / wrapped-array output shapes

**If it is still slow or failing, check in order**:

1. Run `ollama list` and make sure the configured model name matches **exactly** (case and `:tag`, e.g. `qwen3:8b` — not just `qwen3`)
2. Confirm the Ollama service is running (opening `http://localhost:11434/v1/models` in a browser should return JSON)
3. Switch to a model with a **larger context window** (e.g. `qwen2.5:14b` / `qwen3:14b`); `ollama show <model>` shows its context length
4. Read the hint after `LLM HTTP ...` in the backend logs — it distinguishes "input too long" from "invalid model name"

## 📁 Project Structure

```
mailigence/
├── start.bat / start.ps1      # Windows one-click start (auto-initialises DB and dependencies)
├── stop.bat / stop.ps1        # One-click stop (stop.ps1 -StopDb also stops the DB)
├── docker-compose.yml         # Cross-platform Docker: postgres + backend + frontend
├── .env.docker.example        # Env template for Docker (copy to .env.docker)
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes (accounts/dashboard/settings/reports…)
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Email sync, AI analysis, IMAP IDLE, encryption…
│   ├── Dockerfile        # Backend image (python:3.11-slim, psycopg[binary] no build tools)
│   ├── entrypoint.sh     # Container entrypoint (auto-generates and persists the encryption key)
│   ├── run.py            # Local launcher (Windows-compatible)
│   ├── .env.example      # Environment variable template (local dev)
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile        # Multi-stage (node build → nginx static hosting)
│   ├── nginx.conf        # SPA fallback + /api reverse proxy to backend
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── api.ts        # Backend API client
│   │   └── i18n.tsx      # Chinese/English copy
│   └── package.json
└── .gitignore
```

## ❓ FAQ

**Startup fails with `Psycopg cannot use the 'ProactorEventLoop'`?** On Windows, Python 3.13 uses ProactorEventLoop by default, which is incompatible with psycopg's async mode, and uvicorn forces its own event loop. Start with `python run.py` (the script pins SelectorEventLoop).

**`pip install -r requirements.txt` fails?** Dependencies use `psycopg[binary]`, which ships prebuilt wheels for every platform (including Windows / Python 3.13) — no MSVC toolchain required.

**Database connection fails (IPv6 / SSLRequest)?** Make sure `DATABASE_URL` in `.env` uses `127.0.0.1` rather than `localhost`, and keeps `?sslmode=disable` (`app/database.py` also forces SSL off via `connect_args`).

**Adding a mailbox fails?** Most providers require an "authorization code" / app-specific password rather than your regular login password (for QQ Mail / 163, enable IMAP in the web settings and generate an authorization code first).

**Can I use it without an AI key?** Yes. Choose "rules-only mode", or keep the default smart mode (it falls back to rules when AI is unconfigured). Every feature (classification, priority, schedule extraction) has a rule-based fallback implementation.

**How do I use Ollama?** Full tutorial above: [Local Ollama setup](#local-ollama-setup-free-offline-private) — install Ollama → `ollama pull qwen2.5:7b` → create an "OpenAI-compatible" config in Settings → AI configs with Base URL `http://localhost:11434/v1`, leave the key blank, save and set it active.

**Local model is slow / drafts fail to parse?** See [Local small / thinking model adaptation](#local-small--thinking-model-adaptation) above: thinking models (e.g. qwen3) burn the token budget on reasoning — the app already disables thinking for Ollama and raises budget/timeout. If it still fails, check the model name against `ollama list` (case and `:tag`), or switch to a model with a larger context window.

**Why is semantic search (vector retrieval) unavailable?** It needs the **pgvector** extension in PostgreSQL. The Docker deployment ships it (`pgvector/pgvector:pg16` image); the bundled portable build requires installing pgvector yourself — otherwise the startup log shows `pgvector not available — semantic search disabled` and retrieval falls back to keyword-only (chat Q&A states "keyword retrieval" in its system prompt). Nothing else is affected.

**Can't find emails that are topically related but share no literal keywords?** That's exactly what semantic search fixes: once an embedding model is configured and pgvector is available, retrieval automatically upgrades to keyword + vector dual recall.

**Port conflicts?** Backend defaults to 8000, frontend to 5173. Change these via `APP_PORT` in `.env` and in `vite.config.ts`.

**The one-click script says PostgreSQL was not found?** Unzip the portable build into `\.pginstall\pgsql` and retry, or install PostgreSQL and add it to PATH.

**Database port is taken / blocked by a firewall?** Change the port in `DATABASE_URL` in `backend\.env` (e.g. `@127.0.0.1:5433/`) — the launcher reads the port from `.env`, no extra configuration needed.

**How do I migrate / back up data?** The portable build stores its data in `\.pginstall\pgdata` — copy that directory to migrate everything, or export with `pg_dump`.

**How do I run it on macOS/Linux?** See [Manual start](#manual-start-macos--linux--advanced) above; the **recommended** path is `docker compose up -d` from the repo root, which starts every service (see [Docker one-click start](#docker-one-click-start-cross-platform-recommended)).

## 🔒 Security Notes

- Mailbox passwords and OAuth credentials are encrypted at rest using Fernet (master key in `CREDENTIAL_ENCRYPTION_KEY`)
- AI API keys are encrypted at rest as well; `.env` is excluded via `.gitignore` — never commit real keys
- Plaintext credentials only exist in memory momentarily, while establishing an IMAP connection

## 📄 License

MIT

---

<p align="center">
  Built with 💛 · <a href="https://github.com/baiyizhuoait/Mailigence">GitHub</a>
</p>
