# -*- coding: utf-8 -*-
"""冒烟：社区显示昵称（非账号）+ 评论归属判断（is_mine）。"""
import json
import random
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

n = random.randint(1000, 9999)
s, d = req("POST", "/register", {"username": f"nick{n}a", "password": "Pass123456", "name": "樱花同学"})
assert s == 200, d
TA = d["access_token"]
s, d = req("POST", "/register", {"username": f"nick{n}b", "password": "Pass123456", "name": "山田太郎"})
assert s == 200, d
TB = d["access_token"]

# B 发帖
s, d = req("POST", "/community/posts", {"title": "昵称测试帖", "content": "内容"}, token=TB)
assert s == 201, d
assert d["username"] == "山田太郎", f"帖子作者应显示昵称，实际: {d['username']}"
print(f"发帖作者显示: {d['username']} ✅（账号 nick{n}b）")
pid = d["id"]

# A 评论
s, d = req("POST", f"/community/posts/{pid}/comments", {"content": "很好的分享"}, token=TA)
assert s == 201, d
assert d["username"] == "樱花同学", f"评论作者应显示昵称: {d['username']}"
assert d["is_mine"] is True
print(f"评论作者显示: {d['username']} ✅ is_mine={d['is_mine']}")

# 帖子列表：作者为昵称
s, d = req("GET", "/community/posts", token=TA)
found = [p for p in d["posts"] if p["id"] == pid]
assert found and found[0]["username"] == "山田太郎", found
print(f"列表作者显示: {found[0]['username']} ✅")

# 详情：B 看该评论（非本人 → is_mine=False）
s, d = req("GET", f"/community/posts/{pid}", token=TB)
c = [x for x in d["comments"] if x["content"] == "很好的分享"][0]
assert c["username"] == "樱花同学" and c["is_mine"] is False, c
print(f"他人视角评论: {c['username']} is_mine={c['is_mine']} ✅（非本人无删除按钮）")

# A 看同一评论（本人 → is_mine=True）
s, d = req("GET", f"/community/posts/{pid}", token=TA)
c = [x for x in d["comments"] if x["content"] == "很好的分享"][0]
assert c["is_mine"] is True, c
print(f"本人视角评论: is_mine={c['is_mine']} ✅")

print("\n社区昵称显示 + 归属判断全部通过 ✅")
