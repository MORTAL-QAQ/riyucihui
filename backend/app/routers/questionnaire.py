"""问卷路由（科研数据采集）。

用户侧：
1. GET  /api/questionnaires                  问卷列表（含我的提交状态）
2. GET  /api/questionnaires/{code}           取问卷题目定义 + 我的作答（如有）
3. POST /api/questionnaires/{code}           提交作答（校验必答 / 选项范围 / 防重复提交）

管理员侧：
4. GET  /api/admin/questionnaires/stats       各卷提交情况 + 逐人作答与维度分
5. GET  /api/admin/questionnaires/export      CSV 导出（data=作答数据 / dict=题号对照表）

设计要点：题目定义不在数据库里，而是来自 `app/questionnaires.py`（措辞冻结、随代码版本管理）；
提交时把 code / version / 题目快照关键信息一并落库到 questionnaire_responses，
保证日后即使问卷改版，历史数据依然可解释、可复现。
"""
import csv
import io
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import questionnaires as qq
from ..auth import get_admin_user, get_current_user
from ..database import get_db
from ..models import QuestionnaireResponse, User
from ..services.rate_limiter import rate_limit

router = APIRouter(prefix="/api", tags=["questionnaire"])

# 提交接口做 IP 级限流（防止脚本刷科研数据）
SUBMIT_LIMIT = rate_limit(max_requests=30, window_seconds=3600)


class SubmitRequest(BaseModel):
    answers: dict = Field(..., description="条目 key → 作答值")
    duration_sec: int = Field(default=0, ge=0, le=86400)


def _parse_answers(raw: str) -> dict:
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError):
        return {}


def _parse_scores(raw: str) -> dict:
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError):
        return {}


def _questionnaire_out(q: dict, resp: QuestionnaireResponse | None = None) -> dict:
    return {
        "code": q["code"],
        "number": q["number"],
        "name": q["name"],
        "display_name": qq.display_name(q),
        "version": q["version"],
        "audience": q["audience"],
        "timing": q["timing"],
        "minutes": q["minutes"],
        "page_count": len(q["pages"]),
        "item_count": len(qq.item_keys(q)),
        "submitted": resp is not None,
        "submitted_at": resp.submitted_at.isoformat() if resp else None,
        "duration_sec": resp.duration_sec if resp else None,
    }


def _get_responses(db: Session, user_id: int) -> dict:
    rows = db.execute(
        select(QuestionnaireResponse).where(QuestionnaireResponse.user_id == user_id)
    ).scalars().all()
    return {r.code: r for r in rows}


# ────────────────────────── 用户侧 ──────────────────────────

