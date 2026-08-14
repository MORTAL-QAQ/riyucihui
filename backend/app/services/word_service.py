from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, undefer

from ..models import Word
from ..schemas import WordItem


def save_words(db: Session, user_id: int, topic: str, words: list[WordItem],
               jlpt_level: str | None = None) -> list[Word]:
    records = []
    for w in words:
        record = Word(
            user_id=user_id,
            topic=topic,
            japanese=w.japanese,
            kana=w.kana,
            chinese=w.chinese,
            example_ja=w.example_ja,
            example_cn=w.example_cn,
            jlpt_level=jlpt_level or w.jlpt_level,
        )
        db.add(record)
        records.append(record)
    db.commit()
    for r in records:
        db.refresh(r)
    return records


def get_words(
    db: Session,
    user_id: int,
    topic: str | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = 50,
    include_images: bool = False,
) -> tuple[list[Word], int]:
    """查询单词列表。image_base64 为 deferred 大字段，默认不加载（#31）。"""
    stmt = select(Word).where(Word.user_id == user_id)
    if include_images:
        stmt = stmt.options(undefer(Word.image_base64))
    if topic:
        stmt = stmt.where(Word.topic == topic)
    if search:
        # 转义 LIKE 通配符 %/_（#11），否则用户搜索 "%" 会匹配全部记录
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        stmt = stmt.where(
            Word.japanese.like(pattern, escape="\\")
            | Word.kana.like(pattern, escape="\\")
            | Word.chinese.like(pattern, escape="\\")
        )
    # count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar()
    # fetch
    stmt = stmt.order_by(Word.created_at.desc()).offset(offset).limit(limit)
    words = db.execute(stmt).scalars().all()
    return words, total


def get_topics(db: Session, user_id: int) -> list[dict]:
    stmt = (
        select(
            Word.topic,
            func.count(Word.id),
            func.min(Word.jlpt_level),  # 取词单中最高难度等级作为代表：字符串序 N1<N2<...<N5，min 即 N1
        )
        .where(Word.user_id == user_id)
        .group_by(Word.topic)
        .order_by(Word.topic)
    )
    rows = db.execute(stmt).all()
    return [{"topic": r[0], "count": r[1], "jlpt_level": r[2]} for r in rows]


def delete_word(db: Session, user_id: int, word_id: int) -> bool:
    word = db.get(Word, word_id)
    if not word or word.user_id != user_id:
        return False
    db.delete(word)
    db.commit()
    return True


def delete_topic(db: Session, user_id: int, topic: str) -> int:
    stmt = delete(Word).where(Word.user_id == user_id, Word.topic == topic)
    result = db.execute(stmt)
    db.commit()
    return result.rowcount


def add_word_to_topic(db: Session, user_id: int, topic: str, item: WordItem) -> Word:
    record = Word(
        user_id=user_id,
        topic=topic,
        japanese=item.japanese,
        kana=item.kana,
        chinese=item.chinese,
        example_ja=item.example_ja,
        example_cn=item.example_cn,
        jlpt_level=item.jlpt_level,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def deduplicate_words(db: Session, user_id: int) -> int:
    """Delete duplicate words for a user, keeping the oldest entry per japanese.
    Returns the number of deleted duplicates.

    Uses a single DELETE with a subquery — no N+1 loop."""
    keep_sub = (
        select(func.min(Word.id))
        .where(Word.user_id == user_id)
        .group_by(Word.japanese)
    )
    stmt = delete(Word).where(
        Word.user_id == user_id,
        Word.id.not_in(keep_sub),
    )
    result = db.execute(stmt)
    removed = result.rowcount
    if removed:
        db.commit()
    return removed
