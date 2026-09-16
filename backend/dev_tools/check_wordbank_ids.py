# -*- coding: utf-8 -*-
"""检查 wordbank.js 中引用的导出相关 DOM id 是否都存在（防已删元素残留）。"""
import io, re

js = io.open(r"C:\Users\Administrator\Desktop\11\frontend\js\wordbank.js", encoding="utf-8").read()
html = io.open(r"C:\Users\Administrator\Desktop\11\frontend\wordbank.html", encoding="utf-8").read()

ids = set(re.findall(r'\$\("#([A-Za-z0-9_-]+)"\)', js))
ids |= set(re.findall(r'getElementById\("([A-Za-z0-9_-]+)"\)', js))

missing = []
for i in sorted(ids):
    if ('id="' + i + '"') not in html:
        missing.append(i)

print(f"引用 id 数: {len(ids)}")
if missing:
    print("❌ 缺失元素（会导致 null 报错）:")
    for m in missing:
        print("  -", m)
else:
    print("✅ 全部 id 在 HTML 中存在")

# 检查 querySelector 的 name 选择器元素
for sel in re.findall(r'querySelector\("input\[name=.(export-[a-z]+).\]', js):
    has = f'name="{sel}"' in html
    print(f"  name={sel}: {'✅' if has else '❌ 缺失'}")
