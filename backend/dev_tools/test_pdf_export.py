# -*- coding: utf-8 -*-
"""冒烟：词库 PDF 导出（table / card 布局）端到端。"""
import json
import urllib.request

BASE = "http://127.0.0.1:8099/api"

def req(method, path, body=None, token=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            if raw:
                return resp.status, resp.read()
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

import random
u = f"pdf{random.randint(10000, 99999)}"
s, d = req("POST", "/register", {"username": u, "password": "Pass123456", "name": "PDF测试"})
assert s == 200, d
T = d["access_token"]

# 加词（含全部必填字段）
s, d = req("POST", "/words", {
    "topic": "天气",
    "jlpt_level": "N4",
    "words": [
        {"japanese": "天気", "kana": "てんき", "chinese": "天气", "example_ja": "今日はいい天気です。", "example_cn": "今天天气很好。", "jlpt_level": "N4"},
        {"japanese": "雨", "kana": "あめ", "chinese": "雨", "example_ja": "雨が降っています。", "example_cn": "正在下雨。", "jlpt_level": "N5"},
    ],
}, token=T)
print("加词:", s)
assert s in (200, 201), d

# 导出 PDF（table / card）
for layout in ("table", "card"):
    s, body = req("GET", f"/words/export/pdf?layout={layout}", token=T, raw=True)
    ok = s == 200 and body[:4] == b"%PDF"
    print(f"导出 {layout}: {s} size={len(body) if isinstance(body, bytes) else body} PDF头={ok}")
    assert ok, body

print("\nPDF 导出端到端通过 ✅")
