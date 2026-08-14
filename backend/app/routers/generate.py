"""AI 单词生成端点。

POST /api/generate — 根据主题生成日语单词列表。
支持流式（SSE）和非流式两种模式。流式模式通过 Server-Sent Events 逐步返回 AI 生成内容，
前端可以实时显示生成进度。
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..schemas import GenerateRequest, GenerateResponse
from ..services.ai_service import generate_words, generate_words_stream
from ..services.rate_limiter import rate_limit
from ..services.usage_service import check_limit, count_today, get_user_daily_limit, record_usage

router = APIRouter(prefix="/api", tags=["generate"])

logger = logging.getLogger(__name__)

# IP 级限流：防未登录/多账号刷 AI 调用（用户级每日配额之外的第二道防线）
GENERATE_IP_LIMIT = rate_limit(max_requests=10, window_seconds=60)  # 10/min per IP


def _sse(generator):
    """Convert a generator yielding {"chunk": str} / {"done": True, "result": ...} into SSE bytes."""
    for event in generator:
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.get("/generate/quota")
def get_generate_quota(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Return today's word generation usage and limit for the current user."""
    today_used = count_today(db, user.id, "generated_words")
    daily_limit = get_user_daily_limit(db, user.id, "generated_words")
    remaining = None if daily_limit is None else max(0, daily_limit - today_used)
    return {
        "today_generated": today_used,
        "daily_limit": daily_limit,
        "remaining": remaining,
        "is_admin": user.is_admin,
    }


@router.post("/generate")
def generate(
    req: GenerateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ip_rate: None = Depends(GENERATE_IP_LIMIT),
):
    # 检查每日生成单词数量限制（默认100个/天，独立于AI调用次数限制）
    word_allowed, word_msg = check_limit(db, user.id, "generated_words")
    if not word_allowed:
        raise HTTPException(status_code=429, detail=word_msg)

    if req.stream:
        difficulty = req.difficulty

        def _stream_and_record():
            tokens_est = 0
            word_count = 0
            for event in generate_words_stream(
                req.topic, difficulty, req.extra, req.count, req.exclude_words
            ):
                # 将 JLPT 等级注入到每个生成结果单词中
                if event.get("done") and difficulty:
                    for w in event.get("result", []):
                        w["jlpt_level"] = difficulty
                yield event
                if event.get("done"):
                    result_words = event.get("result", [])
                    word_count = len(result_words)
                    tokens_est = len(json.dumps(result_words, ensure_ascii=False)) // 2
            record_usage(db, user.id, "generate", tokens_est)
            record_usage(db, user.id, "generated_words", word_count)

        return StreamingResponse(
            _sse(_stream_and_record()),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        words, tokens = generate_words(req.topic, req.difficulty, req.extra, req.count, req.exclude_words)
        # 将 JLPT 等级标记到每个单词上
        if req.difficulty:
            for w in words:
                w["jlpt_level"] = req.difficulty
        record_usage(db, user.id, "generate", tokens)
        record_usage(db, user.id, "generated_words", len(words))
        return GenerateResponse(topic=req.topic, words=words)
    except HTTPException:
        raise
    except ValueError as e:
        # 只对外返回笼统信息，内部细节进日志（#10）
        logger.error("AI 单词生成失败 topic=%r: %s", req.topic, e)
        raise HTTPException(status_code=502, detail="AI 生成服务暂时不可用，请稍后重试")
    except RuntimeError as e:
        logger.error("AI 单词生成运行时错误 topic=%r: %s", req.topic, e)
        raise HTTPException(status_code=502, detail="AI 生成服务暂时不可用，请稍后重试")
    except Exception:
        logger.exception("AI 单词生成未知异常 topic=%r", req.topic)
        raise HTTPException(status_code=500, detail="AI 生成服务内部错误，请稍后重试")
