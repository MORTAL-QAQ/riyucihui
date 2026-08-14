"""In-memory rate limiter for auth endpoints.

No external dependencies — uses a dict with timestamp-based expiry.
For multi-process deployments, replace with Redis-backed slowapi or similar.
"""

import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request

_store: dict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()
_cleanup_ts = 0.0


def _cleanup(now: float, window: float):
    global _cleanup_ts, _store
    if now - _cleanup_ts < 60:
        return
    _cleanup_ts = now
    with _lock:
        expired = [k for k, v in _store.items() if not v or v[-1] < now - window]
        for k in expired:
            del _store[k]


def get_client_ip(request: Request) -> str:
    """Resolve the real client IP.

    只信任 nginx 反向代理写入的 X-Real-IP（nginx.conf 中
    ``proxy_set_header X-Real-IP $remote_addr`` 会覆盖客户端伪造的同名头）。

    刻意**不信任** X-Forwarded-For：该头由客户端可控，直接访问应用时可
    伪造任意值绕过 IP 级限流（攻击者每次请求换一个假 IP 即可打满配额）。
    生产架构下 backend 仅经 nginx 暴露，X-Real-IP 必然由 nginx 写入。
    """
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


def check_rate(key: str, max_requests: int = 5, window_seconds: int = 60) -> tuple[bool, int]:
    """Returns (allowed, remaining)."""
    now = time.time()
    cutoff = now - window_seconds
    _cleanup(now, window_seconds)

    with _lock:
        timestamps = _store[key]
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)
        used = len(timestamps)
        if used >= max_requests:
            return False, 0
        timestamps.append(now)
        return True, max_requests - used - 1


def rate_limit(max_requests: int = 5, window_seconds: int = 60):
    """FastAPI dependency: limit requests per IP + endpoint."""

    async def _limiter(request: Request):
        client_ip = get_client_ip(request)
        key = f"{client_ip}:{request.url.path}"
        allowed, remaining = check_rate(key, max_requests, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"请求过于频繁，请 {window_seconds} 秒后再试",
                headers={"Retry-After": str(window_seconds)},
            )

    return _limiter


def check_username_rate(
    username: str, endpoint: str, max_requests: int = 5, window_seconds: int = 60
):
    """Raise HTTPException 429 if the username has exceeded its per-account rate limit.

    This prevents targeted brute force against a single account even when the
    attacker rotates IPs, because the limit is keyed on username + endpoint.
    """
    key = f"user:{username}:{endpoint}"
    allowed, remaining = check_rate(key, max_requests, window_seconds)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"该账号请求过于频繁，请 {window_seconds} 秒后再试",
            headers={"Retry-After": str(window_seconds)},
        )
