# -*- coding: utf-8 -*-
"""问卷功能端到端测试（本地起服务后运行）。

前置：本地已启动后端（默认 http://127.0.0.1:8099），DB 由 DATABASE_URL 指定。
用法：
    python dev_tools/test_questionnaire.py
    QQ_DB=data/test_qq.db python dev_tools/test_questionnaire.py

覆盖：问卷列表 → 取卷 → 必答校验 → 选项校验 → 提交 → 防重复 → 管理员统计 → CSV 导出。
"""
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request

BASE = os.getenv("QQ_BASE", "http://127.0.0.1:8099/api")
DB = os.getenv("QQ_DB", "data/test_qq.db")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


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


def make_admin(username: str):
    """直接改库把账号设为管理员（本地测试用；get_admin_user 每次从库里读）。"""
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()


failures = []


def check(cond, msg):
    if cond:
        print(f"  ✓ {msg}")
    else:
        print(f"  ✗ {msg}")
        failures.append(msg)


print("== 1. 注册测试用户 ==")
s, d = req("POST", "/register", {"username": "qq_test", "password": "Pass123456", "name": "问卷测试"})
if s != 200:
    s, d = req("POST", "/login", {"username": "qq_test", "password": "Pass123456"})
assert s == 200, d
TOKEN = d["access_token"]
check(True, "取得 token")

print("== 2. 问卷列表 ==")
s, d = req("GET", "/questionnaires", token=TOKEN)
check(s == 200, f"列表返回 200（实际 {s}）")
forms = d.get("questionnaires", [])
names = [f["display_name"] for f in forms]
print("     ", "、".join(names))
check(len(forms) == 5, f"共 5 份问卷（实际 {len(forms)}）")
check(all("（实验组）" not in f["display_name"] and "（对照组）" not in f["display_name"]
          for f in forms if f["code"].startswith("q2") or f["code"] == "q2"),
      "卷2 已取消实验组/对照组分组，仅一份")
check(all(f["display_name"].startswith(("卷1", "卷2", "卷3", "卷4")) for f in forms),
      "展示名均为「卷N 名称」形式")
check(d.get("submitted_count") == 0, "初始提交数为 0")

print("== 3. 取卷 1 题目定义 ==")
s, d = req("GET", "/questionnaires/q1", token=TOKEN)
check(s == 200, f"取卷返回 200（实际 {s}）")
q = d.get("questionnaire", {})
check(len(q.get("pages", [])) == 5, f"卷1 共 5 页（实际 {len(q.get('pages', []))}）")
check("匿名编码" in q.get("intro", ""), "卷首语含匿名编码说明")
p2 = q["pages"][1]["items"][0]
check(p2["type"] == "matrix" and len(p2["rows"]) == 18, "第2页为 18 行矩阵题")
check(p2.get("reverse_rows") == [5, 6, 11, 12, 16, 17], "BPNS 反向题行号正确")
check(q["pages"][2]["items"][0]["scale"]["max_label"] == "非常强烈", "情绪题量表标签正确")

print("== 4. 必答校验 ==")
s, d = req("POST", "/questionnaires/q1", {"answers": {}, "duration_sec": 60}, token=TOKEN)
check(s == 400, f"空作答被拒（实际 {s}）")
print("     提示：", d.get("detail"))

print("== 5. 选项范围校验（其余题目全部合法作答，只留一个非法值）==")
s, d = req("GET", "/questionnaires/q1", token=TOKEN)
q = d["questionnaire"]


def fill(q, value=4):
    """按题目定义生成一份完整合法作答。"""
    out = {}
    for page in q["pages"]:
        for item in page["items"]:
            if item["type"] == "matrix":
                for i in range(1, len(item["rows"]) + 1):
                    out[f"{item['key']}_r{i}"] = value
            elif item["type"] == "radio":
                out[item["key"]] = item["options"][0]
            elif item["type"] == "text":
                out[item["key"]] = "0521LX"
            else:
                out[item["key"]] = "测试作答"
    return out


answers = fill(q)
answers["p1q2"] = "外星人"
s, d = req("POST", "/questionnaires/q1", {"answers": answers, "duration_sec": 60}, token=TOKEN)
check(s == 400 and "不合法" in str(d.get("detail", "")), f"非法选项被拒（实际 {s} {d.get('detail')}）")

print("== 6. 正常提交 ==")
answers = fill(q)
s, d = req("POST", "/questionnaires/q1", {"answers": answers, "duration_sec": 480}, token=TOKEN)
check(s == 200, f"提交成功（实际 {s} {d}）")

print("== 7. 防重复提交 ==")
s, d = req("POST", "/questionnaires/q1", {"answers": answers, "duration_sec": 480}, token=TOKEN)
check(s == 409, f"重复提交被拒（实际 {s}）")

