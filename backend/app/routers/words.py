from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
from ..services.image_service import generate_word_image
from ..services.usage_service import check_limit, record_usage

router = APIRouter(prefix="/api", tags=["words"])


@router.post("/words")
def save_words(
    req: SaveWordsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not req.words:
        raise HTTPException(status_code=400, detail="至少需要保存一个单词")
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
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if search and len(search) > 100:
        raise HTTPException(status_code=400, detail="搜索关键词不能超过100个字符")
    if limit > 200:
        limit = 200
    words, total = word_service.get_words(db, user.id, topic, search, offset, limit)
    return WordListResponse(words=[WordOut.model_validate(w) for w in words], total=total)


@router.get("/topics")
def list_topics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return word_service.get_topics(db, user.id)


@router.delete("/topics/{topic}")
def delete_topic(
    topic: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
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
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    word.image_base64 = image_base64
    db.commit()
    db.refresh(word)
    record_usage(db, user.id, "image_generation", 1)
    return WordOut.model_validate(word)


@router.get("/image-cards", response_model=ImageCardListResponse)
def list_image_cards(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按词单分组返回已有配图的单词，用于图片词卡页面。"""
    # 查询当前用户所有有配图的单词
    rows = db.execute(
        select(Word)
        .where(
            Word.user_id == user.id,
            Word.image_base64.isnot(None),
            Word.image_base64 != "",
        )
        .order_by(Word.topic, Word.created_at.desc())
    ).scalars().all()

    # 按 topic 分组
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
                image_base64=w.image_base64 or "", topic=w.topic,
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
