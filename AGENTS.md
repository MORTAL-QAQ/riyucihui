# AGENTS.md

本文件为项目级指令文档，描述「AIGC 多模态日语词汇学习平台」的架构与部署方式，供 AI 编程助手快速上手。

## 项目概览

日语词汇学习平台，FastAPI + 原生前端 + PostgreSQL 全栈应用，支持 AI 生成单词/短文/语法/完型、VOICEVOX 日语发音、AI 配图、PDF 导出、学习记录与成就系统、管理员后台。

## 技术栈

- 后端：Python 3.12 / FastAPI / SQLAlchemy ORM / JWT (HS256, 24h) 认证
- 前端：原生 HTML/JS/CSS，无构建步骤（`frontend/`），由 FastAPI `StaticFiles` 或 Nginx 托管
- 数据库：SQLite（开发，默认 `sqlite:///./data/words.db`）/ PostgreSQL 16（生产，`DATABASE_URL` 切换）
- TTS：VOICEVOX 日语语音合成（本地引擎 `linux-cpu-arm64/run` 或容器 `http://voicevox:50021`）
- AI：DeepSeek API（单词/短文/语法/完型生成）、火山引擎豆包 Seedream（AI 配图）

## 后端代码结构（`backend/app/`）

- 入口 `main.py`：注册全部路由并 `mount("/", StaticFiles)` 托管前端
- 路由 `routers/`：auth、admin_api、words、study、grammar、essay、cloze、generate、voice、achievement、settings、export
- 数据模型 `models.py`：User、UsageRecord、Word、StudyRecord、Essay、Cloze、GrammarCompare、Achievement、LoginHistory
- 服务层 `services/`：ai_service、word_service、voicevox_manager、image_service、pdf_service、achievement_service、usage_service、rate_limiter、secrets、font_manager
- 配置 `config.py`：全部从环境变量读取，敏感值经 `services/secrets.py` 解析（支持 Docker secrets）
- CLI `cli.py`：管理命令（`create-admin`、`login-report` 等），从 backend/ 目录运行 `python -m app.cli ...`

## 前端结构（`frontend/`）

`index.html` + `css/`（desktop.css / mobile.css）+ `js/`（api.js、app.js），app.js 含全部交互逻辑。

## 部署

Docker Compose 部署到生产服务器，无 CI/CD，手动执行 `deploy.sh`。

- 服务器：`root@101.37.204.74`，项目路径 `/opt/riyucihui`
- 域名：`riyucihuixuexi.cn` / `www.riyucihuixuexi.cn`（Nginx + Let's Encrypt）
- SSH 已配置免密（本地 → 服务器）

**Docker Compose 服务**（`docker-compose.yml`，5 个服务）
- `voicevox`：TTS 引擎（端口 50021，容器 jp-vocab-voicevox）
- `postgres`：PostgreSQL 16（端口 5432，容器 jp-vocab-db，低内存参数）
- `backend`：FastAPI（端口 8000，容器 jp-vocab-backend，512M 内存上限，`Dockerfile` 构建）
- `nginx`：反向代理（80/443，容器 jp-vocab-nginx，托管前端静态文件 + `/api/*` 反代到 backend）
- `certbot`：证书管理（`certbot` profile，仅按需运行）

**一键部署**：本地项目根目录运行 `bash deploy.sh`，流程为 scp 同步 backend/frontend/配置 → `docker compose build backend` → `docker compose up -d --force-recreate backend` → 重启 nginx → 健康检查。

**常用运维命令**（在服务器 `/opt/riyucihui` 执行）
- 日志：`docker compose logs -f`
- 重启/停止：`docker compose restart` / `docker compose down`
- 创建管理员：`docker compose exec backend python -m app.cli create-admin <用户> <密码>`
- 登录报告：`docker compose exec backend python -m app.cli login-report [--user <用户名>]`
- 证书续期：`docker compose run --rm certbot renew`

**环境变量**（`.env`）：`SECRET_KEY`、`DEEPSEEK_API_KEY`、`VOLCANO_API_KEY`、`DB_PASSWORD`、`CORS_ORIGINS`。