print("== 8. 列表显示已提交 ==")
s, d = req("GET", "/questionnaires", token=TOKEN)
q1 = [f for f in d["questionnaires"] if f["code"] == "q1"][0]
check(q1["submitted"] is True and q1["duration_sec"] == 480, "列表反映提交状态与用时")

print("== 9. 我的提交记录（含维度分）==")
s, d = req("GET", "/questionnaires/my/history", token=TOKEN)
check(s == 200 and len(d.get("items", [])) == 1, "历史记录 1 条")
scores = d["items"][0]["scores"]
print("     维度分：", json.dumps(scores, ensure_ascii=False))
# 反向题：作答全 4 → 反向题为 6-4=2，维度均值应为 3.333
check(abs(scores.get("Q1_胜任感", 0) - 10 / 3) < 0.01, "含反向题的维度分计算正确（4 与 2 的均值=3.333）")

print("== 10. 管理员统计 ==")
s, d = req("POST", "/register", {"username": "qq_admin", "password": "Pass123456", "name": "问卷管理员"})
if s != 200:
    s, d = req("POST", "/login", {"username": "qq_admin", "password": "Pass123456"})
ATOKEN = d["access_token"]
make_admin("qq_admin")
s, d = req("GET", "/admin/questionnaires/stats", token=ATOKEN)
check(s == 200, f"管理员统计可访问（实际 {s}）")
if s == 200:
    summ = {x["code"]: x for x in d["summary"]}
    check(len(summ) == 5, "统计覆盖 5 份问卷")
    check("q2" in summ and "q2_ctrl" not in summ, "卷2 为单一版本（无对照组版）")
    check(summ["q2"]["item_count"] == 69, f"卷2 题量 69（实际 {summ['q2']['item_count']}）")
    check(summ["q1"]["submitted"] == 1, "卷1 提交数 = 1")
    detail = d["detail"]["q1"][0]
    check(detail["name"] == "问卷测试", "明细显示昵称")
    check(len(detail["answers"]) == 42, f"明细含 42 个作答（实际 {len(detail['answers'])}）")
    check("Q7_自我效能" in detail["scores"], "明细含维度分")
    check(len(d["labels"]["q1"]) == 42, "含题号-题干对照")

print("== 10.5 开放题选填（卷3：留空也应能提交）==")
s, d = req("GET", "/questionnaires/q3", token=TOKEN)
q3 = d["questionnaire"]
a3 = fill(q3)
a3.pop("p6q1", None)      # 开放题留空
a3.pop("p6q2", None)
s, d = req("POST", "/questionnaires/q3", {"answers": a3, "duration_sec": 300}, token=TOKEN)
check(s == 200, f"卷3 开放题留空仍可提交（实际 {s} {d}）")
s, d = req("GET", "/questionnaires/q3", token=TOKEN)
check(d["submitted"] and "p6q1" not in d["my_answers"], "开放题空值不落库")

print("== 11. 普通用户不得访问管理员接口 ==")
s, d = req("GET", "/admin/questionnaires/stats", token=TOKEN)
check(s == 403, f"普通用户被拒（实际 {s}）")

print("== 12. CSV 导出 ==")
s, body = req("GET", "/admin/questionnaires/export?code=q1&kind=data", token=ATOKEN, raw=True)
check(s == 200, f"数据导出成功（实际 {s}）")
text = body.decode("utf-8-sig")
lines = text.strip().split("\n")
check("维度分_Q7_自我效能" in lines[0], "表头含维度分列")
check("p2m1_r1" in lines[0], "表头含条目 key 列")
check(len(lines) >= 2 and "qq_test" in lines[1], "数据行含作答者")
print(f"     数据行：{lines[1][:110]}…")

s, body = req("GET", "/admin/questionnaires/export?code=q1&kind=dict", token=ATOKEN, raw=True)
check(s == 200, f"对照表导出成功（实际 {s}）")
dtext = body.decode("utf-8-sig")
check("学号后4位" in dtext, "对照表含题干原文")
check("反向计分" in dtext, "对照表标注反向计分")

print("== 13. 越权/异常输入 ==")
s, d = req("GET", "/questionnaires/not_exist", token=TOKEN)
check(s == 404, "不存在的问卷返回 404")
s, d = req("POST", "/questionnaires/q1", {"answers": {"p1q1": "x" * 5000}}, token=TOKEN)
check(s in (400, 409), f"超长/非法输入被拒（实际 {s}）")

print()
if failures:
    print(f"FAIL（{len(failures)} 项未通过）")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("PASS：问卷功能全部通过")
