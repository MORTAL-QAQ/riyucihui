# -*- coding: utf-8 -*-
"""冒烟测试：注册带昵称 / 默认昵称=用户名 / me 返回 name / 改名 / 改密码 / 旧token失效。"""
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

# 1) 注册带昵称
s, d = req("POST", "/register", {"username": "nickuser1", "password": "Pass123456", "name": "小明"})
print("1 注册带昵称:", s, "name =", d.get("name"))
assert s == 200 and d.get("name") == "小明"

# 2) 注册不带昵称 → name 默认 = username
s, d = req("POST", "/register", {"username": "noname1", "password": "Pass123456"})
print("2 注册默认昵称:", s, "name =", d.get("name"))
assert s == 200 and d.get("name") == "noname1"
TOKEN = d["access_token"]

# 3) me 返回 name
s, d = req("GET", "/me", token=TOKEN)
print("3 me:", s, "name =", d.get("name"))
assert s == 200 and d.get("name") == "noname1"

# 4) 改名
s, d = req("PUT", "/settings/name", {"name": "新昵称"}, token=TOKEN)
print("4 改名:", s, d)
assert s == 200 and d.get("name") == "新昵称"
s, d2 = req("GET", "/me", token=TOKEN)
assert d2.get("name") == "新昵称"

# 5) 改密码（错误旧密码 → 400）
s, d = req("PUT", "/settings/password", {"old_password": "WrongPass", "new_password": "NewPass123"}, token=TOKEN)
print("5a 错误旧密码:", s, d)
assert s == 400

# 6) 改密码（正确）→ 旧 token 失效
s, d = req("PUT", "/settings/password", {"old_password": "Pass123456", "new_password": "NewPass123"}, token=TOKEN)
print("5b 改密码成功:", s, d)
assert s == 200
s, d = req("GET", "/me", token=TOKEN)
print("5c 旧token访问me:", s, d)
assert s == 401, "改密码后旧 token 应失效"

# 7) 新密码登录
s, d = req("POST", "/login", {"username": "noname1", "password": "NewPass123"})
print("6 新密码登录:", s, "name =", d.get("name"))
assert s == 200

# 8) 新密码改回（旧密码应为 NewPass123）
s, d = req("PUT", "/settings/password", {"old_password": "NewPass123", "new_password": "Pass123456"}, token=d["access_token"])
print("7 改回密码:", s)
assert s == 200

print("\n全部通过 ✅")
