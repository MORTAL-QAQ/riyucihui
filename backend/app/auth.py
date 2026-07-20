"""认证与授权模块。

提供密码哈希、JWT Token 签发/验证、当前用户注入等认证功能。
所有需要登录的 API 端点通过 `get_current_user` 依赖注入获取当前用户。

安全机制：
- 密码使用 bcrypt 哈希存储，不可逆
- JWT Token 包含 token_version，支持批量踢出登录（修改版本号使旧 Token 失效）
- 管理员通过 `get_admin_user` 依赖进行权限校验
"""

from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from . import config
from .database import get_db
from .models import User

# bcrypt 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__truncate_error=True)
# HTTP Bearer Token 安全方案（从 Authorization 请求头提取 Token）
security = HTTPBearer()


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希。"""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码是否与哈希值匹配。"""
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, token_version: int = 0) -> str:
    """为用户签发 JWT 访问令牌。

    Args:
        user_id: 用户 ID
        token_version: Token 版本号，与用户记录的 token_version 比对可实现强制下线
    """
    expire = datetime.now(UTC) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "ver": token_version, "exp": expire}
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
) -> User:
    """FastAPI 依赖：从 HTTP Authorization 请求头解析 JWT Token，返回当前登录用户。

    验证流程：
    1. 解码 JWT Token，提取 user_id 和 token_version
    2. 查询数据库确认用户存在
    3. 比对 token_version 确认 Token 未被撤销
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        user_id = int(payload["sub"])
        token_ver = payload.get("ver", 0)
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录"
        )

    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if token_ver != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token已失效，请重新登录"
        )
    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI 依赖：要求当前用户为管理员，否则返回 403。"""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user
