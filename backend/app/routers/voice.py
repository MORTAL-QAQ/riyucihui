import hashlib
import time
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import config
from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..services.rate_limiter import rate_limit
from ..services.usage_service import check_limit, record_usage
from .settings import read_settings

router = APIRouter(prefix="/api", tags=["voice"])

# IP 级限流：voice 端点无鉴权成本低，防脚本刷引擎（用户级每日 50 次之外的第二道防线）
VOICE_IP_LIMIT = rate_limit(max_requests=30, window_seconds=60)  # 30/min per IP

CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "voice_cache"
MAX_CACHE_FILES = 500
MAX_CACHE_AGE_DAYS = 30
# #32：evict 全目录 stat 开销大，降频为每 10 分钟最多一次
_EVICT_INTERVAL = 600
_last_evict_ts = 0.0


class VoiceRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)


def _cache_key(text: str, settings: dict, user_id: int) -> str:
    """Generate a deterministic cache key from text + voice settings + user."""
    raw = (
        f"{text}|{settings['speaker']}|{settings['speed']:.2f}"
        f"|{settings['pitch']:.2f}|{settings['intonation']:.2f}|{settings['volume']:.2f}"
        f"|{user_id}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_cached(key: str) -> bytes | None:
    path = CACHE_DIR / f"{key}.wav"
    if path.exists():
        return path.read_bytes()
    return None


def _set_cache(key: str, data: bytes):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.wav").write_bytes(data)
    _maybe_evict_cache()


def _maybe_evict_cache():
    """降频版缓存清理（#32）：每 _EVICT_INTERVAL 秒最多执行一次全目录扫描。"""
    global _last_evict_ts
    now = time.time()
    if now - _last_evict_ts < _EVICT_INTERVAL:
        return
    _last_evict_ts = now
    _evict_cache()


def _evict_cache():
    """Remove oldest files when over limit, and expired files beyond TTL."""
    try:
        paths = sorted(CACHE_DIR.iterdir(), key=lambda p: p.stat().st_mtime)
    except FileNotFoundError:
        return

    cutoff = time.time() - MAX_CACHE_AGE_DAYS * 86400
    excess = len(paths) - MAX_CACHE_FILES

    for p in paths:
        if excess <= 0 and p.stat().st_mtime >= cutoff:
            break
        p.unlink()
        excess -= 1


@router.post("/voice")
async def synthesize(
    req: VoiceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ip_rate: None = Depends(VOICE_IP_LIMIT),
):
    allowed, msg = check_limit(db, user.id, "voice")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    settings = read_settings()
    speaker = settings["speaker"]
    key = _cache_key(req.text, settings, user.id)

    cached = _get_cached(key)
    if cached is not None:
        record_usage(db, user.id, "voice", len(req.text))
        return Response(content=cached, media_type="audio/wav")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            query_resp = await client.post(
                f"{config.VOICEVOX_BASE_URL}/audio_query",
                params={"text": req.text, "speaker": speaker},
            )
            if query_resp.status_code != 200:
                raise HTTPException(status_code=502, detail="VOICEVOX audio_query 失败")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="VOICEVOX Engine 未运行，请先启动")

        query_data = query_resp.json()

        query_data["speedScale"] = settings["speed"]
        query_data["pitchScale"] = settings["pitch"]
        query_data["intonationScale"] = settings["intonation"]
        query_data["volumeScale"] = settings["volume"]

        try:
            synth_resp = await client.post(
                f"{config.VOICEVOX_BASE_URL}/synthesis",
                params={"speaker": speaker},
                json=query_data,
            )
            if synth_resp.status_code != 200:
                raise HTTPException(status_code=502, detail="VOICEVOX synthesis 失败")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="VOICEVOX Engine 未运行，请先启动")

        audio = synth_resp.content
        _set_cache(key, audio)
        record_usage(db, user.id, "voice", len(req.text))
        return Response(content=audio, media_type="audio/wav")
