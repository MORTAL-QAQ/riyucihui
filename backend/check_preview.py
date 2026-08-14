# -*- coding: utf-8 -*-
"""检查各生成页 runStreamToPreview 的 previewId（第3个参数）与 html 元素匹配。"""
import io, re, os

BASE = r"C:\Users\Administrator\Desktop\11\frontend"

for page in ["generate", "essay", "cloze", "grammar"]:
    js = io.open(os.path.join(BASE, "js", page + ".js"), encoding="utf-8").read()
    html = io.open(os.path.join(BASE, page + ".html"), encoding="utf-8").read()
    # 匹配 runStreamToPreview(url, body, "previewId", ...) 的第三个字符串参数
    pat = re.compile(r'runStreamToPreview\(\s*"[^"]+"\s*,[^,]+,\s*"([^"]+)"')
    found = pat.findall(js)
    for pid in found:
        ok = ('id="' + pid + '"') in html
        print(f"{page}: previewId={pid} exists={ok}")
    if not found:
        print(f"{page}: 未匹配到调用（可能跨行，需人工确认）")

print("done")
