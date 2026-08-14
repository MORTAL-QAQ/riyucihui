# -*- coding: utf-8 -*-
"""验证：12 页顶栏导航均无静态管理按钮（应由 common.js 动态注入）。"""
import io, re, os

BASE = r"C:\Users\Administrator\Desktop\11\frontend"
pages = ["community", "wordbank", "study", "generate", "essay", "cloze",
         "grammar", "image", "settings", "achievement", "admin", "saved"]
ok = True
for p in pages:
    h = io.open(os.path.join(BASE, p + ".html"), encoding="utf-8").read()
    m = re.search(r'flex-wrap:wrap; justify-content:center;">(.*?)</div>', h, re.S)
    nav = m.group(1) if m else ""
    has = 'href="/admin"' in nav
    if has:
        print(f"{p}: 顶栏仍有静态管理按钮！")
        ok = False
print("全部顶栏无静态管理按钮 ✅" if ok else "存在静态管理按钮 ❌")
