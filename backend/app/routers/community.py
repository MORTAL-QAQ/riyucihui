"""社区路由 — 学习内容分享 + 管理员公告。

功能：
- 帖子：列表（公告置顶优先）、发布、详情、删除（作者/管理员）
- 互动：点赞/取消、评论/删评论
- 管理：发布公告、置顶/取消置顶、删除任意帖子（内容审核兜底）
- 审核：发布前敏感词过滤（services/sensitive_words.py）+ 管理员删帖双重机制

安全：
- 所有端点需登录（get_current_user），管理端点需管理员（get_admin_user）
- 发帖/评论有 IP 级限流（防刷）
- 内容经 pydantic 长度限制；前端渲染使用 esc() 防 XSS
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..auth import get_admin_user, get_current_user
from ..database import get_db
from ..models import Post, PostComment, PostLike, User
from ..schemas import (
    AnnouncementCreate,
    CommentCreate,
    CommentOut,
    PostCreate,
    PostDetailResponse,
    PostListResponse,
    PostOut,
)
from ..services.achievement_service import check_achievements
from ..services.rate_limiter import rate_limit
from ..services.sensitive_words import check_sensitive

router = APIRouter(prefix="/api/community", tags=["community"])

logger = logging.getLogger(__name__)

POST_IP_LIMIT = rate_limit(max_requests=5, window_seconds=60)      # 发帖 5/min per IP
COMMENT_IP_LIMIT = rate_limit(max_requests=10, window_seconds=60)   # 评论 10/min per IP
LIKE_IP_LIMIT = rate_limit(max_requests=30, window_seconds=60)      # 点赞 30/min per IP

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 50


def _reject_if_sensitive(text: str):
    """命中敏感词则 400 拒绝（发布前审核）。"""
    hit = check_sensitive(text)
    if hit:
        logger.warning("社区内容命中敏感词「%s」被拦截", hit)
        raise HTTPException(status_code=400, detail="内容包含敏感词，无法发布")


def _counts(db: Session) -> tuple[dict[int, int], dict[int, int]]:
    """一次聚合取出所有帖子的点赞数 / 评论数，避免 N+1 查询。"""
    like_counts = dict(
        db.execute(
            select(PostLike.post_id, func.count(PostLike.id)).group_by(PostLike.post_id)
        ).all()
    )
    comment_counts = dict(
        db.execute(
            select(PostComment.post_id, func.count(PostComment.id)).group_by(PostComment.post_id)
        ).all()
    )
    return like_counts, comment_counts


def _to_out(row) -> PostOut:
    """row = (Post, username, like_count, comment_count) → PostOut"""
    post, username, like_count, comment_count = row
    return PostOut(
        id=post.id,
        type=post.type,
        title=post.title,
        content=post.content,
        is_pinned=post.is_pinned,
        username=username,
        like_count=like_count,
        comment_count=comment_count,
        created_at=post.created_at,
    )


@router.get("/posts", response_model=PostListResponse)
def list_posts(
    post_type: str | None = Query(default=None, alias="type", pattern=r"^(post|announcement)$"),
    offset: int = 0,
    limit: int = _DEFAULT_LIMIT,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """社区帖子列表：置顶优先（公告），再按时间倒序。"""
    limit = min(limit, _MAX_LIMIT)
    like_counts, comment_counts = _counts(db)

    stmt = (
        select(Post, User.username)
        .join(User, Post.user_id == User.id)
        .order_by(Post.is_pinned.desc(), Post.created_at.desc())
    )
    if post_type:
        stmt = stmt.where(Post.type == post_type)

    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar() or 0

    rows = db.execute(stmt.offset(offset).limit(limit)).all()
    posts = [
        _to_out((p, username, like_counts.get(p.id, 0), comment_counts.get(p.id, 0)))
        for p, username in rows
    ]
    return PostListResponse(posts=posts, total=total)


@router.post("/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    req: PostCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate: None = Depends(POST_IP_LIMIT),
):
    """发布帖子（敏感词过滤 + 触发「首次发帖」成就）。"""
    _reject_if_sensitive(req.title)
    _reject_if_sensitive(req.content)

    post = Post(user_id=user.id, type="post", title=req.title, content=req.content)
    db.add(post)
    db.commit()
    db.refresh(post)

    new_achs = check_achievements(db, user.id)
    return PostOut(
        id=post.id, type=post.type, title=post.title, content=post.content,
        is_pinned=post.is_pinned, username=user.username,
        like_count=0, comment_count=0, created_at=post.created_at,
        new_achievements=[{"name": a["name"], "icon": a["icon"]} for a in new_achs] or None,
    )


@router.get("/posts/{post_id}", response_model=PostDetailResponse)
def get_post(
    post_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """帖子详情：内容 + 点赞/评论数 + 当前用户点赞状态 + 评论列表。"""
    row = (
        db.execute(select(Post, User.username).join(User, Post.user_id == User.id)
                   .where(Post.id == post_id))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="帖子不存在")
    post, username = row

    like_count = db.scalar(
        select(func.count(PostLike.id)).where(PostLike.post_id == post_id)
    ) or 0
    comment_count = db.scalar(
        select(func.count(PostComment.id)).where(PostComment.post_id == post_id)
    ) or 0
    liked = db.scalar(
        select(func.count(PostLike.id)).where(
            PostLike.post_id == post_id, PostLike.user_id == user.id
        )
    ) > 0

    comments = db.execute(
        select(PostComment, User.username)
        .join(User, PostComment.user_id == User.id)
        .where(PostComment.post_id == post_id)
        .order_by(PostComment.created_at)
    ).all()
    comment_outs = [
        CommentOut(id=c.id, post_id=c.post_id, content=c.content,
                   username=uname, created_at=c.created_at)
        for c, uname in comments
    ]

    post_out = PostOut(
        id=post.id, type=post.type, title=post.title, content=post.content,
        is_pinned=post.is_pinned, username=username,
        like_count=like_count, comment_count=comment_count, created_at=post.created_at,
    )
    return PostDetailResponse(
        post=post_out, liked=liked,
        is_owner=post.user_id == user.id, is_admin=user.is_admin,
        comments=comment_outs,
    )


@router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除帖子：作者本人或管理员（内容审核兜底）。"""
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if post.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="无权删除该帖子")
    db.delete(post)
    db.commit()
    return {"message": "帖子已删除"}


