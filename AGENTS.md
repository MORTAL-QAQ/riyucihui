# AGENTS.md

本文件为项目级指令文档，描述「AIGC 多模态日语词汇学习平台」的架构与部署方式，供 AI 编程助手快速上手。

## 项目概览

日语词汇学习平台：FastAPI + PostgreSQL + 原生前端。功能：AI 生成单词/短文/语法/完型、VOICEVOX 日语发音、AI 配图、PDF 导出、学习记录与成就、管理员后台、社区（帖子/公告/点赞评论/敏感词过滤）。

## 技术栈

- 后端：Python 3.12 / FastAPI / SQLAlchemy ORM / JWT (HS256, 24h) / bcrypt 密码哈希
- 数据库：SQLite（开发 `sqlite:///./data/words.db`）/ PostgreSQL 16（生产，Docker secrets 注入）
- 前端：原生 HTML/JS/CSS 无构建步骤；TTS 用 VOICEVOX（容器 `http://voicevox:50021`）；AI 用 DeepSeek（生成）+ 火山豆包 Seedream（配图）

## 后端结构（`backend/app/`）

- 入口 `main.py`：路由注册、`/api/health`、`mount("/", StaticFiles)` 托管前端
- 路由 `routers/`：auth、admin_api、words、study、grammar、essay、cloze、generate、voice、achievement、settings、export、community
  - AI/语音/图片端点有 IP 级限流（信任 nginx `X-Real-IP`）+ 用户级每日限额（北京时区零点重置）
  - 错误对外笼统、细节进日志
- 模型 `models.py`：User、UsageRecord、Word（`image_base64` 为 deferred 列）、StudyRecord、Essay、Cloze、GrammarCompare、Achievement、LoginHistory
- 服务 `services/`：ai_service、word_service、voicevox_manager、image_service、pdf_service、achievement_service、usage_service、rate_limiter、secrets、font_manager、sensitive_words
- 配置 `config.py` 全走环境变量；密钥经 `secrets.py`（env → Docker secrets → keyring → .env）；**未配置 SECRET_KEY 启动报错**
- CLI `cli.py`：`create-admin`、`login-report`、`backfill-orphans` 等，`python -m app.cli ...`

## 前端结构（`frontend/`）—— MPA 多页架构

**架构**：全部业务页为独立子页（HTML + JS，无后缀 URL），`index.html` 仅剩首页仪表盘 + 登录/注册（SPA 剩余：认证、switchTab 路由跳转、home、侧边栏、移动端导航）。所有页共享 `css/` + `js/common.js`（SPA 与子页共用同一共享层，无重复定义）。

**共享层 `js/common.js`**：`$`/`esc`/`jlptBadge`/`fmtTime`/`showToast`/`handleApiError`/`speakWord`（Web Audio，api.voice 返回 Blob 直接 arrayBuffer 解码）/`runStreamToPreview`（SSE，`$("#"+previewId)` 注意 # 前缀）/`initPage`（认证守卫）/`currentUsername`/`isAdmin`/`bindLogout`/`injectAdminNav`（管理按钮按 isAdmin 动态注入，普通用户不可见）。

**独立子页模板**：`<body class="subpage" style="margin:0;">` + `<div id="app" style="display:block; min-height:100vh;">`（覆盖全局 `#app{display:flex}` 防收缩左偏）+ `<main style="margin:auto; max-width:1200px; ...">` 居中 + 顶栏三区内联样式（左品牌 / 中导航 11 项：返回首页·词库·背词·生成·短文·完型·语法·图片·社区·成就·保存，当前页高亮，管理按钮动态注入 / 右设置·退出）。入口 `initPage().then(ok => ok && 加载函数())`；管理页额外校验 isAdmin。

**页面清单**：
| 页面 | URL | 文件 |
|------|-----|------|
| 首页（仪表盘/登录） | `/` | index.html + js/app.js |
| 社区 | `/community` | community.html + js/community.js |
| 词库 | `/wordbank` | wordbank.html + js/wordbank.js |
| 背词 | `/study` | study.html + js/study.js |
| 生成 | `/generate` | generate.html + js/generate.js |
| 短文 | `/essay` | essay.html + js/essay.js |
| 完型 | `/cloze` | cloze.html + js/cloze.js |
| 语法 | `/grammar` | grammar.html + js/grammar.js |
| 图片 | `/image` | image.html + js/image.js |
| 设置 | `/settings` | settings.html + js/settings.js |
| 成就 | `/achievement` | achievement.html + js/achievement.js |
| 管理（管理员） | `/admin` | admin.html + js/admin.js |
| 保存 | `/saved` | saved.html + js/saved.js |

**版本号机制**：css/js 引用 `?v={placeholder}`，deploy.sh 注入内容哈希。**`{app_version}` 为全部 js 合并哈希**（任一 js 变化版本号即变，防止浏览器缓存旧 JS 导致功能失效——曾因此出过生成/发声/登录故障）。

**开发工具（`backend/dev_tools/`）**：`unify_topbar.py`（统一顶栏生成）、`strip_*.py`（拆分清理）、`verify_*`（部署回归）、`test_load_js.js`/`test_inject_admin.js`（前端加载/注入回归）、`diag_*`（生产诊断）。**改动前端后部署前跑 test_load_js.js 防 SyntaxError**（曾因顶层变量重复声明致登录失效）。

## 改进清单

`改进清单.md` 跟踪 46 条优化项：P0/P1/P2 全部完成，P3 完成 12/13，仅 #41（mobile.css 重写）⏸ 暂缓。处理新改动前先查看。

## 部署

Docker Compose 部署，手动 `bash deploy.sh`（无 CI/CD）。

- 服务器 `root@101.37.204.74`，路径 `/opt/riyucihui`；域名 `riyucihuixuexi.cn`（Nginx + Let's Encrypt）；SSH 免密
- 5 服务：voicevox / postgres / backend（512M 上限，非 root 运行）/ nginx（托管前端 + 反代 /api + `proxy_buffering off` 支持 SSE）/ certbot
- **密钥**：secrets/ 目录经 compose 注入容器 `/run/secrets/`；服务器 secrets/ 目录 700、文件 644（非 root 容器需读）；deploy 不覆盖服务器真实密钥
- **部署流程**：tar 同步 backend → scp frontend → 构建重建 backend → 重启 nginx → 注入版本号 → 健康检查 → 注册每日备份 cron；`deploy.sh rollback` 回滚
- **运维**（服务器 `/opt/riyucihui`）：`docker compose logs -f` / `restart` / `down`；`python -m app.cli create-admin <用户> <密码>`；每日 03:00 自动备份至 `backups/`（保留 14 份）；证书续期 `bash scripts/cert-setup.sh renew`
- **环境变量**（`.env` 本地；生产 secrets）：`SECRET_KEY`、`DEEPSEEK_API_KEY`、`VOLCANO_API_KEY`、`DATABASE_URL`、`CORS_ORIGINS`（生产为具体域名）、`DEFAULT_DAILY_*`
