from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, undefer

from ..auth import get_current_user
from ..database import get_db
from ..models import User, Word
from ..schemas import (
    ImageCardListResponse,
    ImageCardOut,
    ImageCardTopic,
    SaveWordsRequest,
    WordItem,
    WordListResponse,
    WordOut,
)
from ..services import word_service
from ..services.achievement_service import check_achievements
from ..services.experiment import can_access_locked, is_locked_topic
from ..services.image_service import generate_word_image
from ..services.rate_limiter import rate_limit
from ..services.usage_service import check_limit, record_usage

router = APIRouter(prefix="/api", tags=["words"])

logger = logging.getLogger(__name__)

# IP 级限流：AI 配图调用火山引擎付费接口，防刷
IMAGE_IP_LIMIT = rate_limit(max_requests=10, window_seconds=60)  # 10/min per IP


@router.post("/words")
def save_words(
    req: SaveWordsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not req.words:
        raise HTTPException(status_code=400, detail="至少需要保存一个单词")
    if is_locked_topic(req.topic) and not can_access_locked(user):
        raise HTTPException(status_code=403, detail="实验词单仅对实验组开放")
    records = word_service.save_words(db, user.id, req.topic, req.words, req.jlpt_level)
    new_achs = check_achievements(db, user.id)
    resp = {"message": f"成功保存 {len(records)} 个单词", "count": len(records)}
    if new_achs:
        resp["new_achievements"] = [{"name": a["name"], "icon": a["icon"]} for a in new_achs]
    return resp


@router.get("/words", response_model=WordListResponse)
def list_words(
    topic: str | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = 50,
    include_images: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出单词。include_images=False 时不返回 base64 图片数据（大幅减小响应体积）。"""
    if search and len(search) > 100:
        raise HTTPException(status_code=400, detail="搜索关键词不能超过100个字符")
    if limit > 200:
        limit = 200
    if is_locked_topic(topic) and not can_access_locked(user):
        raise HTTPException(status_code=403, detail="实验词单仅对实验组开放")
    words, total = word_service.get_words(db, user.id, topic, search, offset, limit,
                                          include_images=include_images,
                                          exclude_locked=not can_access_locked(user))
    out = [WordOut.model_validate(w) for w in words]
    # Strip heavy image_base64 by default for performance
    if not include_images:
        for w in out:
            w.image_base64 = None
    return WordListResponse(words=out, total=total)


@router.get("/topics")
def list_topics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    topics = word_service.get_topics(db, user.id)
    if not can_access_locked(user):
        # 非实验组用户隐藏实验词单
        topics = [t for t in topics if not is_locked_topic(t["topic"])]
    return topics


@router.delete("/topics/{topic}")
def delete_topic(
    topic: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if is_locked_topic(topic) and not can_access_locked(user):
        raise HTTPException(status_code=403, detail="实验词单仅对实验组开放")
    count = word_service.delete_topic(db, user.id, topic)
    if count == 0:
        raise HTTPException(status_code=404, detail="词单不存在或已为空")
    return {"message": f"已删除 {count} 个单词", "count": count}


@router.post("/topics/{topic}/words", response_model=WordOut)
def add_word_to_topic(
    topic: str,
    item: WordItem,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if is_locked_topic(topic) and not can_access_locked(user):
        raise HTTPException(status_code=403, detail="实验词单仅对实验组开放")
    return WordOut.model_validate(word_service.add_word_to_topic(db, user.id, topic, item))


@router.delete("/words/{word_id}")
def delete_word(
    word_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ok = word_service.delete_word(db, user.id, word_id)
    if not ok:
        raise HTTPException(status_code=404, detail="单词不存在")
    return {"message": "删除成功"}


@router.post("/words/{word_id}/image", response_model=WordOut)
def generate_image(
    word_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _ip_rate: None = Depends(IMAGE_IP_LIMIT),
):
    """为词库中的单词调用火山引擎 AI 生成配图。普通用户每天限3张，管理员无限。"""
    # 用量检查（管理员自动通过）
    allowed, msg = check_limit(db, user.id, "image_generation")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    word = db.get(Word, word_id)
    if not word or word.user_id != user.id:
        raise HTTPException(status_code=404, detail="单词不存在")

    try:
        image_base64 = generate_word_image(
            japanese=word.japanese,
            chinese=word.chinese,
            kana=word.kana or "",
            example_ja=word.example_ja or "",
            example_cn=word.example_cn or "",
        )
    except RuntimeError as e:
        # 只对外返回笼统信息，内部细节（临时 URL / LLM 响应）进日志（#10）
        logger.error("AI 配图生成失败 word_id=%s: %s", word_id, e)
        raise HTTPException(status_code=502, detail="AI 配图生成失败，请稍后重试")

    word.image_base64 = image_base64
    db.commit()
    db.refresh(word)
    record_usage(db, user.id, "image_generation", 1)
    return WordOut.model_validate(word)


@router.get("/words/{word_id}/image-data")
def get_word_image_data(
    word_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """仅返回单张图片的 base64 数据（懒加载用）。"""
    word = db.execute(
        select(Word).where(Word.id == word_id).options(undefer(Word.image_base64))
    ).scalar_one_or_none()
    if not word or word.user_id != user.id:
        raise HTTPException(status_code=404, detail="单词不存在")
    return {"id": word.id, "image_base64": word.image_base64 or ""}


@router.get("/image-cards", response_model=ImageCardListResponse)
def list_image_cards(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    include_data: bool = False,
):
    """按词单分组返回已有配图的单词。

    include_data 默认 False（#30）：不返回图片 base64 数据，避免整页传输巨量内容；
    需要图片数据时显式传 include_data=true（前端仅在展示单张时请求）。
    """
    rows = db.execute(
        select(Word)
        .where(
            Word.user_id == user.id,
            Word.image_base64.isnot(None),
            Word.image_base64 != "",
        )
        .options(undefer(Word.image_base64))
        .order_by(Word.topic, Word.created_at.desc())
    ).scalars().all()

    topic_map: dict[str, list[Word]] = {}
    for w in rows:
        topic_map.setdefault(w.topic, []).append(w)

    topics = [
        ImageCardTopic(
            topic=topic,
            count=len(words),
            words=[ImageCardOut(
                id=w.id, japanese=w.japanese, kana=w.kana, chinese=w.chinese,
                example_ja=w.example_ja, example_cn=w.example_cn,
                image_base64=(w.image_base64 or "") if include_data else "",
                topic=w.topic,
            ) for w in words],
        )
        for topic, words in topic_map.items()
    ]

    return ImageCardListResponse(topics=topics, total_images=len(rows))


@router.post("/words/deduplicate")
def merge_duplicates(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    removed = word_service.deduplicate_words(db, user.id)
    if removed == 0:
        return {"message": "没有重复单词需要合并", "removed": 0}
    return {"message": f"已合并 {removed} 个重复单词", "removed": removed}


@router.get("/words/export/pdf")
def export_words_pdf(
    topic: str | None = None,
    layout: str = Query("table", pattern=r"^(table|card)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """导出词单为 PDF 文件。支持 table/card 两种布局（不含配图）。"""
    from ..services.pdf_service import generate_words_pdf, _encode_filename

    if is_locked_topic(topic) and not can_access_locked(user):
        raise HTTPException(status_code=403, detail="实验词单仅对实验组开放")
    words, total = word_service.get_words(db, user.id, topic, None, 0, 10000,
                                          exclude_locked=not can_access_locked(user))
    if not words:
        raise HTTPException(status_code=404, detail="没有可导出的单词")

    topic_name = topic or "全部词单"
    buf = generate_words_pdf(words, topic_name, total, layout=layout)

    now = datetime.now()
    filename = f"词单_{topic_name}_{now.strftime('%Y%m%d')}.pdf"
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*={_encode_filename(filename)}",
        },
    )
