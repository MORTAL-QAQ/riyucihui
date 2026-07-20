"""Achievement definitions and checking logic."""

from datetime import date, timedelta

from sqlalchemy import func, select

from sqlalchemy.orm import Session
from ..models import Achievement, Essay, GrammarCompare, StudyRecord, UsageRecord, User, Word

# Categories for grouping in the UI
CATEGORIES = {
    "word": "📝 单词收集",
    "memorize": "🧠 记忆大师",
    "essay": "✍️ 短文写作",
    "grammar": "🎯 语法学习",
    "study": "📖 背诵练习",
    "streak": "🔥 连续学习",
    "mastery": "👑 单词掌握",
}

ACHIEVEMENTS = {
    # ── 单词收集 ──
    "first_word": {"category": "word", "name": "初めての単語", "description": "保存第一个单词", "icon": "📝"},
    "words_50": {"category": "word", "name": "単語コレクター", "description": "累计保存50个单词", "icon": "📚"},
    "words_200": {"category": "word", "name": "単語マスター", "description": "累计保存200个单词", "icon": "🎓"},
    # ── 词单管理 (merged into 单词收集) ──
    "topics_5": {"category": "word", "name": "トピック探検家", "description": "创建5个不同主题的词单", "icon": "🗺️"},
    # ── 记忆大师 ──
    "memory_10": {"category": "memorize", "name": "記憶の芽生え", "description": "背诵过10个不同的单词", "icon": "🌱"},
    "memory_30": {"category": "memorize", "name": "記憶の成長", "description": "背诵过30个不同的单词", "icon": "🌿"},
    "memory_50": {"category": "memorize", "name": "記憶の達人", "description": "背诵过50个不同的单词", "icon": "💡"},
    "memory_100": {"category": "memorize", "name": "記憶の巨匠", "description": "背诵过100个不同的单词", "icon": "🔮"},
    "memory_200": {"category": "memorize", "name": "記憶の賢者", "description": "背诵过200个不同的单词", "icon": "📯"},
    "memory_300": {"category": "memorize", "name": "記憶の王者", "description": "背诵过300个不同的单词", "icon": "👑"},
    "memory_500": {"category": "memorize", "name": "記憶の神話", "description": "背诵过500个不同的单词", "icon": "🌈"},
    # ── 短文写作 ──
    "first_essay": {"category": "essay", "name": "短文作家", "description": "保存第一篇短文", "icon": "✍️"},
    "essays_10": {"category": "essay", "name": "多作の作家", "description": "保存10篇短文", "icon": "📖"},
    # ── 语法学习 ──
    "grammar_all": {"category": "grammar", "name": "文法博士", "description": "使用过全部3种语法功能", "icon": "🎯"},
    # ── 背诵练习 ──
    "study_50": {"category": "study", "name": "勤勉な学習者", "description": "累计背诵50次", "icon": "💪"},
    "study_200": {"category": "study", "name": "知識の探究者", "description": "累计背诵200次", "icon": "🧠"},
    "study_500": {"category": "study", "name": "記憶の達人", "description": "累计背诵500次", "icon": "🏋️"},
    "study_1000": {"category": "study", "name": "伝説の学習者", "description": "累计背诵1000次", "icon": "🌟"},
    # ── 连续学习 ──
    "streak_1": {"category": "streak", "name": "初日", "description": "连续学习1天", "icon": "🌅"},
    "streak_3": {"category": "streak", "name": "三日坊主突破", "description": "连续学习3天", "icon": "🔥"},
    "streak_7": {"category": "streak", "name": "週間皆勤", "description": "连续学习7天", "icon": "✨"},
    "streak_10": {"category": "streak", "name": "十日皆勤", "description": "连续学习10天", "icon": "💎"},
    "streak_30": {"category": "streak", "name": "月間皆勤", "description": "连续学习30天", "icon": "🏅"},
    "streak_100": {"category": "streak", "name": "百折不撓", "description": "连续学习100天", "icon": "🏆"},
    # ── 单词掌握 ──
    "master_20": {"category": "mastery", "name": "完璧主義者", "description": "掌握20个单词（达到阶段7）", "icon": "⭐"},
    "master_50": {"category": "mastery", "name": "単語仙人", "description": "掌握50个单词（达到阶段7）", "icon": "👑"},
    "master_100": {"category": "mastery", "name": "単語皇帝", "description": "掌握100个单词（达到阶段7）", "icon": "🏅"},
    "master_200": {"category": "mastery", "name": "語彙の神髄", "description": "掌握200个单词（达到阶段7）", "icon": "🎖️"},
}


def get_user_achievements(db: Session, user_id: int) -> list[dict]:
    """Return all achievements with their status for a user, grouped by category."""
    rows = (
        db.execute(
            select(Achievement).where(Achievement.user_id == user_id)
        )
        .scalars()
        .all()
    )
    achieved_map = {r.key: r.achieved_at for r in rows}

    result = []
    for key, info in ACHIEVEMENTS.items():
        result.append({
            "key": key,
            "category": info["category"],
            "name": info["name"],
            "description": info["description"],
            "icon": info["icon"],
            "achieved": key in achieved_map,
            "achieved_at": achieved_map.get(key),
        })
    return result


def _award(db: Session, user_id: int, key: str) -> bool:
    """Award an achievement if not already earned. Returns True if newly awarded."""
    existing = db.execute(
        select(Achievement).where(
            Achievement.user_id == user_id, Achievement.key == key
        )
    ).scalar()
    if existing:
        return False
    db.add(Achievement(user_id=user_id, key=key))
    db.flush()
    return True


