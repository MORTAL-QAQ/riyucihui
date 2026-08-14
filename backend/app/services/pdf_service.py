"""PDF export service for the Japanese vocabulary learning app.

Provides functions to generate PDF documents using ReportLab.
All functions return BytesIO buffers ready for HTTP response.

Design:
- All text uses the Japanese font registered by font_manager.py.
- Styles and table formatting are centralized for visual consistency.
- Each generate_*_pdf function is self-contained and returns a BytesIO.
"""

import base64
from datetime import datetime
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


# ── Helpers ──────────────────────────────────────────────────────────────────


def _jp_font_name() -> str:
    """Lazy-import and return the registered Japanese font name."""
    from .font_manager import get_font_name

    return get_font_name()


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


# ── Image helpers (Phase 2) ──────────────────────────────────────────────────


def _decode_image(image_base64: str, max_width: float = 80, max_height: float = 80):
    """Decode a base64 image string into a ReportLab Image, scaled to fit.

    Returns None if the image is empty or decoding fails.
    """
    if not image_base64:
        return None
    try:
        from reportlab.lib.utils import ImageReader
        from reportlab.platypus import Image as RLImage

        data = image_base64
        if "," in data:
            data = data.split(",", 1)[1]
        img_bytes = base64.b64decode(data)
        img_io = BytesIO(img_bytes)
        reader = ImageReader(img_io)
        iw, ih = reader.getSize()
        ratio = min(max_width / iw, max_height / ih, 1.0)
        return RLImage(reader, width=iw * ratio, height=ih * ratio)
    except Exception:
        return None


# ── Word PDF export ──────────────────────────────────────────────────────────


def generate_words_pdf(
    words,
    topic_name: str,
    total: int,
    *,
    layout: str = "table",
    include_images: bool = True,
) -> BytesIO:
    """Generate a PDF of vocabulary words.

    Args:
        words: List of Word ORM objects.
        topic_name: Display name for the topic (e.g. "食物").
        total: Total word count (for footer).
        layout: "table" for a compact data table, "card" for 2-column cards.
        include_images: Whether to embed AI-generated word images (card mode only).

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
    elements.append(Paragraph(f"多模态日语词汇学习 — {topic_name}", styles["title"]))
    elements.append(Spacer(1, 10))

    if layout == "card" and include_images:
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

    col_widths = [30, 72, 72, 64, 24, 238]
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(_default_table_style(font_name))
    return [tbl]


def _build_word_cards(words, font_name: str, styles: dict) -> list:
    """Build card-mode elements for word export (2-column grid)."""
    elements: list = []
    # Build rows of 2 cards each
    row_data: list[list] = []
    for i in range(0, len(words), 2):
        left = _word_card(words[i], font_name, styles) if i < len(words) else []
        right = _word_card(words[i + 1], font_name, styles) if i + 1 < len(words) else []
        row_data.append([left, right])

    card_width = (A4[0] - _MARGIN * 2) / 2 - 4
    tbl = Table(row_data, colWidths=[card_width, card_width])
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


def _word_card(w, font_name: str, styles: dict) -> list:
    """Build a single word card as a list of flowables."""
    parts: list = []

    # Japanese + kana
    jp_text = f"<b>{w.japanese}</b>"
    if w.kana:
        jp_text += f'  <font size="8" color="#6b7280">{w.kana}</font>'
    parts.append(Paragraph(jp_text, styles["card_jp"]))

    # Chinese meaning
    parts.append(Paragraph(w.chinese, styles["card_cn"]))

    # JLPT badge
    if w.jlpt_level:
        jlpt_color = _JLPT_COLORS.get(w.jlpt_level, "#9ca3af")
        parts.append(Paragraph(
            f'<font color="{jlpt_color}" size="8"><b>{w.jlpt_level}</b></font>',
            styles["small"],
        ))

    # Example
    if w.example_ja:
        ex_text = w.example_ja[:80]
        if len(w.example_ja or "") > 80:
            ex_text += "..."
        parts.append(Paragraph(
            f'<font size="7">{ex_text}</font>',
            styles["small"],
        ))

    # Image (if available)
    img = _decode_image(w.image_base64, max_width=100, max_height=100)
    if img:
        parts.append(Spacer(1, 4))
        parts.append(img)

    return parts


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
    elements.append(Paragraph(essay.title, styles["title"]))
    if essay.jlpt_level:
        jlpt_color = _JLPT_COLORS.get(essay.jlpt_level, "#9ca3af")
        elements.append(Paragraph(
            f'<font color="{jlpt_color}"><b>{essay.jlpt_level}</b></font>',
            styles["small"],
        ))
        elements.append(Spacer(1, 8))

    # Japanese content
    content = essay.content.replace("【", '<font color="#6366f1"><b>【') \
                           .replace("】", '】</b></font>')
    elements.append(Paragraph(content, styles["body_large"]))
    elements.append(Spacer(1, 16))

    # Chinese translation
    elements.append(Paragraph("中文翻译", styles["heading"]))
    elements.append(Paragraph(essay.chinese_translation, styles["body"]))
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
    elements.append(Paragraph(f"完型填空 — {cloze.title}", styles["title"]))
    if cloze.jlpt_level:
        jlpt_color = _JLPT_COLORS.get(cloze.jlpt_level, "#9ca3af")
        elements.append(Paragraph(
            f'<font color="{jlpt_color}"><b>{cloze.jlpt_level}</b></font>',
            styles["small"],
        ))
        elements.append(Spacer(1, 8))

    # Passage with ____ blanks
    passage_text = cloze.passage.replace("____", " ________ ")
    elements.append(Paragraph(passage_text, styles["body_large"]))
    elements.append(Spacer(1, 16))

    # Answer key
    elements.append(Paragraph("答案", styles["heading"]))
    answer_header = ["序号", "答案", "假名"]
    answer_data = [answer_header]
    for b in blanks:
        answer_data.append([str(b.get("id", "")), b.get("answer", ""), b.get("kana", "")])

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
        elements.append(Paragraph(cloze.chinese_translation, styles["body"]))

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
    elements.append(Paragraph(f"语法辨析 — {grammar.topic}", styles["title"]))
    elements.append(Spacer(1, 8))

    # Summary
    if result.get("summary"):
        elements.append(Paragraph(result["summary"], styles["body"]))
        elements.append(Spacer(1, 12))

    # Comparison table
    rows = result.get("rows", [])
    if rows:
        table_header = ["语法点", "接续", "含义", "例句", "例句翻译"]
        table_data = [table_header]
        for r in rows:
            table_data.append([
                r.get("grammar", ""),
                r.get("pattern", ""),
                r.get("meaning", ""),
                r.get("example", ""),
                r.get("example_cn", ""),
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
