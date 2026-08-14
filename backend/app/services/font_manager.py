"""Japanese font manager for ReportLab PDF generation.

Discovers and registers a Japanese-capable TTF/OTC font for use in PDF exports.
Priority: environment variable FONT_PATH > Noto Sans CJK JP > IPAexGothic > fallback.

Usage:
    from .font_manager import get_font_name
    font_name = get_font_name()  # Returns "JP" or "Helvetica" as fallback
"""

import os
import sys
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONT_REGISTERED = False
_FONT_NAME = "JP"

# Common installation paths for Japanese fonts across platforms.
# .ttc (TrueType Collection) files may contain multiple sub-fonts;
# we typically want subfontIndex=0 for the Regular weight.
_CANDIDATE_PATHS: list[tuple[str, int]] = [
    # 文泉驿微米黑 — fonts-wqy-microhei (TrueType, 完整 CJK, ReportLab 确认兼容)
    ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 0),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0),
    ("/usr/share/fonts/wqy-microhei/wqy-microhei.ttc", 0),
    ("/usr/share/fonts/wqy/wqy-microhei.ttc", 0),
    # IPAexGothic — fonts-ipaexfont (TrueType, CJK, 备选)
    ("/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf", 0),
    ("/usr/share/fonts/opentype/ipaexfont-mincho/ipaexm.ttf", 0),
    ("/usr/share/fonts/opentype/ipaexfont/ipaexg.ttf", 0),
    # Noto Sans CJK — fonts-noto-cjk (CFF outlines, 可能不支持)
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
    # macOS
    ("/System/Library/Fonts/NotoSansCJK-Regular.ttc", 0),
    # Windows
    ("C:\\Windows\\Fonts\\msgothic.ttc", 0),
    ("C:\\Windows\\Fonts\\yugoth.ttc", 0),
]


def _find_font() -> tuple[str, int] | None:
    """Find a usable Japanese font file on the filesystem.

    Returns (path, subfont_index) or None if no font found.
    """
    env_path = os.getenv("FONT_PATH")
    if env_path and Path(env_path).exists():
        return (env_path, 0)

    for path, index in _CANDIDATE_PATHS:
        if Path(path).exists():
            return (path, index)

    # Broader search: walk common font directories for Japanese-named fonts
    for base in ["/usr/share/fonts", "/usr/local/share/fonts"]:
        if not Path(base).exists():
            continue
        for root, _dirs, files in os.walk(base):
            for f in files:
                if not f.lower().endswith((".ttf", ".ttc", ".otf")):
                    continue
                fl = f.lower()
                if any(kw in fl for kw in ["noto", "ipa", "cjk", "gothic", "mincho",
                                             "japanese", "jp-", "-jp", "yugo"]):
                    return (str(Path(root) / f), 0)

    return None


def register_japanese_font() -> str:
    """Register the Japanese font with ReportLab and return the font name.

    Returns "JP" on success, or "Helvetica" if no Japanese font is found.
    Safe to call multiple times — registration is cached.
    """
    global _FONT_REGISTERED

    if _FONT_REGISTERED:
        return _FONT_NAME if _FONT_NAME in pdfmetrics._fonts else "Helvetica"  # type: ignore[union-attr]

    _FONT_REGISTERED = True

    result = _find_font()
    if result is None:
        print(
            "WARNING: No Japanese font found. PDF characters may display as boxes.\n"
            "  Install fonts-noto-cjk or set FONT_PATH environment variable.",
            file=sys.stderr,
        )
        return "Helvetica"

    font_path, subfont_index = result
    try:
        pdfmetrics.registerFont(TTFont(_FONT_NAME, font_path, subfontIndex=subfont_index))
        print(f"[pdf] Registered Japanese font: {font_path}", file=sys.stderr)
        return _FONT_NAME
    except Exception as exc:
        print(f"WARNING: Failed to register font {font_path}: {exc}", file=sys.stderr)
        return "Helvetica"


def get_font_name() -> str:
    """Return the registered Japanese font name, auto-registering on first call.

    Returns "JP" if a Japanese font was found, otherwise "Helvetica".
    """
    return register_japanese_font()
