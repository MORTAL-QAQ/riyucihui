"""AI 单词生成端点。

POST /api/generate — 根据主题生成日语单词列表。
支持流式（SSE）和非流式两种模式。流式模式通过 Server-Sent Events 逐步返回 AI 生成内容，
前端可以实时显示生成进度。
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..schemas import GenerateRequest, GenerateResponse
from ..services.ai_service import generate_words, generate_words_stream
from ..services.usage_service import check_limit, record_usage

router = APIRouter(prefix="/api", tags=["generate"])


def _sse(generator):
    """Convert a generator yielding {"chunk": str} / {"done": True, "result": ...} into SSE bytes."""
    for event in generator:
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("/generate")
def generate(
    req: GenerateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    allowed, msg = check_limit(db, user.id, "generate")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    if req.stream:
        difficulty = req.difficulty

        def _stream_and_record():
            tokens_est = 0
            for event in generate_words_stream(
                req.topic, difficulty, req.extra, req.count, req.exclude_words
            ):
                # 将 JLPT 等级注入到每个生成结果单词中
                if event.get("done") and difficulty:
                    for w in event.get("result", []):
                        w["jlpt_level"] = difficulty
                yield event
                if event.get("done"):
                    tokens_est = len(json.dumps(event.get("result", []), ensure_ascii=False)) // 2
            record_usage(db, user.id, "generate", tokens_est)

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
        return GenerateResponse(topic=req.topic, words=words)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI服务调用失败: {str(e)[:200]}")
