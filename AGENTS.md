# AGENTS.md

本文件为项目级指令文档，描述「AIGC 多模态日语词汇学习平台」的架构与部署方式，供 AI 编程助手快速上手。

## 项目概览

日语词汇学习平台，FastAPI + 原生前端 + PostgreSQL 全栈应用，支持 AI 生成单词/短文/语法/完型、VOICEVOX 日语发音、AI 配图、PDF 导出、学习记录与成就系统、管理员后台、社区（帖子分享 + 管理员公告 + 点赞评论 + 敏感词过滤）。

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
- 路由 `routers/`：auth、admin_api、words、study、grammar、essay、cloze、generate、voice、achievement、settings、export、community
  - AI/语音/图片付费端点均有 **IP 级限流**（`rate_limiter`，只信任 nginx 的 `X-Real-IP`）+ 用户级每日限额（北京时区零点重置）
  - 错误对外统一笼统信息，细节进日志（logging）
- 数据模型 `models.py`：User、UsageRecord、Word、StudyRecord、Essay、Cloze、GrammarCompare、Achievement、LoginHistory
  - `Word.image_base64` 为 **deferred 列**（常规查询不加载大字段，需要时显式 `undefer`）
  - 复合索引：study_records `(user_id,next_review_date)`/`(user_id,last_review_date)`、usage_records `(user_id,kind,created_at)`、words 多列 + pg_trgm
- 服务层 `services/`：ai_service（统一 `_chat()` 调用）、word_service、voicevox_manager、image_service、pdf_service（含 `_esc` 转义、`jlpt_color`、`generate_study_report_pdf`）、achievement_service、usage_service、rate_limiter、secrets、font_manager、sensitive_words（社区敏感词过滤）
- 配置 `config.py`：全部从环境变量读取；`SECRET_KEY`/`DATABASE_URL`/API Key 经 `services/secrets.py` 解析（env → Docker secrets → keyring → .env）；**未配置 SECRET_KEY 启动直接报错**；默认每日限额集中在 `config.DEFAULT_DAILY_*`
- CLI `cli.py`：管理命令（`create-admin`、`login-report`、`backfill-orphans` 等），从 backend/ 目录运行 `python -m app.cli ...`

## 前端结构（`frontend/`）—— 多页架构（阶段二）

**架构**：MPA 主导。全部业务页面已拆为独立子页（独立 HTML + 独立 JS，URL 路由化无后缀路径），`index.html` SPA 仅保留首页（仪表盘）与登录/注册。所有页面共享 `css/`（desktop/mobile）与 `js/common.js`（共享层）。

**共享层 `js/common.js`**：`$`/`esc`/`escHtml`/`jlptBadge`/`fmtTime`/`showToast`/`handleApiError`/`speakWord`（Web Audio 发音）/`showImageLightbox`/`runStreamToPreview`（SSE 流式预览）/`initPage`（认证守卫，未登录跳 `/`）/`initSidebar`（移动端抽屉）/`currentUsername`/`isAdmin`/`bindLogout`。

**独立子页模板**（全部子页统一）：
- 顶栏三区（全部内联样式，不依赖 CSS 缓存）：左品牌 / 中导航居中（返回首页·词库·背词·生成·社区·短文·完型·语法·图片·成就·保存，当前页高亮；仅管理页额外含「🛡 管理」高亮项）/ 右「设置·退出」贴最右
- `<body class="subpage" style="margin:0;">` + `<div id="app" style="display:block; min-height:100vh;">`（覆盖全局 `#app{display:flex}`，否则内容收缩左偏）
- `<main class="main" style="margin-left:auto;margin-right:auto;max-width:1200px;width:100%;box-sizing:border-box;padding:24px 20px 60px;">` 内容居中
- 页面 JS 入口：`initPage().then(ok => ok && 加载函数())`；管理页额外校验 `isAdmin` 否则跳回首页
- nginx `try_files $uri $uri.html $uri/ /index.html` 支持无后缀路由 + SPA 回退

**页面清单**（全部已拆为独立子页）：
| 页面 | URL | 文件 | 状态 |
|------|-----|------|------|
| 首页（仪表盘/登录） | `/` | index.html + js/app.js（SPA 剩余：认证、switchTab 路由跳转、home 仪表盘、侧边栏、移动端底部导航、彩蛋） | ✅ |
| 社区 | `/community` | community.html + js/community.js | ✅ 已拆 |
| 词库 | `/wordbank` | wordbank.html + js/wordbank.js | ✅ 已拆 |
| 背词 | `/study` | study.html + js/study.js | ✅ 已拆 |
| 生成 | `/generate` | generate.html + js/generate.js | ✅ 已拆 |
| 短文 | `/essay` | essay.html + js/essay.js | ✅ 已拆 |
| 完型 | `/cloze` | cloze.html + js/cloze.js | ✅ 已拆 |
| 语法 | `/grammar` | grammar.html + js/grammar.js | ✅ 已拆 |
| 图片 | `/image` | image.html + js/image.js | ✅ 已拆 |
| 设置 | `/settings` | settings.html + js/settings.js | ✅ 已拆 |
| 成就 | `/achievement` | achievement.html + js/achievement.js | ✅ 已拆 |
| 管理（管理员） | `/admin` | admin.html + js/admin.js | ✅ 已拆 |
| 保存 | `/saved` | saved.html + js/saved.js | ✅ 已拆 |

**开发工具脚本（`backend/dev_tools/`，一次性维护工具，已归档）**：
- `strip_*.py`：页面拆分时从 app.js/index.html 精确删除已迁移代码（UTF-8 安全，含断言）
- `unify_topbar.py`：统一全部独立子页顶栏导航（当前页高亮参数化生成）
- `verify_topbar.py` / `verify_*.sh`：本地/生产页面回归验证（状态码 + js 引用 + 导航按钮数）

**版本号机制**：index.html 与独立子页的 css/js 引用带 `?v={version}` 占位符，deploy.sh 部署时用内容哈希统一注入（所有 `*.html`）。

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
