"""PDF export service for the Japanese vocabulary learning app.

Provides functions to generate PDF documents using ReportLab.
All functions return BytesIO buffers ready for HTTP response.

Design:
- All text uses the Japanese font registered by font_manager.py.
- Styles and table formatting are centralized for visual consistency.
- Each generate_*_pdf function is self-contained and returns a BytesIO.
"""

import html
from datetime import date, datetime
from io import BytesIO
from urllib.parse import quote

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Constants ────────────────────────────────────────────────────────────────

_MARGIN = 20 * mm

# Brand color (indigo/purple tone matching the frontend)
_BRAND = colors.HexColor("#6366f1")
_TEXT_MAIN = colors.HexColor("#1f2937")
_TEXT_SECONDARY = colors.HexColor("#6b7280")
_TEXT_MUTED = colors.HexColor("#9ca3af")
_BORDER = colors.HexColor("#d1d5db")
_STRIPE = colors.HexColor("#f9fafb")

# JLPT level color badges
_JLPT_COLORS: dict[str, str] = {
    "N1": "#ef4444",
    "N2": "#f97316",
    "N3": "#6366f1",
    "N4": "#22c55e",
    "N5": "#9ca3af",
}


def jlpt_color(level: str | None) -> str:
    """返回 JLPT 等级对应的徽章颜色（#42：集中定义，避免多处内联字典重复）。"""
    return _JLPT_COLORS.get(level or "", "#9ca3af")


def generate_study_report_pdf(db, user_id: int) -> BytesIO:
    """生成学习进度报告 PDF（#43：从 routers/study.py 下沉，集中 PDF 渲染逻辑）。

    包含：学习统计概览、SM-2 阶段分布、待复习单词列表。
    """
    from sqlalchemy import func

    from ..models import StudyRecord, Word

    font_name = _jp_font_name()
    styles = _build_styles(font_name)
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=_MARGIN,
        leftMargin=_MARGIN,
        topMargin=_MARGIN + 8,
        bottomMargin=_MARGIN + 16,
        title="学习报告",
        author="多模态日语词汇学习",
        creator="多模态日语词汇学习 PDF Export",
    )

    today = date.today()
    elements: list = []

    # ── Title ──
    elements.append(Paragraph("多模态日语词汇学习 — 学习报告", styles["title"]))
    elements.append(Spacer(1, 12))

    # ── Stats ──
    total_learned = db.query(func.count(StudyRecord.id)).filter(
        StudyRecord.user_id == user_id
    ).scalar() or 0

    total_words = db.query(func.count(Word.id)).filter(
        Word.user_id == user_id
    ).scalar() or 0

    mastered = db.query(func.count(StudyRecord.id)).filter(
        StudyRecord.user_id == user_id,
        StudyRecord.stage >= 5,
    ).scalar() or 0

    due_review = db.query(func.count(StudyRecord.id)).filter(
        StudyRecord.user_id == user_id,
        StudyRecord.next_review_date <= today,
        StudyRecord.stage < 7,
    ).scalar() or 0

    today_reviewed = db.query(func.count(StudyRecord.id)).filter(
        StudyRecord.user_id == user_id,
        StudyRecord.last_review_date == today,
    ).scalar() or 0

    stats_data = [
        ["总词库", "已学习", "掌握中", "待复习", "今日已复习"],
        [str(total_words), str(total_learned), str(mastered), str(due_review), str(today_reviewed)],
    ]
    stats_tbl = Table(stats_data, colWidths=[90, 90, 90, 90, 100])
    stats_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), _BRAND),
        ("BACKGROUND", (0, 1), (-1, 1), _STRIPE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(stats_tbl)
    elements.append(Spacer(1, 20))

    # ── SM-2 Stage distribution ──
    elements.append(Paragraph("SM-2 阶段分布", styles["heading"]))
    stage_counts = db.execute(
        db.query(StudyRecord.stage, func.count(StudyRecord.id))
        .filter(StudyRecord.user_id == user_id)
        .group_by(StudyRecord.stage)
        .order_by(StudyRecord.stage)
    ).all()
    stage_map = {s: c for s, c in stage_counts}

    stage_labels = ["阶段0\n(新卡)", "阶段1\n(1天)", "阶段2\n(2-3天)", "阶段3\n(4-7天)",
                    "阶段4\n(8-21天)", "阶段5\n(22-60天)", "阶段6\n(61-180天)", "阶段7\n(已掌握)"]
    stage_data = [["阶段", "数量", "进度"]]
    max_count = max(stage_map.values()) if stage_map else 1
    for s in range(8):
        cnt = stage_map.get(s, 0)
        bar = "█" * max(1, int(cnt / max(max_count, 1) * 20))
        stage_data.append([stage_labels[s], str(cnt), bar])

    stage_tbl = Table(stage_data, colWidths=[120, 60, 280])
    stage_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), _BRAND),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _STRIPE]),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(stage_tbl)
    elements.append(Spacer(1, 20))

    # ── Due review word list ──
    if due_review > 0:
        elements.append(Paragraph(f"待复习单词（共 {due_review} 个）", styles["heading"]))
        due_words = (
            db.query(Word, StudyRecord)
            .join(StudyRecord, Word.id == StudyRecord.word_id)
            .filter(
                StudyRecord.user_id == user_id,
                StudyRecord.next_review_date <= today,
                StudyRecord.stage < 7,
            )
            .order_by(StudyRecord.stage, StudyRecord.next_review_date)
            .limit(50)
            .all()
        )
        dw_header = ["序号", "日语", "假名", "中文", "阶段", "间隔(天)"]
        dw_data = [dw_header]
        for i, (w, sr) in enumerate(due_words):
            dw_data.append([
                str(i + 1), _esc(w.japanese), _esc(w.kana), _esc(w.chinese),
                str(sr.stage), str(sr.interval or 0),
            ])
        dw_tbl = Table(dw_data, colWidths=[30, 72, 72, 72, 36, 48])
        dw_tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 0), (-1, 0), _BRAND),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _STRIPE]),
            ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(dw_tbl)

    elements.append(Spacer(1, 20))
    now_dt = datetime.now()
    elements.append(Paragraph(
        f"报告生成时间: {now_dt.strftime('%Y-%m-%d %H:%M')}",
        styles["footer"],
    ))

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, "学习报告"),
               onLaterPages=lambda c, d: _header_footer(c, d, "学习报告"))
    buf.seek(0)
    return buf


