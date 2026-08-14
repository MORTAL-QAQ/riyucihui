# -*- coding: utf-8 -*-
"""验证顶栏/侧边栏/更多菜单顺序一致：社区在学习功能（词库/背词/生成/短文/完型/语法/图片）之后。"""
import io, re, os

BASE = r"C:\Users\Administrator\Desktop\11\frontend"
EXPECTED = ["home", "wordbank", "study", "generate", "essay", "cloze",
            "grammar", "image", "community", "achievement", "saved"]

ok = True

# 1) 各独立页顶栏顺序（提取导航 href 顺序；admin 页额外高亮项在末尾，不算错）
for page in ["community", "wordbank", "study", "generate", "essay", "cloze",
             "grammar", "image", "settings", "achievement", "admin", "saved"]:
    h = io.open(os.path.join(BASE, page + ".html"), encoding="utf-8").read()
    nav = re.search(r'<div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; justify-content:center;">(.*?)</div>', h, re.S)
    if not nav:
        print(f"{page}: 未找到导航区")
        ok = False
        continue
    hrefs = re.findall(r'<a href="(/[^"]*)"', nav.group(1))
    tabs = ["home" if x == "/" else x.strip("/") for x in hrefs]
    extra = ["admin"] if page == "admin" else []
    good = tabs == EXPECTED + extra
    if not good:
        print(f"{page} 顶栏顺序不符: {tabs}")
        ok = False

# 2) 首页侧边栏（前 11 项 = 顶栏顺序；settings/admin 在末尾）
h = io.open(os.path.join(BASE, "index.html"), encoding="utf-8").read()
nav = re.search(r'<nav class="nav">(.*?)</nav>', h, re.S).group(1)
tabs = re.findall(r'data-tab="([a-z]+)"', nav)
good = tabs == EXPECTED + ["settings", "admin"]
print(f"侧边栏顺序一致: {good}")
if not good:
    print("  实际:", tabs)
    ok = False

# 3) 移动端更多菜单（底部固定含 study/wordbank/generate/essay，更多菜单顺序应与其衔接一致）
more = re.search(r'<div class="more-menu-popup".*?</div>\s*</div>', h, re.S).group(0)
more_tabs = re.findall(r'data-tab="([a-z]+)"', more)
bottom = ["study", "wordbank", "generate", "essay"]
sub = [t for t in EXPECTED if t not in bottom] + ["settings"]
good = more_tabs == sub
print(f"更多菜单顺序一致: {good} 实际: {more_tabs}")
if not good:
    ok = False

print("全部通过 ✅" if ok else "有不一致 ❌")
