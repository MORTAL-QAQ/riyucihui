from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException

# 北京时间
CST = timezone(timedelta(hours=8))


def _to_cst(dt: datetime | None) -> str:
    """将 UTC 时间转为北京时间字符串"""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CST).strftime("%Y-%m-%d %H:%M:%S")
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from ..auth import get_admin_user, hash_password
from ..database import get_db
from ..models import LoginHistory, StudyRecord, UsageRecord, User, Word
from ..services.usage_service import get_usage_summary, get_user_usage

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminUserOut(BaseModel):
    id: int
    username: str
    is_admin: bool
    daily_ai_limit: int | None = None
    daily_voice_limit: int | None = None
    daily_word_limit: int | None = None
    daily_image_limit: int | None = None
    remark: str | None = None
    created_at: str
    word_count: int
    study_count: int
    usage: dict | None = None

    class Config:
        from_attributes = True


class AdminStatsOut(BaseModel):
    total_users: int
    total_words: int
    total_study_records: int
    admin_count: int
    total_ai_calls: int = 0
    total_voice_calls: int = 0
    total_tokens: int = 0


class SetLimitsRequest(BaseModel):
    daily_ai_limit: int | None = None  # null = 不限
    daily_voice_limit: int | None = None  # null = 不限
    daily_word_limit: int | None = None  # null = 不限（普通用户默认100）


