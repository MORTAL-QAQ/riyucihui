from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import StudyRecord, User, Word
from ..services.achievement_service import check_achievements

router = APIRouter(prefix="/api/study", tags=["study"])

MAX_NEW_PER_DAY = 50
MAX_REVIEW_PER_SESSION = 100  # 每轮最多复习数，防止复习债堆积


def sm2(easiness: float, interval: int, repetition: int, quality: int,
        days_overdue: int = 0) -> tuple[float, int, int, int]:
    """增强版 SM-2 间隔重复算法。

    相比标准 SM-2 的改进：
    1. 逾期惩罚 —— 逾期超过当前间隔时降低 easiness 并缩短新间隔
    2. 失效处理 —— 评分 < 3 时大幅缩短间隔、降低 repetition
    3. 阶段映射 —— stage 基于实际间隔天数而非 repetition 次数，更准确反映掌握度
    4. 长期记忆 —— 间隔 ≥ 180 天自动标记为 stage 7（已掌握）
    """
    # ── 逾期惩罚 ──
    if days_overdue > 0 and interval > 0 and quality >= 3:
        overdue_ratio = days_overdue / max(interval, 1)
        if overdue_ratio > 2.0:
            # 逾期超过间隔2倍：大幅降级
            easiness -= 0.20
            interval = max(1, round(interval * 0.4))
            repetition = max(0, repetition - 2)
        elif overdue_ratio > 1.0:
            # 逾期超过间隔1倍：适度降级
            easiness -= 0.10
            interval = max(1, round(interval * 0.7))
            repetition = max(0, repetition - 1)
        elif overdue_ratio > 0.5:
            easiness -= 0.05

    # ── 评分处理 ──
    if quality >= 3:
        # 正确回答
        if repetition == 0:
            new_interval = 1           # 首次正确 → 明天复习
            new_repetition = 1
        elif repetition == 1:
            new_interval = max(2, round(interval * easiness))  # 第二次正确 → 进入标准节奏
            new_repetition = 2
        else:
            new_interval = round(interval * easiness)          # 标准 SM-2
            new_repetition = repetition + 1
    else:
        # 回答失败：失效处理
        if repetition >= 3:
            # 已掌握的卡片失效 → 回退但不归零
            new_interval = max(1, round(interval * 0.25))
            new_repetition = max(1, repetition - 3)
        elif repetition >= 1:
            new_interval = 1           # 学习中的卡片失败 → 明天再来
            new_repetition = max(0, repetition - 1)
        else:
            new_interval = 0           # 新卡失败 → 今天继续
            new_repetition = 0

    # ── EF 调整（标准 SM-2 公式）──
    ef = easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if ef < 1.3:
        ef = 1.3

    # ── 阶段映射：基于实际间隔天数 ──
    if new_interval <= 0:
        stage = 0
    elif new_interval <= 1:
        stage = 1
    elif new_interval <= 3:
        stage = 2
    elif new_interval <= 7:
        stage = 3
    elif new_interval <= 21:
        stage = 4
    elif new_interval <= 60:
        stage = 5
    elif new_interval <= 180:
        stage = 6
    else:
        stage = 7  # 已掌握

    return ef, new_interval, new_repetition, stage


class WordOut(BaseModel):
    id: int
    topic: str
    japanese: str
    kana: str
    chinese: str
    example_ja: str
    example_cn: str
    image_base64: str | None = None
    jlpt_level: str | None = None
    stage: int = 0
    review_count: int = 0

    class Config:
        from_attributes = True


class StartRequest(BaseModel):
    topics: list[str] = Field(default_factory=list, max_length=20)
    count: int = Field(default=20, ge=5, le=50)
    mode: str = Field(default="mixed", pattern=r"^(mixed|review|new)$")


class RecordRequest(BaseModel):
    word_id: int
    quality: int = Field(default=3, ge=0, le=5)


class RecordOut(BaseModel):
    id: int
    stage: int
    next_review_date: str
    easiness_factor: float
    interval: int


class StatsOut(BaseModel):
    due_review: int
    new_available: int
    new_today: int
    learned: int
    mastering: int


class CalendarDay(BaseModel):
    date: str
    count: int


class CalendarOut(BaseModel):
    days: list[CalendarDay]
    new_available: int


class WordStatusOut(BaseModel):
    word_id: int
    stage: int
    review_count: int
    last_review_date: str | None
    next_review_date: str | None
    easiness_factor: float
    interval: int


# ── 撤销记录（内存缓存，仅当前进程有效）──
_undo_store: dict[int, dict] = {}  # user_id → {word_id, prev_state, ...}


def _word_out(w: Word, sr: StudyRecord | None) -> WordOut:
    return WordOut(
        id=w.id,
        topic=w.topic,
        japanese=w.japanese,
        kana=w.kana,
        chinese=w.chinese,
        example_ja=w.example_ja,
        example_cn=w.example_cn,
        image_base64=w.image_base64,
        jlpt_level=w.jlpt_level,
        stage=sr.stage if sr else 0,
        review_count=sr.review_count if sr else 0,
    )