def _calc_longest_streak(db: Session, user_id: int) -> int:
    """Calculate the longest consecutive study day streak for a user."""
    rows = db.execute(
        select(func.distinct(StudyRecord.last_review_date))
        .where(
            StudyRecord.user_id == user_id,
            StudyRecord.last_review_date.isnot(None),
        )
        .order_by(StudyRecord.last_review_date.desc())
    ).scalars().all()

    if not rows:
        return 0

    # rows are descending; reverse to ascending for streak calc
    dates = [d for d in rows if isinstance(d, date)]
    if not dates:
        return 0

    sorted_dates = sorted(dates)

    longest = 1
    current = 1
    for i in range(1, len(sorted_dates)):
        delta = (sorted_dates[i] - sorted_dates[i - 1]).days
        if delta == 1:
            current += 1
        elif delta == 0:
            continue  # same day, skip
        else:
            if current > longest:
                longest = current
            current = 1
    if current > longest:
        longest = current

    return longest


def check_achievements(db: Session, user_id: int):
    """Check all achievement conditions for a user and award any newly earned ones."""
    newly_awarded = []

    # ── Word count ──
    word_count = db.scalar(
        select(func.count(Word.id)).where(Word.user_id == user_id)
    ) or 0
    if word_count >= 1 and _award(db, user_id, "first_word"):
        newly_awarded.append("first_word")
    if word_count >= 50 and _award(db, user_id, "words_50"):
        newly_awarded.append("words_50")
    if word_count >= 200 and _award(db, user_id, "words_200"):
        newly_awarded.append("words_200")

    # ── Topic count ──
    topic_count = db.scalar(
        select(func.count(func.distinct(Word.topic))).where(Word.user_id == user_id)
    ) or 0
    if topic_count >= 5 and _award(db, user_id, "topics_5"):
        newly_awarded.append("topics_5")

    # ── Memory: distinct words studied ──
    memory_count = db.scalar(
        select(func.count(func.distinct(StudyRecord.word_id))).where(
            StudyRecord.user_id == user_id
        )
    ) or 0
    if memory_count >= 10 and _award(db, user_id, "memory_10"):
        newly_awarded.append("memory_10")
    if memory_count >= 30 and _award(db, user_id, "memory_30"):
        newly_awarded.append("memory_30")
    if memory_count >= 50 and _award(db, user_id, "memory_50"):
        newly_awarded.append("memory_50")
    if memory_count >= 100 and _award(db, user_id, "memory_100"):
        newly_awarded.append("memory_100")
    if memory_count >= 200 and _award(db, user_id, "memory_200"):
        newly_awarded.append("memory_200")
    if memory_count >= 300 and _award(db, user_id, "memory_300"):
        newly_awarded.append("memory_300")
    if memory_count >= 500 and _award(db, user_id, "memory_500"):
        newly_awarded.append("memory_500")

    # ── Essay count ──
    essay_count = db.scalar(
        select(func.count(Essay.id)).where(Essay.user_id == user_id)
    ) or 0
    if essay_count >= 1 and _award(db, user_id, "first_essay"):
        newly_awarded.append("first_essay")
    if essay_count >= 10 and _award(db, user_id, "essays_10"):
        newly_awarded.append("essays_10")

    # ── Grammar: used all 3 features ──
    kinds = db.execute(
        select(func.distinct(UsageRecord.kind)).where(
            UsageRecord.user_id == user_id,
            UsageRecord.kind.in_(["grammar_analyze", "grammar_correct", "grammar_compare"]),
        )
    ).scalars().all()
    if len(set(kinds)) >= 3 and _award(db, user_id, "grammar_all"):
        newly_awarded.append("grammar_all")

    # ── Study count ──
    study_count = db.scalar(
        select(func.count(StudyRecord.id)).where(StudyRecord.user_id == user_id)
    ) or 0
    if study_count >= 50 and _award(db, user_id, "study_50"):
        newly_awarded.append("study_50")
    if study_count >= 200 and _award(db, user_id, "study_200"):
        newly_awarded.append("study_200")
    if study_count >= 500 and _award(db, user_id, "study_500"):
        newly_awarded.append("study_500")
    if study_count >= 1000 and _award(db, user_id, "study_1000"):
        newly_awarded.append("study_1000")

    # ── Mastered words (stage >= 7) ──
    master_count = db.scalar(
        select(func.count(StudyRecord.id)).where(
            StudyRecord.user_id == user_id, StudyRecord.stage >= 7
        )
    ) or 0
    if master_count >= 20 and _award(db, user_id, "master_20"):
        newly_awarded.append("master_20")
    if master_count >= 50 and _award(db, user_id, "master_50"):
        newly_awarded.append("master_50")
    if master_count >= 100 and _award(db, user_id, "master_100"):
        newly_awarded.append("master_100")
    if master_count >= 200 and _award(db, user_id, "master_200"):
        newly_awarded.append("master_200")

    # ── Consecutive study streak ──
    streak = _calc_longest_streak(db, user_id)
    if streak >= 1 and _award(db, user_id, "streak_1"):
        newly_awarded.append("streak_1")
    if streak >= 3 and _award(db, user_id, "streak_3"):
        newly_awarded.append("streak_3")
    if streak >= 7 and _award(db, user_id, "streak_7"):
        newly_awarded.append("streak_7")
    if streak >= 10 and _award(db, user_id, "streak_10"):
        newly_awarded.append("streak_10")
    if streak >= 30 and _award(db, user_id, "streak_30"):
        newly_awarded.append("streak_30")
    if streak >= 100 and _award(db, user_id, "streak_100"):
        newly_awarded.append("streak_100")

    if newly_awarded:
        db.commit()
        return [ACHIEVEMENTS[k] for k in newly_awarded]
    return []
