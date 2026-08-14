# -*- coding: utf-8 -*-
"""检查各独立页 js 引用的 DOM id 是否存在于对应 html（运行时崩溃排查）。"""
import io, re, os

BASE = r"C:\Users\Administrator\Desktop\11\frontend"

def read(p):
    return io.open(p, encoding="utf-8").read()

pages = ["generate", "essay", "cloze", "grammar", "study", "wordbank",
         "community", "image", "settings", "achievement", "admin", "saved"]

for page in pages:
    js_path = os.path.join(BASE, "js", page + ".js")
    html_path = os.path.join(BASE, page + ".html")
    if not os.path.exists(js_path) or not os.path.exists(html_path):
        continue
    js = read(js_path)
    html = read(html_path)
    ids_in_js = set(re.findall(r'\$\("#([A-Za-z0-9_-]+)"\)', js))
    ids_in_js |= set(re.findall(r'getElementById\("([A-Za-z0-9_-]+)"\)', js))
    ids_in_js |= set(re.findall(r'querySelector\("#([A-Za-z0-9_-]+)"\)', js))
    missing = [i for i in sorted(ids_in_js) if ('id="' + i + '"') not in html]
    if missing:
        print(f"{page}.js 缺失 id: {missing}")
    else:
        print(f"{page}: OK ({len(ids_in_js)} 个 id 全部存在)")

# common.js 与 api.js 的 id 引用（用于各页）
for f in ["common.js", "api.js"]:
    js = read(os.path.join(BASE, "js", f))
    ids = set(re.findall(r'\$\("#([A-Za-z0-9_-]+)"\)', js))
    ids |= set(re.findall(r'getElementById\("([A-Za-z0-9_-]+)"\)', js))
    print(f"{f}: 引用了 {len(ids)} 个 id（跨页使用，需各页存在）")

print("done")
