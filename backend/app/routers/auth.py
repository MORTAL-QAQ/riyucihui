from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import create_access_token, get_admin_user, get_current_user, hash_password, verify_password
from .. import config
from ..database import get_db
from ..models import LoginHistory, User
from ..schemas import USERNAME_PATTERN, LoginRequest, RegisterRequest, TokenResponse, UserOut
from ..services.rate_limiter import check_username_rate, rate_limit

router = APIRouter(prefix="/api", tags=["auth"])

AUTH_RATE_LIMIT = rate_limit(max_requests=10, window_seconds=60)  # 10/min per IP for login
REGISTER_RATE_LIMIT = rate_limit(max_requests=3, window_seconds=3600)  # 3/hour per IP for register
LOGIN_USERNAME_LIMIT = 5  # max attempts per username per minute
LOGIN_USERNAME_WINDOW = 60  # window in seconds


@router.post("/register", response_model=TokenResponse)
def register(
    req: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    _rate: None = Depends(REGISTER_RATE_LIMIT),
):
    """公开注册。"""
    # 预检查（快速路径）；check-then-insert 存在竞态，最终以唯一约束兜底（见下方 IntegrityError）
    existing = db.execute(select(User).where(User.username == req.username)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已被注册")

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        daily_ai_limit=config.DEFAULT_DAILY_AI_LIMIT,
        daily_image_limit=config.DEFAULT_DAILY_IMAGE_LIMIT,
        daily_word_limit=config.DEFAULT_DAILY_WORD_LIMIT,
        daily_voice_limit=config.DEFAULT_DAILY_VOICE_LIMIT,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # 并发注册同一用户名 → 撞唯一约束，返回 409 而非 500
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已被注册")
    db.refresh(user)

    token = create_access_token(user.id, user.token_version)

    client_ip = request.client.host if request.client else None
    client_ua = request.headers.get("User-Agent", "")[:500]
    login_record = LoginHistory(
        user_id=user.id,
        ip_address=client_ip,
        user_agent=client_ua,
    )
    db.add(login_record)
    db.commit()

    return TokenResponse(access_token=token, username=user.username, is_admin=user.is_admin)


class AdminCreateUserRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, pattern=USERNAME_PATTERN)
    password: str = Field(..., min_length=6, max_length=72)

    @field_validator("password")
    @classmethod
    def _check_password_bytes(cls, v: str) -> str:
        # bcrypt 只使用前 72 字节（UTF-8）
        if len(v.encode("utf-8")) > 72:
            raise ValueError("密码过长（UTF-8 编码超过 72 字节）")
        return v


@router.post("/admin/create-user")
def admin_create_user(
    req: AdminCreateUserRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """管理员创建新用户。"""
    existing = db.execute(select(User).where(User.username == req.username)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已被注册")

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        daily_ai_limit=config.DEFAULT_DAILY_AI_LIMIT,
        daily_image_limit=config.DEFAULT_DAILY_IMAGE_LIMIT,
        daily_word_limit=config.DEFAULT_DAILY_WORD_LIMIT,
        daily_voice_limit=config.DEFAULT_DAILY_VOICE_LIMIT,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已被注册")
    db.refresh(user)
    return {"message": f"用户 {user.username} 创建成功", "user_id": user.id, "username": user.username}


@router.post("/login", response_model=TokenResponse)
def login(
    req: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    _rate: None = Depends(AUTH_RATE_LIMIT),
):
    # Per-username rate limit — prevents brute force on a single account
    # even if the attacker rotates IPs
    check_username_rate(req.username, "login", LOGIN_USERNAME_LIMIT, LOGIN_USERNAME_WINDOW)

    user = db.execute(select(User).where(User.username == req.username)).scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    token = create_access_token(user.id, user.token_version)

    # 记录登录历史
    client_ip = request.client.host if request.client else None
    client_ua = request.headers.get("User-Agent", "")[:500]  # 截断到 500 字符
    login_record = LoginHistory(
        user_id=user.id,
        ip_address=client_ip,
        user_agent=client_ua,
    )
    db.add(login_record)
    db.commit()

    return TokenResponse(access_token=token, username=user.username, is_admin=user.is_admin)


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Invalidate all existing tokens for this user by incrementing token_version."""
    db.execute(
        update(User).where(User.id == current_user.id).values(token_version=User.token_version + 1)
    )
    db.commit()
    return {"message": "已退出登录"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """当前用户信息。

    成就检查只在触发成就的操作（保存单词/学习/写作等）后执行，不放在
    /me 与 login 等高频路径上（每次 10+ 次聚合查询，见 #26）。
    """
    return UserOut.model_validate(current_user)
