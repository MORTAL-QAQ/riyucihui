"""API 用量限制与记录服务。

功能：
- check_limit(): 检查用户今日调用次数是否达上限
- record_usage(): 在独立事务中记录一次 API 调用（不干扰调用方的事务）
- get_usage_summary(): 管理员仪表盘统计

支持的调用类型（_AI_KINDS）：generate, essay, cloze, grammar_analyze, grammar_correct, grammar_compare
语音合成单独计数，不加 AI 限制。
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import engine
from ..models import UsageRecord

_AI_KINDS = {"generate", "essay", "cloze", "grammar_analyze", "grammar_correct", "grammar_compare"}


def _is_ai_kind(kind: str) -> bool:
    return kind in _AI_KINDS


def record_usage(_caller_db, user_id: int, kind: str, tokens_used: int = 0):
    """Log an API usage event in its own isolated transaction.

    Uses a separate connection so the usage record is persisted
    independently — the caller's session is never touched, and any
    uncommitted changes the caller holds are unaffected.
    """
    try:
        with engine.connect() as conn:
            conn.execute(
                UsageRecord.__table__.insert().values(
                    user_id=user_id, kind=kind, tokens_used=tokens_used,
                ),
            )
            conn.commit()
    except Exception:
        pass  # usage logging is best-effort; never break the caller


def count_today(db: Session, user_id: int, kind: str) -> int:
    """Count today's usage for a given user and kind."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = select(func.count(UsageRecord.id)).where(
        UsageRecord.user_id == user_id,
        UsageRecord.kind == kind,
        UsageRecord.created_at >= today,
    )
    return db.execute(stmt).scalar() or 0


def get_user_daily_limit(db: Session, user_id: int, kind: str) -> int | None:
    """Return the daily limit for a user, or None if unlimited."""
    from ..models import User

    user = db.get(User, user_id)
    if user is None:
        return 0
    if _is_ai_kind(kind):
        return user.daily_ai_limit
    if kind == "voice":
        return user.daily_voice_limit
    if kind == "image_generation":
        # 未设置时默认3张/天（管理员除外，管理员 unlimited）
        return user.daily_image_limit if user.daily_image_limit is not None else (None if user.is_admin else 3)
    return None


def check_limit(db: Session, user_id: int, kind: str) -> tuple[bool, str]:
    """
    Returns (allowed, message).
    Admin users always pass.
    """
    from ..models import User

    user = db.get(User, user_id)
    if user and user.is_admin:
        return True, ""

    limit = get_user_daily_limit(db, user_id, kind)
    if limit is None:
        return True, ""

    used = count_today(db, user_id, kind)
    if used >= limit:
        kind_name = {
            "generate": "AI生成单词", "essay": "AI生成短文", "cloze": "AI完型填空", "voice": "语音合成",
            "grammar_analyze": "语法分析", "grammar_correct": "语法纠错", "grammar_compare": "语法辨析",
            "image_generation": "AI图片生成",
        }.get(kind, kind)
        return False, f"今日{kind_name}次数已达上限（{limit}次/天）"
    return True, ""


def get_usage_summary(db: Session) -> dict:
    """Get total usage summary for admin dashboard."""
    total_ai = (
        db.query(func.count(UsageRecord.id))
        .filter(UsageRecord.kind.in_(list(_AI_KINDS)))
        .scalar()
        or 0
    )

    total_voice = (
        db.query(func.count(UsageRecord.id)).filter(UsageRecord.kind == "voice").scalar() or 0
    )

    total_tokens = db.query(func.coalesce(func.sum(UsageRecord.tokens_used), 0)).scalar()

    return {
        "total_ai_calls": total_ai,
        "total_voice_calls": total_voice,
        "total_tokens": total_tokens,
    }


def get_user_usage(db: Session, user_id: int) -> dict:
    """Get today's and total usage for a single user."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    def _count(kind, since=None):
        stmt = select(func.count(UsageRecord.id)).where(
            UsageRecord.user_id == user_id,
            UsageRecord.kind == kind,
        )
        if since is not None:
            stmt = stmt.where(UsageRecord.created_at >= since)
        return db.execute(stmt).scalar() or 0

    return {
        "today_ai": sum(_count(k, today) for k in _AI_KINDS),
        "today_voice": _count("voice", today),
        "total_ai": sum(_count(k) for k in _AI_KINDS),
        "total_voice": _count("voice"),
    }
