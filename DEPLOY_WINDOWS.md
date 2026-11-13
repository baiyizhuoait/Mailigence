# Windows 11 小主机部署清单（Cloudflare Tunnel + Docker）

目标：让小主机开机即自动提供公网体验入口，**无人值守、断电恢复、域名不变**。
适用：参赛评审 / 长期试用。全程只需在首次配置时操作，之后不用每天启动程序。

> 现有 `docker-compose.yml` 的三个服务已经带 `restart: unless-stopped`，端口也**只绑 127.0.0.1**（不对外暴露数据库和后端）。本文需要改的只有 `.env.docker` 和系统设置，不动业务代码。

---

## 0. 最终形态

```
评审浏览器
   │  https://demo.你的域名.com
   ▼
Cloudflare 边缘（自动 HTTPS）
   │  出站长连接（无需公网 IP / 无需端口映射）
   ▼
小主机：cloudflared 服务
   │  http://localhost:5173
   ▼
Docker Desktop → frontend(nginx) → backend(FastAPI) → postgres
```

四个进程都必须活着：`postgres`、`backend`、`frontend`、`cloudflared`。
重启电脑不会坏，只要 Docker 和 cloudflared 都能开机自启。

---

## 1. 前置条件

| 项 | 要求 |
|---|---|
| 系统 | Windows 11（64 位），已装 WSL2 |
| 内存 | 4 GB 以上（2 GB 也能跑，但构建镜像可能 OOM） |
| 磁盘 | 预留 10 GB（三个镜像约 1 GB + 数据卷） |
| 网络 | 有线网优先；家宽 NAT 即可，**不需要公网 IP** |
| 账号 | Cloudflare 账号 + 一个已托管在 Cloudflare 的域名 |
| 其他 | 小主机 BIOS 支持「来电自启」 |

---

## 2. 安装 Docker Desktop

```powershell
winget install --id Docker.DockerDesktop -e
```

安装后打开 Docker Desktop，完成以下设置：

1. **Settings → General**：勾选 `Start Docker Desktop when you sign in`
2. **Settings → Resources → WSL Integration**：确保已启用
3. 命令行确认：

```powershell
docker version
docker compose version
```

> **关键坑**：Docker Desktop 必须在**用户登录桌面后**才会启动。
> 因此必须开启自动登录（见第 6 节），否则重启后容器永远起不来，而你在别的电脑上只会看到链接打不开。

---

## 3. 放置项目与配置

把项目复制到小主机，例如 `D:\Mailigence`（不要带 `.venv`、`node_modules`、`.pginstall`、`.trae`、`frontend\dist`，这些都能重建）。

```powershell
cd D:\Mailigence
Copy-Item .env.docker.example .env.docker
notepad .env.docker
```

`.env.docker` 至少改这几项：

```ini
# 演示模式：自动播种 4 个虚构邮箱、约 70 封已分析邮件，不连任何真实服务器
DEMO_MODE=1

# 公网访问口令：自己生成一串随机字符（建议 16 位以上）
DEMO_ACCESS_TOKEN=请换成一串随机口令

# 无 AI Key 时用纯规则模式；要用 AI 简报/问答就填一个低额度测试 Key
AI_ANALYSIS_MODE=rules_only
AI_PROVIDER=openai
AI_API_KEY=
AI_BASE_URL=
AI_MODEL=

# 公网地址（只有使用 OAuth 登录才必须改）
PUBLIC_BASE_URL=https://demo.你的域名.com
```

注意事项：

- `DEMO_MODE=1` 与真实邮箱**不能共用同一个数据库**。小主机是全新数据卷，没有这个问题。
- `CREDENTIAL_ENCRYPTION_KEY` 留空即可，容器首次启动会自动生成并持久化到数据卷。
- `.env.docker` 含口令，**不要提交到仓库**，也不要截图外发。

---

## 4. 启动并自检

```powershell
cd D:\Mailigence
docker compose up -d --build
docker compose ps
```

三个容器都应是 `running` / `healthy`。本机自检：

```powershell
curl.exe http://localhost:5173/api/health
curl.exe -s http://localhost:5173/api/dashboard/summary
```

期望：health 返回 `{"status":"ok","demo_mode":true,...}`，summary 里 `pending_count`、`minutes_saved_today` 都大于 0。

浏览器打开 `http://localhost:5173`，应直接看到带演示数据的仪表盘。看不到就查日志：

```powershell
docker compose logs --tail 80 backend
```

---

## 5. 配置 Cloudflare Tunnel

### 5.1 安装 cloudflared

```powershell
winget install --id Cloudflare.cloudflared -e
cloudflared --version
```