@router.post("/posts/{post_id}/like")
def toggle_like(
    post_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate: None = Depends(LIKE_IP_LIMIT),
):
    """点赞 / 取消点赞（首次点赞触发「送出第一个赞」成就）。"""
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    existing = db.scalar(
        select(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == user.id)
    )
    new_achs = []
    if existing:
        db.delete(existing)
        db.commit()
        liked = False
    else:
        db.add(PostLike(post_id=post_id, user_id=user.id))
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(status_code=409, detail="操作冲突，请重试")
        liked = True
        new_achs = check_achievements(db, user.id)

    like_count = db.scalar(
        select(func.count(PostLike.id)).where(PostLike.post_id == post_id)
    ) or 0
    return {
        "liked": liked,
        "like_count": like_count,
        "new_achievements": [{"name": a["name"], "icon": a["icon"]} for a in new_achs] or None,
    }


@router.post("/posts/{post_id}/comments", response_model=CommentOut,
             status_code=status.HTTP_201_CREATED)
def create_comment(
    post_id: int,
    req: CommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate: None = Depends(COMMENT_IP_LIMIT),
):
    """发表评论（敏感词过滤 + 触发「第一条评论」成就）。"""
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    _reject_if_sensitive(req.content)

    comment = PostComment(post_id=post_id, user_id=user.id, content=req.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    new_achs = check_achievements(db, user.id)
    return CommentOut(
        id=comment.id, post_id=comment.post_id, content=comment.content,
        username=user.username, created_at=comment.created_at,
        new_achievements=[{"name": a["name"], "icon": a["icon"]} for a in new_achs] or None,
    )


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除评论：作者本人或管理员。"""
    comment = db.get(PostComment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    if comment.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="无权删除该评论")
    db.delete(comment)
    db.commit()
    return {"message": "评论已删除"}


# ── 管理员：公告与置顶 ──

@router.post("/announcements", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_announcement(
    req: AnnouncementCreate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """管理员发布重要公告（默认置顶，列表优先展示）。"""
    _reject_if_sensitive(req.title)
    _reject_if_sensitive(req.content)

    post = Post(
        user_id=admin.id, type="announcement",
        title=req.title, content=req.content, is_pinned=req.pinned,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return PostOut(
        id=post.id, type=post.type, title=post.title, content=post.content,
        is_pinned=post.is_pinned, username=admin.username,
        like_count=0, comment_count=0, created_at=post.created_at,
    )


@router.put("/posts/{post_id}/pin")
def pin_post(
    post_id: int,
    pinned: bool = Query(...),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """管理员置顶 / 取消置顶帖子。"""
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    post.is_pinned = pinned
    db.commit()
    return {"message": "已置顶" if pinned else "已取消置顶", "is_pinned": post.is_pinned}
