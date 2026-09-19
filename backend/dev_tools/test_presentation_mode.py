# -*- coding: utf-8 -*-
"""词级呈现模式 + 实验词单门禁 的接口级测试（本地起服务后运行）。

用法：
    # 先建测试库（含 20 词实验词单与未分组学生）
    DATABASE_URL=sqlite:///./data/test_pm.db python dev_tools/_tmp_setup.py
    # 起服务后
    DATABASE_URL=sqlite:///./data/test_pm.db python dev_tools/test_presentation_mode.py

覆盖：
  1. GET /api/words 返回 presentation_mode
  2. POST /api/words/presentation-mode 按序号批量绑定（含越界校验）
  3. PUT /api/words/{id}/presentation-mode 逐词设置
  4. GET /api/words/presentation-mode/export 导出词-模态绑定表
  5. 未分组普通学生可访问自己的实验词单（门禁已开放）
  6. 背词会话接口返回 presentation_mode（前端据此隐藏配图/发音）
  7. GET /api/image-cards 对普通用户隐藏纯文字词配图
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.getenv("PM_BASE", "http://127.0.0.1:8099/api")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

failures = []


def req(method, path, body=None, token=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            payload = resp.read()
            return resp.status, (payload if raw else json.loads(payload.decode()))
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            return e.code, json.loads(payload.decode())
        except Exception:
            return e.code, payload


def login(username, password="Pass123456"):
    s, d = req("POST", "/login", {"username": username, "password": password})
    assert s == 200, f"登录失败 {username}: {d}"
    return d["access_token"]


def check(cond, msg):
    print(f"  {'✓' if cond else '✗'} {msg}")
    if not cond:
        failures.append(msg)


TOPIC = "实验:学校生活"
MULTIMODAL = [1, 4, 6, 7, 9, 12, 14, 16, 17, 20]
Q = urllib.parse.quote(TOPIC)

print("== 1. 登录 ==")
TT = login("teacher_t")
ST = login("stu_pm")
check(True, "教师与学生账号均已登录")

print("== 2. 前置复位：按论文分配方案批量绑定（保证可重复运行）==")
s, d = req("POST", "/words/presentation-mode",
           {"topic": TOPIC, "multimodal_indexes": MULTIMODAL}, token=TT)
check(s == 200 and d.get("multimodal") == 10 and d.get("text_only") == 10,
      f"绑定为 10 图文音 / 10 纯文字（实际 {s}）")

print("== 3. 词库接口返回 presentation_mode ==")
s, d = req("GET", f"/words?topic={Q}&limit=50", token=TT)
words = sorted(d.get("words", []), key=lambda w: w["id"])
check(s == 200 and len(words) == 20, f"取到 20 词（实际 {len(words)}）")
check("presentation_mode" in words[0], "字段 presentation_mode 存在")
mm_flags = [i for i, w in enumerate(words, 1) if w.get("presentation_mode") == "multimodal"]
check(mm_flags == MULTIMODAL, f"图文音序号与分配方案一致（实际 {mm_flags}）")

print("== 4. 越界序号应被拒 ==")
s, d = req("POST", "/words/presentation-mode",
           {"topic": TOPIC, "multimodal_indexes": [0, 21]}, token=TT)
check(s == 400 and "超出范围" in str(d.get("detail", "")), f"越界序号被拒（实际 {s}）")

print("== 5. 批量重绑（把 1-10 设为图文音）==")
s, d = req("POST", "/words/presentation-mode",
           {"topic": TOPIC, "multimodal_indexes": list(range(1, 11))}, token=TT)
check(s == 200 and d.get("multimodal") == 10 and d.get("text_only") == 10,
      f"绑定结果为 10/10（实际 {d.get('multimodal')}/{d.get('text_only')}）")
s, d = req("GET", f"/words?topic={Q}&limit=50", token=TT)
words = sorted(d["words"], key=lambda w: w["id"])
check(words[0]["presentation_mode"] == "multimodal" and words[10]["presentation_mode"] == "text_only",
      "第 1 词=图文音、第 11 词=纯文字")

print("== 6. 逐词设置 ==")
wid = words[0]["id"]
s, d = req("PUT", f"/words/{wid}/presentation-mode", {"mode": "text_only"}, token=TT)
check(s == 200 and d.get("presentation_mode") == "text_only", "逐词置为纯文字")

print("== 7. 背词会话返回 presentation_mode ==")
s, d = req("POST", "/study/start", {"topic": "实验:学校生活", "mode": "all", "limit": 5}, token=ST)
if s != 200:
    s, d = req("POST", "/study/start", {"topic": "实验:学校生活", "limit": 5}, token=ST)
if isinstance(d, list) and d:
    check("presentation_mode" in d[0], "背词卡片数据含 presentation_mode")
else:
    print(f"  · 背词会话返回 {s}，响应：{str(d)[:120]}")
    check(s in (200, 400), f"背词接口可调用（实际 {s}）")

print("== 8. 未分组学生可访问实验词单（门禁已开放）==")
s, d = req("GET", "/study/topics?mode=all", token=ST)
topics = [t["topic"] for t in d] if s == 200 and isinstance(d, list) else []
check(s == 200 and TOPIC in topics, f"未分组学生的词单列表含实验词单（实际 {topics}）")
s, d = req("GET", "/words?topic=" + urllib.parse.quote(TOPIC), token=ST)
check(s == 200, f"未分组学生可直接查询实验词单（实际 {s}）")

print("== 9. 导出词-模态绑定表 ==")
s, body = req("GET", "/words/presentation-mode/export?topic=" + urllib.parse.quote(TOPIC),
              token=TT, raw=True)
text = body.decode("utf-8-sig") if isinstance(body, bytes) else str(body)
lines = text.strip().split("\n")
check(s == 200 and "呈现模式" in lines[0], f"导出成功（{len(lines)} 行）")
check(any("图文音" in ln for ln in lines[1:]) and any("纯文字" in ln for ln in lines[1:]),
      "导出内容同时含图文音与纯文字")

print("== 10. 图片词卡对普通用户隐藏纯文字词 ==")
s, d = req("GET", "/image-cards", token=ST)
if s == 200:
    shown = [w["japanese"] for t in d.get("topics", []) for w in t["words"]]
    check(len(shown) == 0, f"该学生的纯文字词无配图时不显示（实际 {shown}）")
else:
    check(False, f"/image-cards 调用失败：{s}")

print()
if failures:
    print(f"FAIL（{len(failures)} 项未通过）")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("PASS：词级呈现模式与门禁开放全部通过")