# ── Helpers ──────────────────────────────────────────────────────────────────


def _jp_font_name() -> str:
    """Lazy-import and return the registered Japanese font name."""
    from .font_manager import get_font_name

    return get_font_name()


def _esc(s) -> str:
    """转义用户内容，防止 ReportLab 段落标记注入（#9）。"""
    return html.escape(str(s), quote=True)


def _build_styles(font_name: str, base_size: int = 9) -> dict[str, ParagraphStyle]:
    """Build a consistent set of ParagraphStyle objects for PDF export."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "JPTitle",
            parent=base["Title"],
            fontName=font_name,
            fontSize=18,
            leading=24,
            spaceAfter=12,
            textColor=_BRAND,
        ),
        "heading": ParagraphStyle(
            "JPHeading",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=14,
            leading=20,
            spaceBefore=12,
            spaceAfter=8,
            textColor=_TEXT_MAIN,
        ),
        "body": ParagraphStyle(
            "JPBody",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=base_size,
            leading=base_size * 1.6,
            textColor=_TEXT_MAIN,
        ),
        "body_large": ParagraphStyle(
            "JPBodyLarge",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=12,
            leading=18,
            textColor=_TEXT_MAIN,
        ),
        "small": ParagraphStyle(
            "JPSmall",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=8,
            leading=12,
            textColor=_TEXT_SECONDARY,
        ),
        "footer": ParagraphStyle(
            "JPFooter",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=7,
            leading=10,
            textColor=_TEXT_MUTED,
        ),
        "card_jp": ParagraphStyle(
            "JPCardJP",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=14,
            leading=20,
            textColor=_TEXT_MAIN,
        ),
        "card_cn": ParagraphStyle(
            "JPCardCN",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=10,
            leading=14,
            textColor=_TEXT_SECONDARY,
        ),
    }


def _default_table_style(font_name: str) -> TableStyle:
    """Return the default alternating-row table style."""
    return TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), _BRAND),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _STRIPE]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ])


def _encode_filename(filename: str) -> str:
    """RFC 5987 filename encoding for Content-Disposition header."""
    return f"UTF-8''{quote(filename)}"


def _header_footer(canvas, doc, title: str):
    """Draw page header and footer on every page."""
    font_name = _jp_font_name()
    page_width, page_height = A4

    canvas.saveState()
    canvas.setFont(font_name, 7)
    canvas.setFillColor(_TEXT_MUTED)

    # Header
    canvas.drawString(
        doc.leftMargin, page_height - doc.topMargin + 4,
        f"多模态日语词汇学习 — {title}",
    )
    canvas.drawRightString(
        page_width - doc.rightMargin, page_height - doc.topMargin + 4,
        f"第 {canvas.getPageNumber()} 页",
    )

    # Footer separator line
    canvas.setStrokeColor(_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(
        doc.leftMargin, doc.bottomMargin - 6,
        page_width - doc.rightMargin, doc.bottomMargin - 6,
    )

    # Footer text
    canvas.drawString(
        doc.leftMargin, doc.bottomMargin - 16,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    canvas.drawRightString(
        page_width - doc.rightMargin, doc.bottomMargin - 16,
        "多模态日语词汇学习",
    )
    canvas.restoreState()


# ── Word PDF export ──────────────────────────────────────────────────────────


def generate_words_pdf(
    words,
    topic_name: str,
    total: int,
    *,
    layout: str = "table",
) -> BytesIO:
    """Generate a PDF of vocabulary words.

    Args:
        words: List of Word ORM objects.
        topic_name: Display name for the topic (e.g. "食物").
        total: Total word count (for footer).
        layout: "table" for a compact data table, "card" for 2-column cards.

    Returns:
        BytesIO buffer containing the completed PDF.
    """
    font_name = _jp_font_name()
    styles = _build_styles(font_name)
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=_MARGIN,
        leftMargin=_MARGIN,
        topMargin=_MARGIN + 8,  # extra space for header
        bottomMargin=_MARGIN + 16,  # extra space for footer
        title=f"词单 - {topic_name}",
        author="多模态日语词汇学习",
        creator="多模态日语词汇学习 PDF Export",
    )

    elements: list = []
    elements.append(Paragraph(f"多模态日语词汇学习 — {_esc(topic_name)}", styles["title"]))
    elements.append(Spacer(1, 10))

    if layout == "card":
        elements.extend(_build_word_cards(words, font_name, styles))
    else:
        elements.extend(_build_word_table(words, font_name))

    elements.append(Spacer(1, 20))
    now = datetime.now()
    elements.append(
        Paragraph(
            f"共 {total} 个单词 · 导出时间: {now.strftime('%Y-%m-%d %H:%M')}",
            styles["footer"],
        )
    )

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, topic_name),
               onLaterPages=lambda c, d: _header_footer(c, d, topic_name))
    buf.seek(0)
    return buf


def _build_word_table(words, font_name: str) -> list:
    """Build table-mode elements for word export."""
    header = ["序号", "日语", "假名", "中文", "N", "例句"]
    data = [header]
    for i, w in enumerate(words):
        example = (w.example_ja or "")[:60]
        example += "..." if len(w.example_ja or "") > 60 else ""
        data.append([
            str(i + 1),
            w.japanese or "",
            w.kana or "",
            w.chinese or "",
            w.jlpt_level or "",
            example,
        ])

    col_widths = [28, 68, 68, 60, 22, 222]  # 合计 468pt < 可用宽度 481pt（A4 - 2×56.7mm 边距）
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(_default_table_style(font_name))
    return [tbl]


def _build_word_cards(words, font_name: str, styles: dict) -> list:
    """Build card-mode elements for word export (2-column grid)."""
    elements: list = []
    # Build rows of 2 cards each
    row_data: list[list] = []
    for i in range(0, len(words), 2):
        left = _word_card(words[i], font_name, styles) if i < len(words) else _empty_card()
        right = _word_card(words[i + 1], font_name, styles) if i + 1 < len(words) else _empty_card()
        row_data.append([left, right])

    tbl = Table(row_data, colWidths=[card_width(), card_width()])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
    ]))
    elements.append(tbl)
    return elements


def _empty_card() -> Table:
    """占位卡片：外层表格单元格需要单一 flowable，空卡片用单行空表格填充。"""
    empty = Table([[""]], colWidths=[10])
    empty.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return empty


def _word_card(w, font_name: str, styles: dict) -> Table:
    """Build a single word card as a nested single-column table.

    用嵌套表格而非 flowable 列表：ReportLab 表格单元格直接放多个 flowable，
    在跨页分页时是已知的重叠 bug 来源（内容堆叠）。嵌套表格保证单元格内
    是单一 flowable，行高与分页计算正确。
    """
    rows: list[list] = []

    # Japanese + kana
    jp_text = f"<b>{_esc(w.japanese)}</b>"
    if w.kana:
        jp_text += f'  <font size="8" color="#6b7280">{_esc(w.kana)}</font>'
    rows.append([Paragraph(jp_text, styles["card_jp"])])

    # Chinese meaning
    rows.append([Paragraph(_esc(w.chinese), styles["card_cn"])])

    # JLPT badge
    if w.jlpt_level:
        rows.append([Paragraph(
            f'<font color="{jlpt_color(w.jlpt_level)}" size="8"><b>{_esc(w.jlpt_level)}</b></font>',
            styles["small"],
        )])

    # Example
    if w.example_ja:
        ex_text = _esc(w.example_ja[:80])
        if len(w.example_ja or "") > 80:
            ex_text += "..."
        rows.append([Paragraph(
            f'<font size="7">{ex_text}</font>',
            styles["small"],
        )])

    card = Table(rows, colWidths=[card_width()])
    card.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return card


def card_width() -> float:
    """外层两列卡片宽度（供嵌套卡片使用，保持一致的可用宽度）。"""
    return (A4[0] - _MARGIN * 2) / 2 - 4


# ── Essay / Cloze / Grammar PDF export (Phase 3 placeholders) ────────────────
# These will be fully implemented in Phase 3.


def generate_essay_pdf(essay) -> BytesIO:
    """Generate a PDF for an AI-generated essay."""
    font_name = _jp_font_name()
    styles = _build_styles(font_name)
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=_MARGIN,
        leftMargin=_MARGIN,
        topMargin=_MARGIN + 8,
        bottomMargin=_MARGIN + 16,
        title=essay.title,
        author="多模态日语词汇学习",
    )

    elements: list = []
    elements.append(Paragraph(_esc(essay.title), styles["title"]))
    if essay.jlpt_level:
        elements.append(Paragraph(
            f'<font color="{jlpt_color(essay.jlpt_level)}"><b>{_esc(essay.jlpt_level)}</b></font>',
            styles["small"],
        ))
        elements.append(Spacer(1, 8))

    # Japanese content
    content = _esc(essay.content).replace("【", '<font color="#6366f1"><b>【') \
                                  .replace("】", '】</b></font>')
    elements.append(Paragraph(content, styles["body_large"]))
    elements.append(Spacer(1, 16))

    # Chinese translation
    elements.append(Paragraph("中文翻译", styles["heading"]))
    elements.append(Paragraph(_esc(essay.chinese_translation), styles["body"]))
    elements.append(Spacer(1, 20))

    now = datetime.now()
    elements.append(Paragraph(
        f"导出时间: {now.strftime('%Y-%m-%d %H:%M')}",
        styles["footer"],
    ))

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, essay.title),
               onLaterPages=lambda c, d: _header_footer(c, d, essay.title))
    buf.seek(0)
    return buf


def generate_cloze_pdf(cloze) -> BytesIO:
    """Generate a PDF for a cloze exercise."""
    import json

    font_name = _jp_font_name()
    styles = _build_styles(font_name)
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=_MARGIN,
        leftMargin=_MARGIN,
        topMargin=_MARGIN + 8,
        bottomMargin=_MARGIN + 16,
        title=cloze.title,
        author="多模态日语词汇学习",
    )

    blanks = json.loads(cloze.blanks) if isinstance(cloze.blanks, str) else cloze.blanks

    elements: list = []
    elements.append(Paragraph(f"完型填空 — {_esc(cloze.title)}", styles["title"]))
    if cloze.jlpt_level:
        elements.append(Paragraph(
            f'<font color="{jlpt_color(cloze.jlpt_level)}"><b>{_esc(cloze.jlpt_level)}</b></font>',
            styles["small"],
        ))
        elements.append(Spacer(1, 8))

    # Passage with ____ blanks
    passage_text = _esc(cloze.passage).replace("____", " ________ ")
    elements.append(Paragraph(passage_text, styles["body_large"]))
    elements.append(Spacer(1, 16))

    # Answer key
    elements.append(Paragraph("答案", styles["heading"]))
    answer_header = ["序号", "答案", "假名"]
    answer_data = [answer_header]
    for b in blanks:
        answer_data.append([str(b.get("id", "")), _esc(b.get("answer", "")), _esc(b.get("kana", ""))])

    tbl = Table(answer_data, colWidths=[40, 120, 120])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), _BRAND),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _STRIPE]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(tbl)
    elements.append(Spacer(1, 12))

    # Chinese translation
    if cloze.chinese_translation:
        elements.append(Paragraph("中文翻译", styles["heading"]))
        elements.append(Paragraph(_esc(cloze.chinese_translation), styles["body"]))

    elements.append(Spacer(1, 20))
    now = datetime.now()
    elements.append(Paragraph(
        f"导出时间: {now.strftime('%Y-%m-%d %H:%M')}",
        styles["footer"],
    ))

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, cloze.title),
               onLaterPages=lambda c, d: _header_footer(c, d, cloze.title))
    buf.seek(0)
    return buf


def generate_grammar_compare_pdf(grammar) -> BytesIO:
    """Generate a PDF for a grammar comparison result."""
    import json

    font_name = _jp_font_name()
    styles = _build_styles(font_name)
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=_MARGIN,
        leftMargin=_MARGIN,
        topMargin=_MARGIN + 8,
        bottomMargin=_MARGIN + 16,
        title=f"语法辨析 — {grammar.topic}",
        author="多模态日语词汇学习",
    )

    result = json.loads(grammar.result) if isinstance(grammar.result, str) else grammar.result

    elements: list = []
    elements.append(Paragraph(f"语法辨析 — {_esc(grammar.topic)}", styles["title"]))
    elements.append(Spacer(1, 8))

    # Summary
    if result.get("summary"):
        elements.append(Paragraph(_esc(result["summary"]), styles["body"]))
        elements.append(Spacer(1, 12))

    # Comparison table
    rows = result.get("rows", [])
    if rows:
        table_header = ["语法点", "接续", "含义", "例句", "例句翻译"]
        table_data = [table_header]
        for r in rows:
            table_data.append([
                _esc(r.get("grammar", "")),
                _esc(r.get("pattern", "")),
                _esc(r.get("meaning", "")),
                _esc(r.get("example", "")),
                _esc(r.get("example_cn", "")),
            ])

        col_widths = [72, 72, 64, 144, 128]
        tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 0), (-1, 0), _BRAND),
            ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _STRIPE]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(tbl)

    elements.append(Spacer(1, 20))
    now = datetime.now()
    elements.append(Paragraph(
        f"导出时间: {now.strftime('%Y-%m-%d %H:%M')}",
        styles["footer"],
    ))

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, grammar.topic),
               onLaterPages=lambda c, d: _header_footer(c, d, grammar.topic))
    buf.seek(0)
    return buf
