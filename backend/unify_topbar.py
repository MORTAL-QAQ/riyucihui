# -*- coding: utf-8 -*-
"""统一所有独立子页顶栏导航：同一套完整导航（返回首页·词库·背词·生成·社区·短文·完型·语法·图片·成就·保存），当前页高亮；管理页额外含「管理」高亮项。"""
import io, re

PAGES = ["community", "wordbank", "study", "generate", "essay", "cloze",
         "grammar", "image", "settings", "achievement", "admin", "saved"]

NAV_ITEMS = [
    ("/", "🏠 返回首页", "home"),
    ("/wordbank", "📖 词库", "wordbank"),
    ("/study", "📝 背词", "study"),
    ("/generate", "✦ 生成", "generate"),
    ("/community", "💬 社区", "community"),
    ("/essay", "📄 短文", "essay"),
    ("/cloze", "📝 完型", "cloze"),
    ("/grammar", "📐 语法", "grammar"),
    ("/image", "📷 图片", "image"),
    ("/achievement", "🏆 成就", "achievement"),
    ("/saved", "💾 保存", "saved"),
]

HOME_STYLE = "display:inline-flex; align-items:center; gap:6px; color:#e5e7eb; text-decoration:none; font-size:14px; font-weight:600; padding:7px 14px; border-radius:999px; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.12);"
NORMAL_STYLE = "display:inline-flex; align-items:center; gap:4px; color:#d5d8e6; text-decoration:none; font-size:13px; padding:7px 12px; border-radius:999px; background:rgba(255,255,255,0.04); border:1px solid transparent;"
ACTIVE_STYLE = "display:inline-flex; align-items:center; gap:4px; color:#fff; text-decoration:none; font-size:13px; padding:7px 12px; border-radius:999px; background:rgba(99,102,241,0.35); border:1px solid rgba(129,140,248,0.4);"

def nav_block(current):
    lines = []
    for href, label, key in NAV_ITEMS:
        if key == "home":
            style = HOME_STYLE
            a = f'<a href="{href}" style="{style}"><span>🏠</span> 返回首页</a>'
        elif key == current:
            style = ACTIVE_STYLE
            a = f'<a href="{href}" style="{style}">{label}</a>'
        else:
            style = NORMAL_STYLE
            a = f'<a href="{href}" style="{style}">{label}</a>'
        lines.append("            " + a)
    if current == "admin":
        lines.append("            " + f'<a href="/admin" style="{ACTIVE_STYLE}">🛡 管理</a>')
    return "\n".join(lines) + "\n"

def read(p):
    return io.open(p, encoding="utf-8").read()

def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)

for page in PAGES:
    path = r"C:\Users\Administrator\Desktop\11\frontend" + "\\" + page + ".html"
    text = read(path)
    lines = text.split("\n")
    # 定位导航容器 div（含 flex-wrap:wrap; justify-content:center）
    start = None
    for i, ln in enumerate(lines):
        if "flex-wrap:wrap; justify-content:center" in ln and "<div" in ln:
            start = i
            break
    assert start is not None, f"{page}: 未找到导航容器"
    indent = re.match(r"\s*", lines[start]).group(0)
    # 找第一个同缩进的 </div>（导航 div 内只有 <a>，无嵌套 div）
    end = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "</div>" and re.match(r"\s*", lines[i]).group(0) == indent:
            end = i
            break
    assert end is not None, f"{page}: 未找到导航闭合"
    old_block = "\n".join(lines[start + 1:end])
    new_block = nav_block(page)
    lines[start + 1:end] = [new_block.rstrip("\n")]
    write(path, "\n".join(lines))
    print(f"{page}: 导航 {len(NAV_ITEMS) + (1 if page == 'admin' else 0)} 项替换完成")

print("done")
