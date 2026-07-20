import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import User

from ..models import GrammarCompare
from ..schemas import (
    GrammarAnalyzeRequest,
    GrammarAnalyzeResponse,
    GrammarCompareListResponse,
    GrammarCompareOut,
    GrammarCompareRequest,
    GrammarCompareResponse,
    GrammarCompareSaveRequest,
    GrammarCorrectRequest,
    GrammarCorrectResponse,
)
from ..services.achievement_service import check_achievements
from ..services.ai_service import (
    analyze_grammar,
    analyze_grammar_stream,
    compare_grammar,
    compare_grammar_stream,
    correct_grammar,
    correct_grammar_stream,
)
from ..services.usage_service import check_limit, record_usage

router = APIRouter(prefix="/api/grammar", tags=["grammar"])


def _sse(generator):
    for event in generator:
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _check(db: Session, user_id: int):
    allowed, msg = check_limit(db, user_id, "grammar")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)


@router.post("/analyze")
def grammar_analyze(
    req: GrammarAnalyzeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check(db, user.id)

    if req.stream:
        def _stream_and_record():
            for event in analyze_grammar_stream(req.sentence):
                yield event
            record_usage(db, user.id, "grammar_analyze", 0)
        return StreamingResponse(
            _sse(_stream_and_record()),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        data, tokens = analyze_grammar(req.sentence)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI服务调用失败: {str(e)}")
    record_usage(db, user.id, "grammar_analyze", tokens)
    new_achs = check_achievements(db, user.id)
    return GrammarAnalyzeResponse(**data)


@router.post("/correct")
def grammar_correct(
    req: GrammarCorrectRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check(db, user.id)

    if req.stream:
        def _stream_and_record():
            for event in correct_grammar_stream(req.sentence):
                yield event
            record_usage(db, user.id, "grammar_correct", 0)
        return StreamingResponse(
            _sse(_stream_and_record()),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        data, tokens = correct_grammar(req.sentence)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI服务调用失败: {str(e)}")
    record_usage(db, user.id, "grammar_correct", tokens)
    new_achs = check_achievements(db, user.id)
    return GrammarCorrectResponse(**data)


@router.post("/compare")
def grammar_compare(
    req: GrammarCompareRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check(db, user.id)

    if req.stream:
        def _stream_and_record():
            for event in compare_grammar_stream(req.topic):
                yield event
            record_usage(db, user.id, "grammar_compare", 0)
        return StreamingResponse(
            _sse(_stream_and_record()),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        data, tokens = compare_grammar(req.topic)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI服务调用失败: {str(e)}")
    record_usage(db, user.id, "grammar_compare", tokens)
    new_achs = check_achievements(db, user.id)
    return GrammarCompareResponse(**data)


@router.post("/compares", response_model=GrammarCompareOut)
def save_compare(
    req: GrammarCompareSaveRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a grammar compare result."""
    json.loads(req.result)  # validate JSON
    entry = GrammarCompare(
        user_id=user.id,
        topic=req.topic,
        result=req.result,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/compares", response_model=GrammarCompareListResponse)
def list_compares(
    offset: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total = (
        db.query(GrammarCompare)
        .filter(GrammarCompare.user_id == user.id)
        .count()
    )
    items = (
        db.query(GrammarCompare)
        .filter(GrammarCompare.user_id == user.id)
        .order_by(GrammarCompare.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {"items": items, "total": total}


@router.delete("/compares/{entry_id}")
def delete_compare(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = (
        db.query(GrammarCompare)
        .filter(GrammarCompare.id == entry_id, GrammarCompare.user_id == user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(entry)
    db.commit()
    return {"message": "已删除"}
