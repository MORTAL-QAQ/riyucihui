"""多模态记忆对照实验路由。

流程：
1. POST /api/experiment/sessions        生成 20 个单词（10 多模态 + 10 非多模态），创建会话
2. POST /api/experiment/words/{id}/image 为多模态组的单词逐张生成配图（前端循环调用，避免长请求超时）
3. GET  /api/experiment/sessions/{id}/quiz  取测试题（日语 → 4 选 1 中文）
4. POST /api/experiment/sessions/{id}/test  提交作答，统计两组正确率
5. GET  /api/experiment/sessions/{id}       会话详情与结果

语音不预生成：学习阶段点击播放时由前端调用 /api/voice 即时合成。
"""
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import ExperimentSession, ExperimentWord, User
from ..services.ai_service import generate_words
from ..services.image_service import generate_word_image
from ..services.rate_limiter import rate_limit

router = APIRouter(prefix="/api/experiment", tags=["experiment"])

# 实验生成成本较高（20 词 + 10 图），做 IP 级限流
EXP_CREATE_LIMIT = rate_limit(max_requests=5, window_seconds=3600)   # 每 IP 每小时 5 次
EXP_IMAGE_LIMIT = rate_limit(max_requests=60, window_seconds=3600)   # 每 IP 每小时 60 张

TOTAL_WORDS = 20
MULTIMODAL_COUNT = 10

# 随机领域池（用户不指定领域时随机选一个）
RANDOM_TOPICS = [
    "日常生活", "食物料理", "旅行观光", "学校学习", "工作职场",
    "天气自然", "交通出行", "购物消费", "健康医疗", "兴趣爱好",
    "家庭生活", "情感表达", "体育运动", "科技互联网", "动物植物",
]

MULTIMODAL_STYLES = [
    {
        "label": "图片 + 语音 + 例句",
        "has_image": True,
        "has_audio": True,
        "has_example": True,
    },
    {
        "label": "仅单词 + 假名",
        "has_image": False,
        "has_audio": False,
        "has_example": False,
    },
]


class SessionCreate(BaseModel):
    topic: str = Field("", max_length=100)      # 空 = 随机领域
    level: str | None = Field(None, pattern=r"^N[1-5]$")


class AnswerItem(BaseModel):
    word_id: int
    choice: str = Field(..., max_length=200)


class TestSubmit(BaseModel):
    answers: list[AnswerItem]


def _word_out(w: ExperimentWord, *, learning: bool = True) -> dict:
    """单词输出。学习阶段：多模态组带图/例句，非多模态组仅单词+假名（均不给中文释义）。"""
    base = {
        "id": w.id,
        "is_multimodal": bool(w.is_multimodal),
        "japanese": w.japanese,
        "kana": w.kana,
    }
    if learning:
        if w.is_multimodal:
            base.update({
                "example_ja": w.example_ja or "",
                "example_cn": w.example_cn or "",
                "image_base64": w.image_base64 or "",
            })
    else:
        # 测试/结果阶段返回中文（用于判分与回看）
        base["chinese"] = w.chinese
    return base


@router.post("/sessions", status_code=201)
def create_session(
    req: SessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate: None = Depends(EXP_CREATE_LIMIT),
):
    """生成 20 个实验单词（10 多模态 + 10 非多模态），创建实验会话。"""
    topic = (req.topic or "").strip()
    if not topic:
        topic = random.choice(RANDOM_TOPICS)

    try:
        words, _tokens = generate_words(topic, req.level, None, TOTAL_WORDS, None)
    except Exception as exc:  # AI 生成失败
        raise HTTPException(status_code=502, detail=f"生成实验材料失败：{exc}")

    if not words or len(words) < TOTAL_WORDS:
        raise HTTPException(status_code=502, detail="生成单词数量不足，请重试")

    words = words[:TOTAL_WORDS]
    # 打乱后再标记组别：避免「前 10 个必有图」的顺序偏差影响学习顺序
    random.shuffle(words)

    session = ExperimentSession(user_id=user.id, topic=topic, status="learning")
    db.add(session)
    db.flush()

    items = []
    for i, w in enumerate(words):
        is_mm = i < MULTIMODAL_COUNT
        row = ExperimentWord(
            session_id=session.id,
            is_multimodal=is_mm,
            japanese=str(w.get("japanese", ""))[:100],
            kana=str(w.get("kana", ""))[:200],
            chinese=str(w.get("chinese", ""))[:200],
            example_ja=(str(w.get("example_ja", ""))[:500] if is_mm else None),
            example_cn=(str(w.get("example_cn", ""))[:500] if is_mm else None),
        )
        db.add(row)
        items.append(row)

    db.commit()
    for row in items:
        db.refresh(row)

    # 学习顺序也打乱（组别仅用于统计，界面不提示）
    learning = [_word_out(w) for w in items]
    random.shuffle(learning)

    return {
        "session_id": session.id,
        "topic": topic,
        "total": TOTAL_WORDS,
        "multimodal_count": MULTIMODAL_COUNT,
        "plain_count": TOTAL_WORDS - MULTIMODAL_COUNT,
        "words": learning,
    }


