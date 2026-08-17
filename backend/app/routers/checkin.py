"""每日签到路由。

- GET /api/checkin/status — 签到状态（是否已签 / 连续天数 / 累计次数）+ 今日推荐单词
- POST /api/checkin — 执行签到：记录签到 + 把今日推荐单词归入用户「签到单词」词单（words.topic）
  （幂等：当天已签到则直接返回当前状态，不重复入库）

设计说明：
- 日期按北京时区（UTC+8）计算，跨天以北京零点为界
- 每日推荐单词确定性选取（按日期序数取模），GET 与 POST 当天返回同一单词：
  优先从用户自己的词库随机取样（排除「签到单词」词单），词库为空时回退内置词表
- 单词入库时按 (japanese, kana) 在「签到单词」词单内去重，不产生重复记录
"""

import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Checkin, User, Word
from ..schemas import CHECKIN_TOPIC, CheckinStatus, CheckinWord

router = APIRouter(prefix="/api/checkin", tags=["checkin"])

logger = logging.getLogger(__name__)

# 北京时区偏移（无 zoneinfo 依赖的轻量实现）
_BJ_OFFSET = timedelta(hours=8)

# 词库为空时的内置兜底词表（常见 JLPT 词）
_BUILTIN_WORDS = [
    {
        "japanese": "桜",
        "kana": "さくら",
        "chinese": "樱花",
        "example_ja": "春になると桜が咲きます。",
        "example_cn": "春天一到樱花就开了。",
        "jlpt_level": "N4",
    },
    {
        "japanese": "猫",
        "kana": "ねこ",
        "chinese": "猫",
        "example_ja": "うちの猫は魚が好きです。",
        "example_cn": "我家的猫喜欢吃鱼。",
        "jlpt_level": "N5",
    },
    {
        "japanese": "勉強",
        "kana": "べんきょう",
        "chinese": "学习",
        "example_ja": "毎日日本語を勉強しています。",
        "example_cn": "我每天都在学习日语。",
        "jlpt_level": "N5",
    },
    {
        "japanese": "旅",
        "kana": "たび",
        "chinese": "旅行",
        "example_ja": "日本の旅は楽しいです。",
        "example_cn": "去日本旅行很开心。",
        "jlpt_level": "N4",
    },
    {
        "japanese": "月",
        "kana": "つき",
        "chinese": "月亮；月份",
        "example_ja": "今夜は月がきれいですね。",
        "example_cn": "今晚的月亮真美啊。",
        "jlpt_level": "N5",
    },
    {
        "japanese": "本",
        "kana": "ほん",
        "chinese": "书",
        "example_ja": "この本はとても面白いです。",
        "example_cn": "这本书非常有趣。",
        "jlpt_level": "N5",
    },
    {
        "japanese": "友達",
        "kana": "ともだち",
        "chinese": "朋友",
        "example_ja": "友達と映画を見に行きました。",
        "example_cn": "和朋友去看了电影。",
        "jlpt_level": "N5",
    },
    {
        "japanese": "空",
        "kana": "そら",
        "chinese": "天空",
        "example_ja": "今日は青い空が広がっています。",
        "example_cn": "今天晴空万里。",
        "jlpt_level": "N4",
    },
    {
        "japanese": "未来",
        "kana": "みらい",
        "chinese": "未来",
        "example_ja": "未来のために頑張ります。",
        "example_cn": "为了未来而努力。",
        "jlpt_level": "N4",
    },
    {
        "japanese": "幸せ",
        "kana": "しあわせ",
        "chinese": "幸福",
        "example_ja": "家族と過ごす時間が一番幸せです。",
        "example_cn": "和家人一起度过的时光最幸福。",
        "jlpt_level": "N4",
    },
]


def _beijing_today() -> date:
    """北京时区今天的日期。"""
    return (datetime.now(timezone.utc) + _BJ_OFFSET).date()


