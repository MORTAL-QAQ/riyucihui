# AGENTS.md

本文件为项目级指令文档，描述「AIGC 多模态日语词汇学习平台」的架构与部署方式，供 AI 编程助手快速上手。

## 项目概览

日语词汇学习平台，FastAPI + 原生前端 + PostgreSQL 全栈应用，支持 AI 生成单词/短文/语法/完型、VOICEVOX 日语发音、AI 配图、PDF 导出、学习记录与成就系统、管理员后台。

## 技术栈

- 后端：Python 3.12 / FastAPI / SQLAlchemy ORM / JWT (HS256, 24h) 认证
- 认证：**PyJWT**（签发/验证）+ **bcrypt**（密码哈希，72 字节限制，见 `auth.py`）——已从 python-jose/passlib 迁移
- 迁移：`create_all` + `run_migrations`（含跨进程文件锁）；**Alembic** 已引入（`backend/migrations/`）作为渐进式迁移框架，尚未切换运行时
- 前端：原生 HTML/JS/CSS，无构建步骤（`frontend/`），由 FastAPI `StaticFiles` 或 Nginx 托管
- 数据库：SQLite（开发，默认 `sqlite:///./data/words.db`）/ PostgreSQL 16（生产，经 Docker secrets 注入 `DATABASE_URL`）
- TTS：VOICEVOX 日语语音合成（容器 `http://voicevox:50021`）
- AI：DeepSeek API（单词/短文/语法/完型生成，客户端 `timeout=60s, max_retries=2`）、火山引擎豆包 Seedream（AI 配图）

## 后端代码结构（`backend/app/`）

- 入口 `main.py`：注册全部路由、`logging.basicConfig` 日志体系、`/api/health` 探测 DB（503 当 DB 不可用）、`mount("/", StaticFiles)` 托管前端
- 路由 `routers/`：auth、admin_api、words、study、grammar、essay、cloze、generate、voice、achievement、settings、export
  - AI/语音/图片付费端点均有 **IP 级限流**（`rate_limiter`，只信任 nginx 的 `X-Real-IP`）+ 用户级每日限额（北京时区零点重置）
  - 错误对外统一笼统信息，细节进日志（logging）
- 数据模型 `models.py`：User、UsageRecord、Word、StudyRecord、Essay、Cloze、GrammarCompare、Achievement、LoginHistory
  - `Word.image_base64` 为 **deferred 列**（常规查询不加载大字段，需要时显式 `undefer`）
  - 复合索引：study_records `(user_id,next_review_date)`/`(user_id,last_review_date)`、usage_records `(user_id,kind,created_at)`、words 多列 + pg_trgm
- 服务层 `services/`：ai_service（统一 `_chat()` 调用）、word_service、voicevox_manager、image_service、pdf_service（含 `_esc` 转义、`jlpt_color`、`generate_study_report_pdf`）、achievement_service、usage_service、rate_limiter、secrets、font_manager
- 配置 `config.py`：全部从环境变量读取；`SECRET_KEY`/`DATABASE_URL`/API Key 经 `services/secrets.py` 解析（env → Docker secrets → keyring → .env）；**未配置 SECRET_KEY 启动直接报错**；默认每日限额集中在 `config.DEFAULT_DAILY_*`
- CLI `cli.py`：管理命令（`create-admin`、`login-report`、`backfill-orphans` 等），从 backend/ 目录运行 `python -m app.cli ...`

## 前端结构（`frontend/`）

`index.html`（资源引用带 `?v={version}` 占位符，FastAPI 或 deploy.sh 注入内容哈希）+ `css/`（desktop.css / mobile.css）+ `js/`（api.js、app.js）。
- `api.js`：请求封装（`request`/`streamRequest`）、`setToken`/`getToken`/`clearToken`（外部禁止直接改写 token 状态）
- `app.js`：全部交互逻辑；SSE 流式统一走 `runStreamToPreview()`；错误统一走 `handleApiError()`

## 改进清单状态

`改进清单.md` 为全部优化项的跟踪清单（46 条）。**P0/P1/P2 全部完成，P3 完成 12/13**，仅 **#41（mobile.css mobile-first 重写）⏸ 暂缓**（高风险纯维护性改动，需专门 UI 回归）。处理新改动前先查看该文件，遵循其状态标记（☐/🔄/✅/⏸）。

## 部署

Docker Compose 部署到生产服务器，无 CI/CD，手动执行 `deploy.sh`。

- 服务器：`root@101.37.204.74`，项目路径 `/opt/riyucihui`
- 域名：`riyucihuixuexi.cn` / `www.riyucihuixuexi.cn`（Nginx + Let's Encrypt）
- SSH 已配置免密（本地 → 服务器）

**Docker Compose 服务**（`docker-compose.yml`，5 个服务）
- `voicevox`：TTS 引擎（端口 50021，容器 jp-vocab-voicevox）
- `postgres`：PostgreSQL 16（端口 5432，容器 jp-vocab-db，低内存参数，密码经 secrets）
- `backend`：FastAPI（端口 8000，容器 jp-vocab-backend，512M 内存上限，`Dockerfile` 构建）
  - **非 root 运行**：`entrypoint.sh` 以 root 修正数据卷属主后 `su appuser` 降权；容器内 secrets 为只读挂载
- `nginx`：反向代理（80/443，容器 jp-vocab-nginx，托管前端静态文件 + `/api/*` 反代 + `proxy_buffering off` 支持 SSE + healthcheck）
- `certbot`：证书管理（`certbot` profile，仅按需运行）

**密钥管理（Docker secrets）**：敏感值（`SECRET_KEY`/`DEEPSEEK_API_KEY`/`VOLCANO_API_KEY`/`DB_PASSWORD`/`DATABASE_URL`）从 `secrets/` 目录经 compose secrets 注入容器 `/run/secrets/`，不落入 environment。**服务器上 `secrets/` 目录权限必须为 700、文件 644**（非 root 容器用户需可读，只读挂载无法在容器内 chmod）。本地 `secrets/` 中的 API Key 为占位符，deploy.sh 不会覆盖服务器真实密钥。

**一键部署**：本地项目根目录运行 `bash deploy.sh`，流程为 tar 流同步 backend（--delete 语义，备份为 backend.bak）→ scp frontend/配置/scripts → 构建并重建 backend → 重启 nginx → 注入前端资源版本号 → 健康检查 → 注册每日备份 cron。`bash deploy.sh rollback` 可从 backend.bak 回滚。

**常用运维命令**（在服务器 `/opt/riyucihui` 执行）
- 日志：`docker compose logs -f`
- 重启/停止：`docker compose restart` / `docker compose down`
- 创建管理员：`docker compose exec backend python -m app.cli create-admin <用户> <密码>`
- 登录报告：`docker compose exec backend python -m app.cli login-report [--user <用户名>]`
- 孤儿数据回填：`docker compose exec backend python -m app.cli backfill-orphans`
- 数据库备份（每日 03:00 cron 自动执行，保留 14 份）：`bash scripts/backup_db.sh`，备份在 `backups/`
- 证书续期（续期后自动回拷 flat 路径并重启 nginx）：`bash scripts/cert-setup.sh renew`

**环境变量**（`.env` 本地开发用；生产由 secrets 注入）：`SECRET_KEY`、`DEEPSEEK_API_KEY`、`VOLCANO_API_KEY`、`DATABASE_URL`、`CORS_ORIGINS`（生产为具体域名 `https://riyucihuixuexi.cn,https://www.riyucihuixuexi.cn`）、`DEFAULT_DAILY_*`（默认限额）。
