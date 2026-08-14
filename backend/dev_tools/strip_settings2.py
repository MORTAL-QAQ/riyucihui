# -*- coding: utf-8 -*-
"""设置页拆分收尾：app.js 移除 pageSettings/pages 条目 + switchTab 跳转；index.html 删除 page-settings section。"""
import io

def read(p):
    return io.open(p, encoding="utf-8").read()

def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)

# ---------- app.js ----------
ap = r"C:\Users\Administrator\Desktop\11\frontend\js\app.js"
a = read(ap)

# 1) 删 pageSettings 变量行
old = 'const pageSettings = $("#page-settings");\n'
assert a.count(old) == 1, "pageSettings 变量行数量异常"
a = a.replace(old, "")

# 2) pages 数组移除 pageSettings
old = "const pages = [pageHome, pageSaved, pageAchievement, pageSettings, pageAdmin];"
assert a.count(old) == 1, "pages 数组异常"
a = a.replace(old, "const pages = [pageHome, pageSaved, pageAchievement, pageAdmin];")

# 3) switchTab settings 分支改为跳转
old = '''  } else if (tab === "settings") {
    navSettings.classList.add("active");
    pageSettings.classList.add("active");
    loadSettings();
  } else if (tab === "admin") {'''
new = '''  } else if (tab === "settings") {
    // 设置已拆为独立子页（阶段二）
    location.href = "/settings";
  } else if (tab === "admin") {'''
assert a.count(old) == 1, "switchTab settings 分支异常"
a = a.replace(old, new)

write(ap, a)
print("app.js OK")

# ---------- index.html ----------
ip = r"C:\Users\Administrator\Desktop\11\frontend\index.html"
h = read(ip)

si = h.index("          <!-- 设置页面 -->")
prev = h.rindex("\n\n", 0, si)  # 回退到上一个空行
ei = h.index("          </section>", si) + len("          </section>\n")
h = h[:prev + 1] + h[ei:]
write(ip, h)
print("index.html OK, 删除", ei - prev - 1, "字符")