class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=6, max_length=100)

    @field_validator("password")
    @classmethod
    def _check_password_bytes(cls, v: str) -> str:
        # bcrypt 只使用前 72 字节（UTF-8）
        if len(v.encode("utf-8")) > 72:
            raise ValueError("密码过长（UTF-8 编码超过 72 字节）")
        return v


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    # Subqueries for word/study counts — avoid N+1 per-user COUNT queries
    wc_sub = (
        select(Word.user_id, func.count(Word.id).label("cnt"))
        .group_by(Word.user_id)
    ).subquery()
    sc_sub = (
        select(StudyRecord.user_id, func.count(StudyRecord.id).label("cnt"))
        .group_by(StudyRecord.user_id)
    ).subquery()

    stmt = (
        select(
            User,
            func.coalesce(wc_sub.c.cnt, 0).label("word_count"),
            func.coalesce(sc_sub.c.cnt, 0).label("study_count"),
        )
        .outerjoin(wc_sub, User.id == wc_sub.c.user_id)
        .outerjoin(sc_sub, User.id == sc_sub.c.user_id)
        .order_by(User.is_admin.desc(), User.id)
    )
    rows = db.execute(stmt).all()

    # Batch usage for all users — single query instead of N
    # AI 调用种类（与 usage_service._AI_KINDS 保持一致）
    _ADMIN_AI_KINDS = ["essay", "cloze", "grammar_analyze", "grammar_correct", "grammar_compare"]
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    usage_rows = db.execute(
        select(
            UsageRecord.user_id,
            func.sum(
                case((UsageRecord.kind.in_(_ADMIN_AI_KINDS), 1), else_=0)
            ).label("total_ai"),
            func.sum(
                case((UsageRecord.kind == "voice", 1), else_=0)
            ).label("total_voice"),
            func.sum(
                case((UsageRecord.kind == "image_generation", 1), else_=0)
            ).label("total_image"),
            func.sum(
                case((UsageRecord.kind == "generated_words", UsageRecord.tokens_used), else_=0)
            ).label("total_word"),
            func.sum(
                case(
                    (
                        and_(
                            UsageRecord.created_at >= today,
                            UsageRecord.kind.in_(_ADMIN_AI_KINDS),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("today_ai"),
            func.sum(
                case(
                    (
                        and_(
                            UsageRecord.created_at >= today,
                            UsageRecord.kind == "voice",
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("today_voice"),
            func.sum(
                case(
                    (
                        and_(
                            UsageRecord.created_at >= today,
                            UsageRecord.kind == "generated_words",
                        ),
                        UsageRecord.tokens_used,
                    ),
                    else_=0,
                )
            ).label("today_word"),
            func.sum(
                case(
                    (
                        and_(
                            UsageRecord.created_at >= today,
                            UsageRecord.kind == "image_generation",
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("today_image"),
        ).group_by(UsageRecord.user_id)
    ).all()

    usage_map = {}
    for row in usage_rows:
        usage_map[row.user_id] = {
            "today_ai": row.today_ai or 0,
            "today_voice": row.today_voice or 0,
            "total_ai": row.total_ai or 0,
            "total_voice": row.total_voice or 0,
            "today_word": row.today_word or 0,
            "total_word": row.total_word or 0,
            "today_image": row.today_image or 0,
            "total_image": row.total_image or 0,
        }

    result = []
    for row in rows:
        u = row[0]
        uid = u.id
        result.append(
            AdminUserOut(
                id=uid,
                username=u.username,
                is_admin=u.is_admin,
                daily_ai_limit=u.daily_ai_limit,
                daily_voice_limit=u.daily_voice_limit,
                daily_word_limit=u.daily_word_limit,
                daily_image_limit=u.daily_image_limit,
                remark=u.remark,
                created_at=_to_cst(u.created_at),
                word_count=row.word_count,
                study_count=row.study_count,
                usage=usage_map.get(
                    uid,
                    {"today_ai": 0, "today_voice": 0, "total_ai": 0, "total_voice": 0, "today_word": 0, "total_word": 0, "today_image": 0, "total_image": 0},
                ),
            )
        )
    return result


@router.get("/stats", response_model=AdminStatsOut)
def get_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    usage = get_usage_summary(db)
    return AdminStatsOut(
        total_users=db.query(func.count(User.id)).scalar() or 0,
        total_words=db.query(func.count(Word.id)).scalar() or 0,
        total_study_records=db.query(func.count(StudyRecord.id)).scalar() or 0,
        admin_count=db.query(func.count(User.id)).filter(User.is_admin.is_(True)).scalar() or 0,
        total_ai_calls=usage["total_ai_calls"],
        total_voice_calls=usage["total_voice_calls"],
        total_tokens=usage["total_tokens"],
    )


@router.put("/users/{user_id}/admin")
def toggle_admin(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能修改自己的管理员状态")
    user.is_admin = not user.is_admin
    db.commit()
    return {"message": f"用户 {user.username} {'已是管理员' if user.is_admin else '已取消管理员'}"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    username = user.username
    db.delete(user)
    db.commit()
    return {"message": f"已删除用户 {username}"}


@router.put("/users/{user_id}/limits")
def set_user_limits(
    user_id: int,
    body: SetLimitsRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Set daily usage limits for a user. null = unlimited."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.daily_ai_limit = body.daily_ai_limit
    user.daily_voice_limit = body.daily_voice_limit
    user.daily_word_limit = body.daily_word_limit
    db.commit()

    return {
        "message": f"用户 {user.username} 限额已更新",
        "daily_ai_limit": user.daily_ai_limit,
        "daily_voice_limit": user.daily_voice_limit,
        "daily_word_limit": user.daily_word_limit,
    }


class SetRemarkRequest(BaseModel):
    remark: str | None = Field(default=None, max_length=200)


@router.put("/users/{user_id}/remark")
def set_user_remark(
    user_id: int,
    body: SetRemarkRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Set or clear the admin remark for a user."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.remark = body.remark
    db.commit()
    return {"message": "备注已更新", "remark": user.remark}


@router.put("/users/{user_id}/password")
def reset_user_password(
    user_id: int,
    body: ResetPasswordRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Admin reset a user's password."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="请通过设置页面修改自己的密码")

    user.password_hash = hash_password(body.password)
    user.token_version = user.token_version + 1  # invalidate existing tokens
    db.commit()
    return {"message": f"用户 {user.username} 的密码已重置"}


@router.get("/usage")
def get_usage_overview(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Get system-wide usage overview."""
    return get_usage_summary(db)


@router.get("/users/{user_id}/usage")
def get_user_usage_detail(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    usage = get_user_usage(db, user_id)
    return {
        "user_id": user_id,
        "username": user.username,
        "daily_ai_limit": user.daily_ai_limit,
        "daily_voice_limit": user.daily_voice_limit,
        **usage,
    }


class LoginHistoryOut(BaseModel):
    username: str
    login_at: str
    ip_address: str | None = None
    user_agent: str | None = None

    class Config:
        from_attributes = True


class UserLoginReport(BaseModel):
    user_id: int
    username: str
    login_count: int
    first_login: str | None = None
    last_login: str | None = None
    logins: list[LoginHistoryOut]


@router.get("/login-history", response_model=list[UserLoginReport])
def get_login_history(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """获取所有用户的登录历史报告。每个用户一张表格，含登录次数和每次登录详情。"""
    # 查所有登录记录，按用户和时间排序
    rows = (
        db.query(
            LoginHistory.user_id,
            User.username,
            LoginHistory.login_at,
            LoginHistory.ip_address,
            LoginHistory.user_agent,
        )
        .join(User, LoginHistory.user_id == User.id)
        .order_by(LoginHistory.user_id, LoginHistory.login_at.desc())
        .all()
    )

    if not rows:
        return []

    # 按用户分组
    from collections import OrderedDict
    user_data: dict[int, dict] = OrderedDict()

    for uid, uname, login_at, ip_addr, ua in rows:
        if uid not in user_data:
            user_data[uid] = {
                "user_id": uid,
                "username": uname,
                "logins": [],
            }
        user_data[uid]["logins"].append(
            LoginHistoryOut(
                username=uname,
                login_at=_to_cst(login_at),
                ip_address=ip_addr,
                user_agent=ua,
            )
        )

    result = []
    for uid, data in user_data.items():
        logins = data["logins"]
        result.append(
            UserLoginReport(
                user_id=uid,
                username=data["username"],
                login_count=len(logins),
                first_login=logins[-1].login_at if logins else None,
                last_login=logins[0].login_at if logins else None,
                logins=logins,
            )
        )

    # 按最后一次登陆时间降序排列
    result.sort(key=lambda r: r.last_login or "", reverse=True)

    return result
