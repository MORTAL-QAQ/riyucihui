"""统一导出路由 — 批量导出多种内容到一个 PDF。

POST /api/export/pdf — 批量导出（words + essays + clozes + grammar + study report）
"""

import json
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from reportlab.lib import colors as rl_colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table as Tbl, TableStyle as TS
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Cloze, Essay, GrammarCompare, StudyRecord, User, Word
from ..schemas import BatchExportRequest
from ..services.pdf_service import (
    _build_styles,
    _encode_filename,
    _header_footer,
    _jp_font_name,
    generate_words_pdf,
)
from ..services import word_service

router = APIRouter(prefix="/api", tags=["export"])


@router.post("/export/pdf")
def batch_export_pdf(
    req: BatchExportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量导出多种内容到一个 PDF 文件。

    请求体示例:
    {
      "words": {"topic": "食物", "layout": "table", "include_images": true},
      "essays": [1, 2],
      "clozes": [3],
      "grammar_compares": [4],
      "study_report": true
    }
    """
    font_name = _jp_font_name()
    styles = _build_styles(font_name)
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm + 8,
        bottomMargin=20 * mm + 16,
        title="学习资料导出",
        author="多模态日语词汇学习",
        creator="多模态日语词汇学习 PDF Export",
    )

    elements: list = []
    sections_added = 0

    # ── Words ──
    if req.words:
        topic = req.words.get("topic")
        layout = req.words.get("layout", "table")
        include_images = req.words.get("include_images", True)
        ids = req.words.get("ids")

        if ids:
            words = db.query(Word).filter(
                Word.user_id == user.id,
                Word.id.in_(ids),
            ).all()
            total = len(words)
            topic_name = "自选单词"
        else:
            words, total = word_service.get_words(db, user.id, topic, None, 0, 10000)
            topic_name = topic or "全部词单"

        if words:
            elements.append(Paragraph(f"词单 — {topic_name}", styles["title"]))
            elements.append(Spacer(1, 8))
            word_buf = generate_words_pdf(
                words, topic_name, total, layout=layout, include_images=include_images
            )
            # Note: full word table rendering in batch mode requires refactoring
            # generate_words_pdf to return flowables. For now, show a summary.
            elements.append(Paragraph(
                f"共 {total} 个单词（请使用单独的单词导出功能查看完整表格）",
                styles["body"],
            ))
            sections_added += 1

    # ── Essays ──
    if req.essays:
        essays = db.query(Essay).filter(
            Essay.user_id == user.id,
            Essay.id.in_(req.essays),
        ).all()
        for essay in essays:
            if sections_added > 0:
                elements.append(PageBreak())
            elements.append(Paragraph(f"短文 — {essay.title}", styles["title"]))
            elements.append(Spacer(1, 8))
            # Inline essay rendering using same logic as generate_essay_pdf
            if essay.jlpt_level:
                jlpt_color = {"N1": "#ef4444", "N2": "#f97316", "N3": "#6366f1",
                              "N4": "#22c55e", "N5": "#9ca3af"}.get(essay.jlpt_level, "#9ca3af")
                elements.append(Paragraph(
                    f'<font color="{jlpt_color}"><b>{essay.jlpt_level}</b></font>',
                    styles["small"],
                ))
                elements.append(Spacer(1, 4))
            content = essay.content.replace("【", '<font color="#6366f1"><b>【') \
                                   .replace("】", '】</b></font>')
            elements.append(Paragraph(content, styles["body_large"]))
            elements.append(Spacer(1, 8))
            elements.append(Paragraph("中文翻译", styles["heading"]))
            elements.append(Paragraph(essay.chinese_translation, styles["body"]))
            sections_added += 1

    # ── Clozes ──
    if req.clozes:
        clozes = db.query(Cloze).filter(
            Cloze.user_id == user.id,
            Cloze.id.in_(req.clozes),
        ).all()
        for cloze in clozes:
            if sections_added > 0:
                elements.append(PageBreak())
            blanks = json.loads(cloze.blanks) if isinstance(cloze.blanks, str) else cloze.blanks

            elements.append(Paragraph(f"完型填空 — {cloze.title}", styles["title"]))
            if cloze.jlpt_level:
                jlpt_color = {"N1": "#ef4444", "N2": "#f97316", "N3": "#6366f1",
                              "N4": "#22c55e", "N5": "#9ca3af"}.get(cloze.jlpt_level, "#9ca3af")
                elements.append(Paragraph(
                    f'<font color="{jlpt_color}"><b>{cloze.jlpt_level}</b></font>',
                    styles["small"],
                ))
                elements.append(Spacer(1, 4))
            passage_text = cloze.passage.replace("____", " ________ ")
            elements.append(Paragraph(passage_text, styles["body_large"]))
            elements.append(Spacer(1, 8))
            elements.append(Paragraph("答案", styles["heading"]))
            answer_parts = [f"{b['answer']}({b['kana']})" for b in blanks]
            elements.append(Paragraph(" / ".join(answer_parts), styles["body"]))
            if cloze.chinese_translation:
                elements.append(Spacer(1, 6))
                elements.append(Paragraph("中文翻译", styles["heading"]))
                elements.append(Paragraph(cloze.chinese_translation, styles["body"]))
            sections_added += 1

    # ── Grammar Compares ──
    if req.grammar_compares:
        compares = db.query(GrammarCompare).filter(
            GrammarCompare.user_id == user.id,
            GrammarCompare.id.in_(req.grammar_compares),
        ).all()
        for gc in compares:
            if sections_added > 0:
                elements.append(PageBreak())
            result = json.loads(gc.result) if isinstance(gc.result, str) else gc.result

            elements.append(Paragraph(f"语法辨析 — {gc.topic}", styles["title"]))
            elements.append(Spacer(1, 8))
            if result.get("summary"):
                elements.append(Paragraph(result["summary"], styles["body"]))
                elements.append(Spacer(1, 8))

            rows = result.get("rows", [])
            if rows:
                table_data = [["语法点", "接续", "含义", "例句"]]
                for r in rows:
                    table_data.append([
                        r.get("grammar", ""),
                        r.get("pattern", ""),
                        r.get("meaning", ""),
                        r.get("example", ""),
                    ])
                tbl = Tbl(table_data, colWidths=[80, 80, 80, 220])
                tbl.setStyle(TS([
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
                    ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#6366f1")),
                    ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.HexColor("#d1d5db")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor("#f9fafb")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]))
                elements.append(tbl)
            sections_added += 1

    # ── Study Report summary ──
    if req.study_report:
        from datetime import date
        today = date.today()

        if sections_added > 0:
            elements.append(PageBreak())

        elements.append(Paragraph("学习报告摘要", styles["title"]))
        elements.append(Spacer(1, 8))

        total_learned = db.query(StudyRecord).filter(StudyRecord.user_id == user.id).count()
        total_words = db.query(Word).filter(Word.user_id == user.id).count()
        mastered = db.query(StudyRecord).filter(
            StudyRecord.user_id == user.id, StudyRecord.stage >= 5
        ).count()
        due_review = db.query(StudyRecord).filter(
            StudyRecord.user_id == user.id,
            StudyRecord.next_review_date <= today,
            StudyRecord.stage < 7,
        ).count()

        stats_text = (
            f"总词库: {total_words} 词 | 已学习: {total_learned} 词 | "
            f"掌握中: {mastered} 词 | 待复习: {due_review} 词"
        )
        elements.append(Paragraph(stats_text, styles["body"]))
        sections_added += 1

    if sections_added == 0:
        raise HTTPException(status_code=400, detail="请至少选择一项内容导出")

    elements.append(Spacer(1, 20))
    now = datetime.now()
    elements.append(Paragraph(
        f"导出时间: {now.strftime('%Y-%m-%d %H:%M')}",
        styles["footer"],
    ))

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, "学习资料"),
               onLaterPages=lambda c, d: _header_footer(c, d, "学习资料"))
    buf.seek(0)

    filename = f"学习资料_{now.strftime('%Y%m%d')}.pdf"
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*={_encode_filename(filename)}",
        },
    )