def _daily_word(db: Session, user_id: int, today: date):
    """确定性选取今日推荐单词（GET/POST 当天一致）。

    优先从用户自己的词库取（排除「签到单词」词单，按 id 稳定排序 + 日期取模）；
    词库为空时回退内置词表。
    """
    words = db.execute(
        select(Word)
        .where(Word.user_id == user_id, Word.topic != CHECKIN_TOPIC)
        .order_by(Word.id)
    ).scalars().all()
    if words:
        idx = today.toordinal() % len(words)
        return words[idx]
    idx = today.toordinal() % len(_BUILTIN_WORDS)
    return _BUILTIN_WORDS[idx]


def _to_checkin_word(word) -> CheckinWord:
    """Word 行或内置 dict → CheckinWord。"""
    if isinstance(word, Word):
        return CheckinWord(
            id=word.id,
            japanese=word.japanese,
            kana=word.kana,
            chinese=word.chinese,
            example_ja=word.example_ja,
            example_cn=word.example_cn,
            jlpt_level=word.jlpt_level,
        )
    return CheckinWord(**word)


def _ensure_checkin_word(db: Session, user_id: int, word) -> Word:
    """把推荐单词归入「签到单词」词单（按 japanese+kana 去重）。"""
    japanese = word.japanese if isinstance(word, Word) else word["japanese"]
    kana = word.kana if isinstance(word, Word) else word["kana"]
    existing = db.execute(
        select(Word).where(
            Word.user_id == user_id,
            Word.topic == CHECKIN_TOPIC,
            Word.japanese == japanese,
            Word.kana == kana,
        )
    ).scalars().first()
    if existing:
        return existing
    record = Word(
        user_id=user_id,
        topic=CHECKIN_TOPIC,
        japanese=japanese,
        kana=kana,
        chinese=word.chinese if isinstance(word, Word) else word["chinese"],
        example_ja=word.example_ja if isinstance(word, Word) else word["example_ja"],
        example_cn=word.example_cn if isinstance(word, Word) else word["example_cn"],
        jlpt_level=word.jlpt_level if isinstance(word, Word) else word.get("jlpt_level"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _status(db: Session, user_id: int, today: date) -> CheckinStatus:
    """组装签到状态 + 今日推荐单词。"""
    dates = {
        r[0] for r in db.execute(select(Checkin.checkin_date).where(Checkin.user_id == user_id)).all()
    }
    total = len(dates)
    checked_in = today in dates

    # 连续签到：今天已签则从今天往前数；今天未签但昨天签了则连续天数仍有效（今天补签可延续）
    cursor = today if checked_in else today - timedelta(days=1)
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)

    word = _daily_word(db, user_id, today)
    return CheckinStatus(
        checked_in=checked_in,
        streak=streak,
        total=total,
        word=_to_checkin_word(word),
    )


@router.get("/status", response_model=CheckinStatus)
def get_checkin_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """签到状态 + 今日推荐单词。"""
    return _status(db, user.id, _beijing_today())


@router.post("", response_model=CheckinStatus)
def do_checkin(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """执行签到（幂等）：记录签到 + 把今日推荐单词加入「签到单词」词单。"""
    today = _beijing_today()

    # 幂等：当天已签到直接返回当前状态
    existing = db.execute(
        select(Checkin.id).where(
            Checkin.user_id == user.id, Checkin.checkin_date == today
        )
    ).first()
    if existing:
        status = _status(db, user.id, today)
        status.newly = False
        return status

    db.add(Checkin(user_id=user.id, checkin_date=today))
    db.commit()

    # 今日推荐单词 → 签到单词词单
    word = _daily_word(db, user.id, today)
    _ensure_checkin_word(db, user.id, word)
    jp = word.japanese if isinstance(word, Word) else word["japanese"]
    logger.info("用户 %s 今日签到，推荐词「%s」已加入签到单词词单", user.username, jp)

    status = _status(db, user.id, today)
    status.newly = True
    return status
