# -*- coding: utf-8 -*-
import io
h = io.open(r"C:\Users\Administrator\Desktop\11\frontend\index.html", encoding="utf-8").read()
assert 'placeholder="账号"' in h, "账号 placeholder 缺失"
assert 'placeholder="用户名"' not in h, "旧用户名 placeholder 残留"
print("登录表单验证 OK: 账号 + 密码")
