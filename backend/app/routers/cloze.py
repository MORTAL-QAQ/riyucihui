"""完型填空生成与保存端点。

POST /api/cloze — AI 生成完型填空练习（流式/非流式）
POST /api/clozes — 保存完型填空
GET /api/clozes — 分页列出已保存的完型填空
GET /api/clozes/{cloze_id}/export/pdf — 导出完型填空为 PDF
DELETE /api/clozes/{cloze_id} — 删除完型填空

生成的短文中包含 ____ 占位符，前端将其替换为输入框供用户填写。
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Cloze, User, Word
from ..schemas import (
    ClozeGenerateRequest,
    ClozeGenerateResponse,
    ClozeListResponse,
    ClozeOut,
    ClozeSaveRequest,
)
from ..services.achievement_service import check_achievements
from ..services.ai_service import generate_cloze, generate_cloze_stream
from ..services.rate_limiter import rate_limit
from ..services.usage_service import check_limit, record_usage

router = APIRouter(prefix="/api", tags=["cloze"])

# IP 级限流：AI 完型填空生成（付费调用）
CLOZE_IP_LIMIT = rate_limit(max_requests=10, window_seconds=60)  # 10/min per IP


def _sse(generator):
    for event in generator:
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("/cloze")
def create_cloze(
    req: ClozeGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _ip_rate: None = Depends(CLOZE_IP_LIMIT),
):
    allowed, msg = check_limit(db, user.id, "cloze")
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
            for event in generate_cloze_stream(
                topics=req.topics,
                word_list=word_list,
                length=req.length,
                jlpt_level=req.jlpt_level,
            ):
                yield event
            record_usage(db, user.id, "cloze", 0)

        return StreamingResponse(
            _sse(_stream_and_record()),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        result, tokens = generate_cloze(
            topics=req.topics,
            word_list=word_list,
            length=req.length,
            jlpt_level=req.jlpt_level,
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI服务调用失败: {str(e)}")

    record_usage(db, user.id, "cloze", tokens)

    return ClozeGenerateResponse(
        title=result["title"],
        passage=result["passage"],
        blanks=result["blanks"],
        chinese_translation=result["chinese_translation"],
    )


@router.post("/clozes")
def save_cloze(
    req: ClozeSaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cloze = Cloze(
        user_id=user.id,
        title=req.title,
        passage=req.passage,
        blanks=json.dumps([b.model_dump() for b in req.blanks], ensure_ascii=False),
        chinese_translation=req.chinese_translation,
        topics=json.dumps(req.topics, ensure_ascii=False),
        length=req.length,
        jlpt_level=req.jlpt_level,
    )
    db.add(cloze)
    db.commit()
    db.refresh(cloze)
    new_achs = check_achievements(db, user.id)
    result = _cloze_out(cloze)
    if new_achs:
        result["new_achievements"] = [{"name": a["name"], "icon": a["icon"]} for a in new_achs]
    return result


@router.get("/clozes", response_model=ClozeListResponse)
def list_clozes(
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total = db.execute(
        select(func.count(Cloze.id)).where(Cloze.user_id == user.id)
    ).scalar() or 0

    rows = db.execute(
        select(Cloze)
        .where(Cloze.user_id == user.id)
        .order_by(Cloze.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).scalars().all()

    return ClozeListResponse(clozes=[_cloze_out(c) for c in rows], total=total)


@router.delete("/clozes/{cloze_id}")
def delete_cloze(
    cloze_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cloze = db.get(Cloze, cloze_id)
    if not cloze or cloze.user_id != user.id:
        raise HTTPException(status_code=404, detail="完型填空不存在")
    db.delete(cloze)
    db.commit()
    return {"message": "已删除"}


@router.get("/clozes/{cloze_id}/export/pdf")
def export_cloze_pdf(
    cloze_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """导出单个完型填空为 PDF 文件（含答案）。"""
    from ..services.pdf_service import generate_cloze_pdf, _encode_filename

    cloze = db.get(Cloze, cloze_id)
    if not cloze or cloze.user_id != user.id:
        raise HTTPException(status_code=404, detail="完型填空不存在")

    buf = generate_cloze_pdf(cloze)

    now = datetime.now()
    safe_title = cloze.title[:30].replace("/", "_").replace("\\", "_")
    filename = f"完型填空_{safe_title}_{now.strftime('%Y%m%d')}.pdf"
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*={_encode_filename(filename)}",
        },
    )


def _cloze_out(c: Cloze):
    return {
        "id": c.id,
        "title": c.title,
        "passage": c.passage,
        "blanks": json.loads(c.blanks) if isinstance(c.blanks, str) else c.blanks,
        "chinese_translation": c.chinese_translation,
        "topics": json.loads(c.topics) if isinstance(c.topics, str) else c.topics,
        "length": c.length or 400,
        "jlpt_level": c.jlpt_level or "N3",
        "created_at": c.created_at,
    }