### 5.2 在控制台创建隧道（推荐用 Token 方式，免配置文件）

1. 打开 Cloudflare Zero Trust → **Networks → Tunnels → Create a tunnel**
2. 选择 **Cloudflared**，命名如 `mailigence-demo`
3. 复制页面给出的 **Windows 安装命令**（形如 `cloudflared.exe service install eyJhIjoi...`）
4. 在该隧道里添加 **Public Hostname**：
   - Subdomain: `demo`
   - Domain: `你的域名.com`
   - Service: `HTTP` → `localhost:5173`
5. 保存后，域名解析会自动创建

### 5.3 把隧道装成 Windows 服务

以**管理员身份**打开 PowerShell，执行第 3 步复制的那条命令：

```powershell
cloudflared.exe service install <你的_TOKEN>
Get-Service cloudflared    # 状态应为 Running，启动类型 Automatic
```

> 用 Token 方式可以绕开「服务读不到配置文件」的经典问题（服务运行在 SYSTEM 账户下，找不到用户目录的 `config.yml`）。

### 5.4 验证

```powershell
curl.exe https://demo.你的域名.com/api/health
```

浏览器打开 `https://demo.你的域名.com`，第一次会要求输入访问口令，输入后进入演示仪表盘。**用自己的手机 4G 网络再测一次**，确认不是靠本机缓存。

---

## 6. 系统设置（决定能不能"无人值守"）

### 6.1 自动登录（Docker Desktop 的前提）

```powershell
netplwiz
```

取消勾选「要使用本计算机，用户必须输入用户名和密码」，确定后输入一次当前账户密码。

> 若 Windows 11 上该选项被隐藏，改用微软官方 Sysinternals **Autologon** 工具。
> 代价：任何能物理接触小主机的人可直接进入你的桌面。请把机器放在可控位置，并单独设置开机密码策略。

### 6.2 禁止睡眠 / 休眠

```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 5
powercfg /hibernate off
```

### 6.3 操作系统更新

设置 → Windows 更新 → **暂停更新**到比赛结束，并设置「活动时间」覆盖全天。
半夜自动重启会让链接断几分钟——容器会自动恢复，但没必要冒这个风险。

### 6.4 BIOS

重启进 BIOS，把 **Restore on AC Power Loss** 设为 `Power On`。
这样跳闸恢复供电后小主机会自动开机，不需要人跑去按电源键。

---

## 7. 验收清单（提交前逐项打勾）

- [ ] `docker compose ps` 三个容器都是 running
- [ ] `Get-Service cloudflared` 是 Running，启动类型 Automatic
- [ ] 无痕窗口打开 `https://demo.域名.com`，输入口令后能看到演示仪表盘
- [ ] 手机切 4G 能打开（排除局域网缓存）
- [ ] 点开一封邮件能看到正文（演示数据自带，不触网）
- [ ] 右上角 ⟲ 能重置演示数据
- [ ] 重启小主机，等 3 分钟，链接自动恢复
- [ ] 拔电再插电（或断电重启），链接自动恢复
- [ ] 深夜时段再打开一次，确认没有掉线

---

## 8. 常见故障

| 现象 | 原因 | 处理 |
|---|---|---|
| 链接 502 | 容器没起 / Docker 未启动 | `docker compose ps`；确认自动登录和 Docker 自启 |
| 链接 1033（隧道未连接） | cloudflared 服务停了 | `Get-Service cloudflared` → `Restart-Service cloudflared` |
| 打开是本机 5173 正常、公网不通 | Public Hostname 端口写错 | 必须是 `localhost:5173`，不是 8000 |
| 页面能开但接口 404 | 前端容器没起，只剩 nginx 页 | `docker compose logs frontend` |
| 显示"添加邮箱"而不是演示数据 | `DEMO_MODE` 没生效 | `.env.docker` 改完要 `docker compose up -d`（不是 restart） |
| 电脑重启后一直打不开 | 没开自动登录 | 见 6.1 |

常用的两条排障命令：

```powershell
docker compose logs --tail 100 backend
docker compose logs --tail 100 frontend
```

---

## 9. 后续更新与收尾

**代码更新后重新部署：**

```powershell
cd D:\Mailigence
git pull
docker compose up -d --build
```

**比赛结束后：**

1. Cloudflare 控制台删除隧道与 Public Hostname
2. `cloudflared service uninstall`
3. `docker compose down`（如需彻底清空再 `docker volume rm mailigence_pgdata`）
4. 撤销 `.env.docker` 里的访问口令

**定期清理（可选，每月一次）：**

```powershell
docker system prune -f
```