@router.post("/words/{word_id}/image")
def generate_image(
    word_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate: None = Depends(EXP_IMAGE_LIMIT),
):
    """为多模态组的实验单词生成配图（前端逐张调用，展示进度）。"""
    row = db.get(ExperimentWord, word_id)
    if not row:
        raise HTTPException(status_code=404, detail="单词不存在")
    session = db.get(ExperimentSession, row.session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该实验")
    if not row.is_multimodal:
        return {"word_id": word_id, "image_base64": ""}   # 非多模态组不配图
    if row.image_base64:
        return {"word_id": word_id, "image_base64": row.image_base64}   # 已生成，复用

    try:
        img = generate_word_image(row.japanese, row.chinese, row.kana,
                                  row.example_ja or "", row.example_cn or "")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"配图生成失败：{exc}")

    if img:
        row.image_base64 = img
        db.commit()
    return {"word_id": word_id, "image_base64": img or ""}


@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """会话详情（学习阶段数据 + 已完成时的结果）。"""
    session = db.get(ExperimentSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="实验不存在")

    rows = db.execute(
        select(ExperimentWord).where(ExperimentWord.session_id == session_id)
        .order_by(ExperimentWord.id)
    ).scalars().all()

    done = session.status == "done"
    return {
        "session_id": session.id,
        "topic": session.topic,
        "status": session.status,
        "created_at": session.created_at,
        "multimodal_total": session.multimodal_total,
        "multimodal_correct": session.multimodal_correct,
        "plain_total": session.plain_total,
        "plain_correct": session.plain_correct,
        "words": [_word_out(w, learning=not done) for w in rows],
    }


@router.get("/sessions/{session_id}/quiz")
def get_quiz(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """生成测试题：每题「日语 → 4 个中文选项」，正确项 + 3 个本批干扰项。"""
    session = db.get(ExperimentSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="实验不存在")
    if session.status == "done":
        raise HTTPException(status_code=400, detail="该实验已完成测试")

    rows = db.execute(
        select(ExperimentWord).where(ExperimentWord.session_id == session_id)
    ).scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="实验单词为空")

    all_meanings = [w.chinese for w in rows]
    quiz = []
    for w in rows:
        distractors = [m for m in all_meanings if m != w.chinese]
        random.shuffle(distractors)
        options = [w.chinese] + distractors[:3]
        # 不足 3 个干扰项时（词义重复）补齐占位
        while len(options) < 4:
            options.append("（无）")
        random.shuffle(options)
        quiz.append({
            "word_id": w.id,
            "japanese": w.japanese,
            "kana": w.kana,
            "options": options,
        })
    random.shuffle(quiz)

    session.status = "testing"
    db.commit()
    return {"session_id": session.id, "topic": session.topic, "quiz": quiz}


@router.post("/sessions/{session_id}/test")
def submit_test(
    session_id: int,
    body: TestSubmit,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交作答：判定每题对错，统计多模态组与非多模态组正确率。"""
    session = db.get(ExperimentSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="实验不存在")
    if session.status == "done":
        raise HTTPException(status_code=400, detail="该实验已提交过测试")

    rows = db.execute(
        select(ExperimentWord).where(ExperimentWord.session_id == session_id)
    ).scalars().all()
    by_id = {w.id: w for w in rows}
    if not body.answers:
        raise HTTPException(status_code=400, detail="未提交任何作答")

    now = datetime.now(timezone.utc)
    mm_total = mm_correct = pl_total = pl_correct = 0
    for ans in body.answers:
        w = by_id.get(ans.word_id)
        if not w:
            continue
        correct = (ans.choice.strip() == w.chinese.strip())
        w.test_choice = ans.choice[:200]
        w.test_correct = correct
        w.tested_at = now
        if w.is_multimodal:
            mm_total += 1
            mm_correct += 1 if correct else 0
        else:
            pl_total += 1
            pl_correct += 1 if correct else 0

    session.multimodal_total = mm_total
    session.multimodal_correct = mm_correct
    session.plain_total = pl_total
    session.plain_correct = pl_correct
    session.status = "done"
    session.completed_at = now
    db.commit()

    return _result_payload(session, rows)


@router.get("/my")
def my_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的实验列表（按时间倒序）。"""
    rows = db.execute(
        select(ExperimentSession).where(ExperimentSession.user_id == user.id)
        .order_by(ExperimentSession.created_at.desc()).limit(20)
    ).scalars().all()
    return {
        "sessions": [
            {
                "session_id": s.id,
                "topic": s.topic,
                "status": s.status,
                "created_at": s.created_at,
                "multimodal_correct": s.multimodal_correct,
                "multimodal_total": s.multimodal_total,
                "plain_correct": s.plain_correct,
                "plain_total": s.plain_total,
            }
            for s in rows
        ]
    }


def _result_payload(session: ExperimentSession, rows: list[ExperimentWord]) -> dict:
    def rate(correct: int, total: int) -> float:
        return round(correct / total * 100, 1) if total else 0.0

    return {
        "session_id": session.id,
        "topic": session.topic,
        "status": session.status,
        "multimodal": {
            "correct": session.multimodal_correct,
            "total": session.multimodal_total,
            "rate": rate(session.multimodal_correct, session.multimodal_total),
        },
        "plain": {
            "correct": session.plain_correct,
            "total": session.plain_total,
            "rate": rate(session.plain_correct, session.plain_total),
        },
        "diff": round(
            rate(session.multimodal_correct, session.multimodal_total)
            - rate(session.plain_correct, session.plain_total), 1
        ),
        "details": [
            {
                "word_id": w.id,
                "japanese": w.japanese,
                "kana": w.kana,
                "chinese": w.chinese,
                "is_multimodal": bool(w.is_multimodal),
                "test_choice": w.test_choice,
                "test_correct": w.test_correct,
            }
            for w in rows
        ],
    }
