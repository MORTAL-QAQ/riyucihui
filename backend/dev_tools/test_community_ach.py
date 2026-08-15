# -*- coding: utf-8 -*-
"""冒烟：社区互动成就（首次点赞/首条评论/发帖10篇）。"""
import json
import urllib.request

BASE = "http://127.0.0.1:8099/api"

def req(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def achs(token):
    s, d = req("GET", "/achievements", token=token)
    return {a["key"]: a for a in d.get("achievements", [])}

# 用户 A：发帖/点赞/评论
s, d = req("POST", "/register", {"username": "achA", "password": "Pass123456", "name": "成就A"})
assert s == 200
TA = d["access_token"]
# 用户 B：发帖供 A 点赞评论
s, d = req("POST", "/register", {"username": "achB", "password": "Pass123456"})
assert s == 200
TB = d["access_token"]

# B 发一帖
s, d = req("POST", "/community/posts", {"title": "测试帖", "content": "内容"}, token=TB)
assert s == 201, d
pid = d["id"]

# A 首次点赞 → 应解锁 first_like
s, d = req("POST", f"/community/posts/{pid}/like", {}, token=TA)
print("点赞:", s, "liked =", d.get("liked"), "new =", d.get("new_achievements"))
assert s == 200 and d.get("liked") is True
ach = achs(TA)
print("first_like 解锁:", ach.get("first_like", {}).get("achieved"))
assert ach["first_like"]["achieved"]

# A 首次评论 → 应解锁 first_comment
s, d = req("POST", f"/community/posts/{pid}/comments", {"content": "好帖"}, token=TA)
print("评论:", s, "new =", d.get("new_achievements"))
assert s == 201
ach = achs(TA)
print("first_comment 解锁:", ach.get("first_comment", {}).get("achieved"))
assert ach["first_comment"]["achieved"]

# A 发 10 帖 → posts_10 解锁（需累计 10 篇，含 first_post）
for i in range(10):
    s, d = req("POST", "/community/posts", {"title": f"A 的帖子 {i}", "content": "x"}, token=TA)
    assert s == 201
ach = achs(TA)
print("first_post 解锁:", ach.get("first_post", {}).get("achieved"))
print("posts_10 解锁:", ach.get("posts_10", {}).get("achieved"))
assert ach["first_post"]["achieved"] and ach["posts_10"]["achieved"]

print("\n全部通过 ✅")
