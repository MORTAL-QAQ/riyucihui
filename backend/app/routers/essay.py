"""短文生成与保存端点。

POST /api/essay — AI 生成日语短文（流式/非流式），可使用用户的词单单词
POST /api/essays — 保存生成的短文
GET /api/essays — 分页列出已保存的短文
GET /api/essays/{essay_id}/export/pdf — 导出短文为 PDF
DELETE /api/essays/{essay_id} — 删除短文
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Essay, User, Word
from ..schemas import (
    EssayListResponse,
    EssayOut,
    EssayRequest,
    EssayResponse,
    EssaySaveRequest,
)
from ..services.achievement_service import check_achievements
from ..services.ai_service import generate_essay, generate_essay_stream
from ..services.rate_limiter import rate_limit
from ..services.usage_service import check_limit, record_usage

router = APIRouter(prefix="/api", tags=["essay"])

# IP 级限流：AI 短文生成（付费调用）
ESSAY_IP_LIMIT = rate_limit(max_requests=10, window_seconds=60)  # 10/min per IP


def _sse(generator):
    for event in generator:
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("/essay")
def create_essay(
    req: EssayRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _ip_rate: None = Depends(ESSAY_IP_LIMIT),
):
    allowed, msg = check_limit(db, user.id, "essay")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    if req.words:
        word_list = req.words
    else:
        words = (
            db.execute(select(Word).where(Word.user_id == user.id, Word.topic.in_(req.topics)))
            .scalars()
            .all()
        )
        if not words:
            raise HTTPException(status_code=400, detail="所选词单中没有单词，请先生成或添加单词")
        word_list = [f"{w.japanese}({w.kana})" for w in words]

    if req.stream:
        def _stream_and_record():
            for event in generate_essay_stream(
                topics=req.topics,
                word_list=word_list,
                word_count=req.word_count,
                jlpt_level=req.jlpt_level,
                genre=req.genre,
                title=req.title,
            ):
                yield event
            record_usage(db, user.id, "essay", 0)

        return StreamingResponse(
            _sse(_stream_and_record()),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        result, tokens = generate_essay(
            topics=req.topics,
            word_list=word_list,
            word_count=req.word_count,
            jlpt_level=req.jlpt_level,
            genre=req.genre,
            title=req.title,
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI服务调用失败: {str(e)}")

    record_usage(db, user.id, "essay", tokens)

    return EssayResponse(
        title=result["title"],
        essay=result["essay"],
        words_used=result["words_used"],
        chinese_translation=result["chinese_translation"],
    )


@router.post("/essays")
def save_essay(
    req: EssaySaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    essay = Essay(
        user_id=user.id,
        title=req.title,
        content=req.content,
        chinese_translation=req.chinese_translation,
        topics=json.dumps(req.topics, ensure_ascii=False),
        words_used=json.dumps(req.words_used, ensure_ascii=False),
        word_count=req.word_count,
        jlpt_level=req.jlpt_level,
    )
    db.add(essay)
    db.commit()
    db.refresh(essay)
    new_achs = check_achievements(db, user.id)
    result = _essay_out(essay)
    if new_achs:
        result["new_achievements"] = [{"name": a["name"], "icon": a["icon"]} for a in new_achs]
    return result


@router.get("/essays", response_model=EssayListResponse)
def list_essays(
    offset: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total = db.execute(
        select(func.count(Essay.id)).where(Essay.user_id == user.id)
    ).scalar() or 0

    rows = db.execute(
        select(Essay)
        .where(Essay.user_id == user.id)
        .order_by(Essay.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).scalars().all()

    return EssayListResponse(essays=[_essay_out(e) for e in rows], total=total)


@router.delete("/essays/{essay_id}")
def delete_essay(
    essay_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    essay = db.get(Essay, essay_id)
    if not essay or essay.user_id != user.id:
        raise HTTPException(status_code=404, detail="短文不存在")
    db.delete(essay)
    db.commit()
    return {"message": "已删除"}


@router.get("/essays/{essay_id}/export/pdf")
def export_essay_pdf(
    essay_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """导出单篇短文为 PDF 文件。"""
    from ..services.pdf_service import generate_essay_pdf, _encode_filename

    essay = db.get(Essay, essay_id)
    if not essay or essay.user_id != user.id:
        raise HTTPException(status_code=404, detail="短文不存在")

    buf = generate_essay_pdf(essay)

    now = datetime.now()
    safe_title = essay.title[:30].replace("/", "_").replace("\\", "_")
    filename = f"短文_{safe_title}_{now.strftime('%Y%m%d')}.pdf"
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*={_encode_filename(filename)}",
        },
    )


def _essay_out(e: Essay) -> EssayOut:
    return EssayOut(
        id=e.id,
        title=e.title,
        content=e.content,
        chinese_translation=e.chinese_translation,
        topics=json.loads(e.topics) if isinstance(e.topics, str) else e.topics,
        words_used=json.loads(e.words_used) if isinstance(e.words_used, str) else e.words_used,
        word_count=e.word_count or 0,
        jlpt_level=e.jlpt_level or "N3",
        created_at=e.created_at,
    )
