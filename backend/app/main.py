"""多模态日语词汇学习 — FastAPI 应用入口。

应用启动流程（lifespan）：
1. 创建 data 目录
2. 创建数据库表 + 运行迁移（兼容旧数据库升级）
3. 检测并启动 VOICEVOX 语音引擎

中间件：
- CORS（跨域请求）
- 请求体大小限制（1MB，防止恶意大请求）

路由注册：
- 所有 API 端点通过 app.include_router() 注册
- 前端静态文件在最后挂载（必须在 API 路由之后，否则拦截 API 请求）
- index.html 在服务时注入缓存版本号（cache-busting）
"""

import asyncio
import gc
import hashlib
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .database import Base, engine, run_migrations
from .routers import achievement, admin_api, auth, cloze, essay, export, generate, grammar, settings, study, voice, words
from .services import voicevox_manager

FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
MAX_REQUEST_BYTES = 1_000_000  # 1 MB


_hash_cache: dict[str, tuple[float, str]] = {}


def _file_hash(rel_path: str) -> str:
    """Return first 8 chars of MD5 for a frontend file.
    Cached by mtime so frontend hot-updates are picked up without restart."""
    path = FRONTEND_DIR / rel_path
    if not path.exists():
        return "0" * 8
    mtime = path.stat().st_mtime
    cached = _hash_cache.get(rel_path)
    if cached and cached[0] == mtime:
        return cached[1]
    h = hashlib.md5(path.read_bytes()).hexdigest()[:8]
    _hash_cache[rel_path] = (mtime, h)
    return h


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 确保 data 目录存在（settings.json 等）
    (Path(__file__).parent.parent / "data").mkdir(parents=True, exist_ok=True)

    # 创建所有表
    Base.metadata.create_all(bind=engine)
    # 运行迁移（兼容旧数据库升级）
    run_migrations()

    # 后台定期 gc：每 300 次请求或 30 秒执行一次
    gc_counter = [0]
    async def periodic_gc():
        while True:
            await asyncio.sleep(30)
            gc.collect()
            # 释放 Python 内存归还 OS（需要 glibc 2.31+）
            if hasattr(os, 'sched_yield'):
                pass
    gc_task = asyncio.create_task(periodic_gc())

    if voicevox_manager.check_engine():
        print("[voicevox] Already running", file=sys.stderr)
    elif voicevox_manager.start_engine():
        voicevox_manager.wait_ready()
    elif voicevox_manager.wait_ready(timeout=10):
        print("[voicevox] Connected to external engine", file=sys.stderr)
    else:
        print("[voicevox] Not available — voice features disabled", file=sys.stderr)
    yield
    gc_task.cancel()
    voicevox_manager.stop_engine()


app = FastAPI(title="多模态日语词汇学习", version="1.0.0", lifespan=lifespan)

@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    # Fast path: honest Content-Length header
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_REQUEST_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": f"Request body too large (max {MAX_REQUEST_BYTES // 1_000_000} MB)"},
        )

    # Defense in depth: cap actual body stream (Content-Length can be
    # omitted or spoofed)
    if request.method in ("POST", "PUT", "PATCH"):
        body = b""
        async for chunk in request.stream():
            body += chunk
            if len(body) > MAX_REQUEST_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"Request body too large (max {MAX_REQUEST_BYTES // 1_000_000} MB)"
                    },
                )
        request._body = body

    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS.split(",") if config.CORS_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(admin_api.router)
app.include_router(grammar.router)
app.include_router(achievement.router)
app.include_router(generate.router)
app.include_router(words.router)
app.include_router(voice.router)
app.include_router(settings.router)
app.include_router(study.router)
app.include_router(essay.router)
app.include_router(cloze.router)
app.include_router(export.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve index.html with auto-generated cache-busting versions."""
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace("{style_version}", _file_hash("css/style.css"))
    html = html.replace("{api_version}", _file_hash("js/api.js"))
    html = html.replace("{app_version}", _file_hash("js/app.js"))
    return html


# 前端静态文件 — 必须在所有 API 路由之后挂载，否则会拦截所有请求
frontend_dir = Path(__file__).parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