@router.get("/topics")
def list_study_topics(
    mode: str = Query(default="all", pattern=r"^(all|new|review)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if mode == "review":
        today = date.today()
        rows = (
            db.query(Word.topic, func.count(Word.id), func.max(Word.jlpt_level))
            .join(StudyRecord, Word.id == StudyRecord.word_id)
            .filter(
                Word.user_id == user.id,
                StudyRecord.user_id == user.id,
                StudyRecord.next_review_date <= today,
                StudyRecord.stage < 7,
            )
            .group_by(Word.topic)
            .all()
        )
    elif mode == "new":
        rows = (
            db.query(Word.topic, func.count(Word.id), func.max(Word.jlpt_level))
            .outerjoin(StudyRecord, Word.id == StudyRecord.word_id)
            .filter(
                Word.user_id == user.id,
                StudyRecord.id.is_(None),
            )
            .group_by(Word.topic)
            .all()
        )
    else:
        rows = (
            db.query(Word.topic, func.count(Word.id), func.max(Word.jlpt_level))
            .filter(Word.user_id == user.id)
            .group_by(Word.topic)
            .all()
        )
    return [{"topic": t, "count": c, "jlpt_level": lv} for t, c, lv in rows]


@router.get("/due")
def get_due(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()

    new_available = (
        db.query(Word)
        .outerjoin(StudyRecord, Word.id == StudyRecord.word_id)
        .filter(Word.user_id == user.id, StudyRecord.id.is_(None))
        .count()
    )

    due_review = (
        db.query(StudyRecord)
        .filter(
            StudyRecord.user_id == user.id,
            StudyRecord.next_review_date <= today,
            StudyRecord.stage < 7,
        )
        .count()
    )

    new_today = min(new_available, MAX_NEW_PER_DAY)
    return {
        "due_review": due_review,
        "new_today": new_today,
        "new_available": new_available,
        "total": due_review + new_today,
    }


@router.get("/stats", response_model=StatsOut)
def get_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()

    due_review = (
        db.query(StudyRecord)
        .filter(
            StudyRecord.user_id == user.id,
            StudyRecord.next_review_date <= today,
            StudyRecord.stage < 7,
        )
        .count()
    )
    new_available = (
        db.query(Word)
        .outerjoin(StudyRecord, Word.id == StudyRecord.word_id)
        .filter(Word.user_id == user.id, StudyRecord.id.is_(None))
        .count()
    )

    learned = db.query(StudyRecord).filter(StudyRecord.user_id == user.id).count()
    mastering = (
        db.query(StudyRecord).filter(StudyRecord.user_id == user.id, StudyRecord.stage >= 5).count()
    )  # stage 5+ (间隔 ≥ 8天) 视为掌握中

    return StatsOut(
        due_review=due_review,
        new_available=new_available,
        new_today=min(new_available, MAX_NEW_PER_DAY),
        learned=learned,
        mastering=mastering,
    )


@router.get("/calendar", response_model=CalendarOut)
def get_calendar(
    days: int = Query(default=14, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    end_date = today + timedelta(days=days)

    rows = (
        db.query(StudyRecord.next_review_date, func.count(StudyRecord.id))
        .filter(
            StudyRecord.user_id == user.id,
            StudyRecord.next_review_date.between(today, end_date),
            StudyRecord.stage < 7,
        )
        .group_by(StudyRecord.next_review_date)
        .all()
    )
    count_map = {r[0]: r[1] for r in rows}

    day_list = []
    for i in range(days + 1):
        d = today + timedelta(days=i)
        day_list.append(
            CalendarDay(
                date=d.isoformat(),
                count=count_map.get(d, 0),
            )
        )

    new_available = (
        db.query(func.count(Word.id))
        .outerjoin(StudyRecord, Word.id == StudyRecord.word_id)
        .filter(Word.user_id == user.id, StudyRecord.id.is_(None))
        .scalar()
    )

    return CalendarOut(days=day_list, new_available=new_available)


@router.get("/words-status", response_model=list[WordStatusOut])
def get_words_status(
    ids: str = Query(default=""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not ids:
        return []

    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    if not id_list:
        return []

    records = (
        db.query(StudyRecord)
        .filter(
            StudyRecord.user_id == user.id,
            StudyRecord.word_id.in_(id_list),
        )
        .all()
    )
    return [
        WordStatusOut(
            word_id=r.word_id,
            stage=r.stage,
            review_count=r.review_count,
            last_review_date=r.last_review_date.isoformat() if r.last_review_date else None,
            next_review_date=r.next_review_date.isoformat() if r.next_review_date else None,
            easiness_factor=r.easiness_factor or 2.5,
            interval=r.interval or 0,
        )
        for r in records
    ]


@router.post("/start", response_model=list[WordOut])
def start_session(
    req: StartRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    results: list[WordOut] = []

    def _due_query():
        q = (
            db.query(Word, StudyRecord)
            .join(StudyRecord, Word.id == StudyRecord.word_id)
            .filter(
                StudyRecord.user_id == user.id,
                StudyRecord.next_review_date <= today,
                StudyRecord.stage < 7,
            )
        )
        if req.topics:
            q = q.filter(Word.topic.in_(req.topics))
        # 优先复习逾期最久 + stage 最低的
        return q.order_by(StudyRecord.stage, StudyRecord.next_review_date)

    def _new_query():
        q = (
            db.query(Word)
            .outerjoin(StudyRecord, Word.id == StudyRecord.word_id)
            .filter(Word.user_id == user.id, StudyRecord.id.is_(None))
        )
        if req.topics:
            q = q.filter(Word.topic.in_(req.topics))
        return q

    if req.mode in ("mixed", "review"):
        for w, sr in _due_query().limit(min(req.count, MAX_REVIEW_PER_SESSION)).all():
            results.append(_word_out(w, sr))

    if req.mode in ("mixed", "new") and len(results) < req.count:
        new_limit = min(req.count - len(results), MAX_NEW_PER_DAY)
        for w in _new_query().limit(new_limit).all():
            results.append(_word_out(w, None))

    # "new" mode fallback: fill remaining slots with review words
    if req.mode == "new" and len(results) < req.count:
        for w, sr in _due_query().limit(req.count - len(results)).all():
            results.append(_word_out(w, sr))
            if len(results) >= req.count:
                break

    return results


@router.post("/record")
def record_review(
    req: RecordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()

    sr = (
        db.query(StudyRecord)
        .filter(
            StudyRecord.word_id == req.word_id,
            StudyRecord.user_id == user.id,
        )
        .first()
    )

    if sr is None:
        word = db.get(Word, req.word_id)
        if not word or word.user_id != user.id:
            raise HTTPException(status_code=404, detail="单词不存在")
        sr = StudyRecord(
            user_id=user.id,
            word_id=req.word_id,
            stage=0,
            review_count=0,
            easiness_factor=2.5,
            interval=0,
            repetition=0,
        )
        db.add(sr)

    # ── 保存撤销快照 ──
    _undo_store[user.id] = {
        "word_id": sr.word_id,
        "prev_stage": sr.stage or 0,
        "prev_easiness": sr.easiness_factor or 2.5,
        "prev_interval": sr.interval or 0,
        "prev_repetition": sr.repetition or 0,
        "prev_review_count": sr.review_count or 0,
        "prev_next_review": sr.next_review_date,
        "prev_last_review": sr.last_review_date,
    }

    # ── 计算逾期天数 ──
    days_overdue = 0
    if sr.next_review_date and sr.next_review_date < today and sr.interval and sr.interval > 0:
        days_overdue = (today - sr.next_review_date).days

    # ── 应用 SM-2 ──
    ef, new_interval, new_repetition, new_stage = sm2(
        easiness=sr.easiness_factor or 2.5,
        interval=sr.interval or 0,
        repetition=sr.repetition or 0,
        quality=req.quality,
        days_overdue=days_overdue,
    )

    sr.user_id = user.id
    sr.easiness_factor = ef
    sr.interval = new_interval
    sr.repetition = new_repetition
    sr.stage = new_stage
    sr.review_count = (sr.review_count or 0) + 1
    sr.last_review_date = today
    sr.next_review_date = today + timedelta(days=new_interval)

    db.commit()
    db.refresh(sr)

    new_achs = check_achievements(db, user.id)

    # ── 计算会话统计 ──
    today_reviewed = (
        db.query(func.count(StudyRecord.id))
        .filter(
            StudyRecord.user_id == user.id,
            StudyRecord.last_review_date == today,
        )
        .scalar()
    )

    result = {
        "id": sr.id,
        "stage": sr.stage,
        "next_review_date": sr.next_review_date.isoformat(),
        "easiness_factor": sr.easiness_factor,
        "interval": sr.interval,
        "quality": req.quality,
        "days_overdue": days_overdue,
        "today_reviewed": today_reviewed or 0,
    }
    if new_achs:
        result["new_achievements"] = [{"name": a["name"], "icon": a["icon"]} for a in new_achs]
    return result


@router.post("/undo")
def undo_review(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """撤销最近一次评分，恢复到评分前的状态。"""
    undo = _undo_store.get(user.id)
    if not undo:
        raise HTTPException(status_code=404, detail="没有可撤销的操作")

    sr = (
        db.query(StudyRecord)
        .filter(
            StudyRecord.word_id == undo["word_id"],
            StudyRecord.user_id == user.id,
        )
        .first()
    )

    if not sr:
        raise HTTPException(status_code=404, detail="学习记录不存在")

    # 恢复到评分前的状态
    sr.stage = undo["prev_stage"]
    sr.easiness_factor = undo["prev_easiness"]
    sr.interval = undo["prev_interval"]
    sr.repetition = undo["prev_repetition"]
    sr.review_count = undo["prev_review_count"]
    sr.next_review_date = undo["prev_next_review"]
    sr.last_review_date = undo["prev_last_review"]

    db.commit()

    # 清除撤销缓存
    del _undo_store[user.id]

    return {
        "message": "已撤销",
        "word_id": sr.word_id,
        "stage": sr.stage,
        "interval": sr.interval,
    }