@router.get("/questionnaires")
def list_questionnaires(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """全部问卷 + 我的提交状态（前端据此显示「未填写 / 已完成」）。"""
    mine = _get_responses(db, user.id)
    return {
        "questionnaires": [_questionnaire_out(q, mine.get(q["code"])) for q in qq.list_questionnaires()],
        "submitted_count": sum(1 for q in qq.list_questionnaires() if q["code"] in mine),
        "total": len(qq.QUESTIONNAIRES),
    }


@router.get("/questionnaires/{code}")
def get_questionnaire(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """取问卷题目定义；已提交过则附带我的作答（前端展示为只读回顾）。"""
    q = qq.get_questionnaire(code)
    if not q:
        raise HTTPException(status_code=404, detail="问卷不存在")

    resp = db.execute(
        select(QuestionnaireResponse).where(
            QuestionnaireResponse.user_id == user.id,
            QuestionnaireResponse.code == code,
        )
    ).scalars().first()

    return {
        "questionnaire": {
            "code": q["code"],
            "number": q["number"],
            "name": q["name"],
            "display_name": qq.display_name(q),
            "version": q["version"],
            "audience": q["audience"],
            "timing": q["timing"],
            "minutes": q["minutes"],
            "intro": q["intro"],
            "outro": q["outro"],
            "pages": q["pages"],
        },
        "submitted": resp is not None,
        "submitted_at": resp.submitted_at.isoformat() if resp else None,
        "duration_sec": resp.duration_sec if resp else None,
        "my_answers": _parse_answers(resp.answers) if resp else {},
    }


@router.post("/questionnaires/{code}")
def submit_questionnaire(
    code: str,
    req: SubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(SUBMIT_LIMIT),
):
    """提交问卷作答（服务端校验必答与选项范围，同一问卷只允许提交一次）。"""
    q = qq.get_questionnaire(code)
    if not q:
        raise HTTPException(status_code=404, detail="问卷不存在")

    exists = db.execute(
        select(QuestionnaireResponse).where(
            QuestionnaireResponse.user_id == user.id,
            QuestionnaireResponse.code == code,
        )
    ).scalars().first()
    if exists:
        raise HTTPException(status_code=409, detail="该问卷你已提交过，无需重复提交")

    answers = req.answers or {}
    options = qq.choice_options(q)

    # 1) 必答校验
    missing = [k for k in qq.required_keys(q) if answers.get(k) in (None, "")]
    if missing:
        labels = qq.item_labels(q)
        first = labels.get(missing[0], missing[0])
        raise HTTPException(
            status_code=400,
            detail=f"还有 {len(missing)} 题未作答：{first}",
        )

    # 2) 选项范围校验（矩阵行与单选）
    labels = qq.item_labels(q)
    for key, value in answers.items():
        allowed = options.get(key)
        if allowed is not None and str(value) not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"题目「{labels.get(key, key)}」的作答值不合法",
            )

    # 3) 只保留本卷定义的条目（防止前端夹带无关字段）
    valid_keys = set(qq.item_keys(q))
    clean = {k: v for k, v in answers.items() if k in valid_keys}

    scores = qq.compute_scores(q, clean)
    row = QuestionnaireResponse(
        user_id=user.id,
        code=q["code"],
        number=q["number"],
        name=q["name"],
        version=q["version"],
        answers=json.dumps(clean, ensure_ascii=False),
        scores=json.dumps(scores, ensure_ascii=False),
        duration_sec=req.duration_sec or 0,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(row)
    try:
        db.commit()
    except Exception:
        db.rollback()
        # 并发重复提交由唯一约束兜底
        raise HTTPException(status_code=409, detail="该问卷你已提交过，无需重复提交")
    db.refresh(row)

    return {
        "message": "问卷提交成功，感谢参与！",
        "code": row.code,
        "submitted_at": row.submitted_at.isoformat(),
        "duration_sec": row.duration_sec,
    }


@router.get("/questionnaires/my/history")
def my_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """我的问卷提交记录（按卷号排序）。"""
    rows = db.execute(
        select(QuestionnaireResponse)
        .where(QuestionnaireResponse.user_id == user.id)
        .order_by(QuestionnaireResponse.number, QuestionnaireResponse.code)
    ).scalars().all()
    return {
        "items": [
            {
                "code": r.code,
                "number": r.number,
                "name": r.name,
                "display_name": f"卷{r.number} {r.name}",
                "version": r.version,
                "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
                "duration_sec": r.duration_sec,
                "scores": _parse_scores(r.scores),
            }
            for r in rows
        ]
    }


# ────────────────────────── 管理员侧 ──────────────────────────

@router.get("/admin/questionnaires/stats")
def admin_stats(
    code: str | None = Query(default=None, description="只看某一份问卷"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """各卷提交情况汇总 + 逐人作答明细（含维度分）。"""
    # 统计口径：以普通用户（非管理员）为分母
    total_users = db.execute(select(User).where(User.is_admin == False)).scalars().all()
    total_count = len(total_users)

    forms = [q for q in qq.list_questionnaires() if (code is None or q["code"] == code)]
    if code and not forms:
        raise HTTPException(status_code=404, detail="问卷不存在")

    rows = db.execute(select(QuestionnaireResponse)).scalars().all()
    by_user = {u.id: u for u in total_users}
    # 管理员账号也可能作答，一并纳入展示
    all_users = {u.id: u for u in db.execute(select(User)).scalars().all()}

    summary = []
    responses_by_code = {}
    for q in forms:
        items = [r for r in rows if r.code == q["code"]]
        items.sort(key=lambda r: r.submitted_at or datetime.min)
        responses_by_code[q["code"]] = items
        durations = [r.duration_sec for r in items if r.duration_sec]
        summary.append({
            "code": q["code"],
            "display_name": qq.display_name(q),
            "number": q["number"],
            "name": q["name"],
            "audience": q["audience"],
            "timing": q["timing"],
            "item_count": len(qq.item_keys(q)),
            "submitted": len(items),
            "total_users": total_count,
            "rate": round(len(items) * 100 / total_count, 1) if total_count else 0.0,
            "avg_duration_min": round(sum(durations) / len(durations) / 60, 1) if durations else 0.0,
        })

    detail = {}
    for c, items in responses_by_code.items():
        detail[c] = [
            {
                "user_id": r.user_id,
                "username": all_users[r.user_id].username if r.user_id in all_users else "（已删除）",
                "name": (all_users[r.user_id].name if r.user_id in all_users else "") or "",
                "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
                "duration_sec": r.duration_sec,
                "answers": _parse_answers(r.answers),
                "scores": _parse_scores(r.scores),
            }
            for r in items
        ]

    return {
        "summary": summary,
        "detail": detail,
        "labels": {q["code"]: qq.item_labels(q) for q in forms},
        "dimensions": {q["code"]: list((q.get("dimensions") or {}).keys()) for q in forms},
    }


@router.get("/admin/questionnaires/export")
def admin_export(
    code: str = Query(..., description="问卷 code"),
    kind: str = Query(default="data", pattern="^(data|dict)$"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """CSV 导出：kind=data 作答数据（一人一行，可直接进 SPSS/Excel）；kind=dict 题号对照表。"""
    q = qq.get_questionnaire(code)
    if not q:
        raise HTTPException(status_code=404, detail="问卷不存在")

    labels = qq.item_labels(q)
    dims = list((q.get("dimensions") or {}).keys())
    buf = io.StringIO()
    writer = csv.writer(buf)

    if kind == "dict":
        writer.writerow(["条目key", "题号/维度", "题干", "反向计分"])
        reverse = set(q.get("reverse") or [])
        owner = {}
        for dim, keys in (q.get("dimensions") or {}).items():
            for k in keys:
                owner.setdefault(k, dim)
        for page_idx, page in enumerate(q["pages"], 1):
            for item in page["items"]:
                if item["type"] == "matrix":
                    for i, row in enumerate(item["rows"], 1):
                        key = f"{item['key']}_r{i}"
                        writer.writerow([key, f"第{page_idx}页 第{i}行", row,
                                         "是" if key in reverse else ""])
                else:
                    writer.writerow([item["key"], f"第{page_idx}页", item["text"],
                                     "是" if item["key"] in reverse else ""])
        writer.writerow([])
        writer.writerow(["维度", "包含条目"])
        for dim, keys in (q.get("dimensions") or {}).items():
            writer.writerow([dim, "、".join(keys)])
        filename = f"问卷{q['number']}_{q['name']}_题号对照表.csv"
    else:
        rows = db.execute(
            select(QuestionnaireResponse).where(QuestionnaireResponse.code == code)
        ).scalars().all()
        rows.sort(key=lambda r: r.submitted_at or datetime.min)
        users = {u.id: u for u in db.execute(select(User)).scalars().all()}

        header = ["用户ID", "账号", "昵称", "问卷", "问卷版本", "提交时间", "用时(秒)"]
        header += [f"维度分_{d}" for d in dims]
        header += qq.item_keys(q)
        writer.writerow(header)

        for r in rows:
            u = users.get(r.user_id)
            answers = _parse_answers(r.answers)
            scores = _parse_scores(r.scores)
            line = [
                r.user_id,
                u.username if u else "",
                (u.name if u else "") or "",
                f"卷{r.number} {r.name}",
                r.version,
                _cst_str(r.submitted_at),
                r.duration_sec or 0,
            ]
            line += [scores.get(d, "") for d in dims]
            line += [answers.get(k, "") for k in qq.item_keys(q)]
            writer.writerow(line)
        filename = f"问卷{q['number']}_{q['name']}_作答数据.csv"

    # BOM 让 Excel 正确识别 UTF-8
    body = "\ufeff" + buf.getvalue()
    disposition = f"attachment; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=body.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": disposition},
    )


def _cst_str(dt: datetime | None) -> str:
    """提交时间按北京时间展示。

    生产 PostgreSQL 存的字面值已是容器本地时间（CST），不能再加 8 小时；
    只有带时区的时间才需要转换——与 admin_api._to_cst 的口径保持一致。
    """
    if dt is None:
        return ""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone(timedelta(hours=8)))
    return dt.strftime("%Y-%m-%d %H:%M:%S")
