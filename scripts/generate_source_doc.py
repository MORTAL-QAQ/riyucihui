"""
生成软著源代码文档。

输出格式：
- 每页 50 行代码
- 页眉：AIGC多模态日语词汇学习 V1.0
- 页脚：页码（第 X 页 / 共 60 页）
- 前30页：核心模块
- 后30页：辅助模块
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINES_PER_PAGE = 50
TOTAL_PAGES = 60
HEADER = "AIGC多模态日语词汇学习 V1.0"

# ── 前30页：核心模块 ──
FRONT_FILES = [
    "backend/app/main.py",
    "backend/app/config.py",
    "backend/app/models.py",
    "backend/app/database.py",
    "backend/app/auth.py",
    "backend/app/services/ai_service.py",
    "backend/app/routers/study.py",
]

# ── 后30页：辅助模块 ──
BACK_FILES = [
    "backend/app/services/achievement_service.py",
    "backend/app/services/usage_service.py",
    "backend/app/services/word_service.py",
    "backend/app/services/voicevox_manager.py",
    "backend/app/services/image_service.py",
    "backend/app/services/secrets.py",
    "backend/app/services/rate_limiter.py",
    "backend/app/routers/auth.py",
    "backend/app/routers/generate.py",
    "backend/app/routers/words.py",
    "backend/app/routers/essay.py",
    "backend/app/routers/cloze.py",
    "backend/app/routers/grammar.py",
    "backend/app/routers/voice.py",
    "backend/app/routers/achievement.py",
    "backend/app/routers/settings.py",
    "backend/app/routers/admin_api.py",
    "backend/app/cli.py",
    "backend/app/schemas.py",
    "nginx.conf",
    "docker-compose.yml",
    "Dockerfile",
]


def read_file_lines(rel_path: str) -> list[str]:
    """Read a file and return its lines, skipping empty leading/trailing lines."""
    full_path = os.path.join(PROJECT_ROOT, rel_path)
    if not os.path.exists(full_path):
        print(f"WARNING: {rel_path} not found, skipping", file=sys.stderr)
        return []
    with open(full_path, encoding="utf-8") as f:
        lines = f.readlines()
    # Keep original lines including blank ones, just strip trailing newline for consistent joining
    return [line.rstrip("\n") for line in lines]


def format_page(lines: list[str], page_num: int) -> str:
    """Format a single page with header, code lines, and footer."""
    header_line = f"{HEADER}                         第 {page_num} 页 / 共 {TOTAL_PAGES} 页"
    separator = "─" * 72

    output_lines = [header_line, separator]

    # Pad to exactly 50 lines
    padded = lines[:LINES_PER_PAGE]
    while len(padded) < LINES_PER_PAGE:
        padded.append("")

    output_lines.extend(padded)
    output_lines.append(separator)
    output_lines.append("")  # blank line between pages for readability

    return "\n".join(output_lines)


def paginate(all_lines: list[str]) -> list[list[str]]:
    """Split lines into pages of LINES_PER_PAGE each."""
    pages = []
    for i in range(0, len(all_lines), LINES_PER_PAGE):
        page = all_lines[i:i + LINES_PER_PAGE]
        if len(page) < LINES_PER_PAGE:
            page.extend([""] * (LINES_PER_PAGE - len(page)))
        pages.append(page)
    return pages


def main():
    output_path = os.path.join(PROJECT_ROOT, "源代码文档.txt")

    # ── Collect front 30 pages worth of lines (1500 lines) ──
    front_all: list[str] = []
    for rel_path in FRONT_FILES:
        lines = read_file_lines(rel_path)
        if lines:
            # Add file separator comment
            front_all.append(f"# {'='*60}")
            front_all.append(f"# File: {rel_path}")
            front_all.append(f"# {'='*60}")
            front_all.append("")
            front_all.extend(lines)
            front_all.append("")

    # Trim to exactly 1500 lines for 30 pages
    target_front = LINES_PER_PAGE * 30
    if len(front_all) < target_front:
        print(f"WARNING: front files only have {len(front_all)} lines, need {target_front}",
              file=sys.stderr)
        front_all.extend([""] * (target_front - len(front_all)))
    else:
        front_all = front_all[:target_front]

    # ── Collect back 30 pages worth of lines (1500 lines) ──
    back_all: list[str] = []
    for rel_path in BACK_FILES:
        lines = read_file_lines(rel_path)
        if lines:
            back_all.append(f"# {'='*60}")
            back_all.append(f"# File: {rel_path}")
            back_all.append(f"# {'='*60}")
            back_all.append("")
            back_all.extend(lines)
            back_all.append("")

    target_back = LINES_PER_PAGE * 30
    if len(back_all) < target_back:
        print(f"WARNING: back files only have {len(back_all)} lines, need {target_back}",
              file=sys.stderr)
        back_all.extend([""] * (target_back - len(back_all)))
    else:
        back_all = back_all[:target_back]

    # ── Paginate ──
    front_pages = paginate(front_all)
    back_pages = paginate(back_all)

    # Ensure exactly 30 pages each
    while len(front_pages) < 30:
        front_pages.append([""] * LINES_PER_PAGE)
    while len(back_pages) < 30:
        back_pages.append([""] * LINES_PER_PAGE)

    front_pages = front_pages[:30]
    back_pages = back_pages[:30]

    # ── Write output ──
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"{HEADER} — 源代码文档\n")
        f.write(f"总共 {TOTAL_PAGES} 页 (前30页 + 后30页)\n")
        f.write("=" * 72 + "\n\n")

        for i, page_lines in enumerate(front_pages):
            f.write(format_page(page_lines, i + 1))
            f.write("\n")

        f.write("\n" + "=" * 72 + "\n")
        f.write("（以下为后30页 — 程序结尾部分）\n")
        f.write("=" * 72 + "\n\n")

        for i, page_lines in enumerate(back_pages):
            f.write(format_page(page_lines, 31 + i))
            f.write("\n")

    print(f"Generated: {output_path}")
    print(f"Front pages: {len(front_pages)}")
    print(f"Back pages: {len(back_pages)}")
    print(f"Front lines: {sum(len(p) for p in front_pages)}")
    print(f"Back lines: {sum(len(p) for p in back_pages)}")


if __name__ == "__main__":
    main()
