# -*- coding: utf-8 -*-
"""成就页拆分收尾：app.js 移除 pageAchievement/loadAchievements + switchTab 跳转；index.html 删除 page-achievement section。"""
import io

def read(p):
    return io.open(p, encoding="utf-8").read()

def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)

# ---------- app.js ----------
ap = r"C:\Users\Administrator\Desktop\11\frontend\js\app.js"
a = read(ap)

# 1) 删 pageAchievement 变量行
old = 'const pageAchievement = $("#page-achievement");\n'
assert a.count(old) == 1, "pageAchievement 变量行数量异常"
a = a.replace(old, "")

# 2) pages 数组移除 pageAchievement
old = "const pages = [pageHome, pageSaved, pageAchievement, pageAdmin];"
assert a.count(old) == 1, "pages 数组异常"
a = a.replace(old, "const pages = [pageHome, pageSaved, pageAdmin];")

# 3) switchTab achievement 分支改为跳转
old = '''  } else if (tab === "achievement") {
    navAchievement.classList.add("active");
    pageAchievement.classList.add("active");
    withLoader("achievement", loadAchievements);
  } else if (tab === "settings") {'''
new = '''  } else if (tab === "achievement") {
    // 成就已拆为独立子页（阶段二）
    location.href = "/achievement";
  } else if (tab === "settings") {'''
assert a.count(old) == 1, "switchTab achievement 分支异常"
a = a.replace(old, new)

# 4) 删除 loadAchievements 函数（// ── 成就页 ── 到 updateStudyBadge 之前）
start_marker = "// ── 成就页 ──"
end_marker = "async function updateStudyBadge()"
si = a.index(start_marker)
ei = a.index(end_marker)
a = a[:si] + a[ei:]
print("loadAchievements 删除:", ei - si, "字符")

write(ap, a)
print("app.js OK")

# ---------- index.html ----------
ip = r"C:\Users\Administrator\Desktop\11\frontend\index.html"
h = read(ip)

si = h.index("          <!-- 成就页面 -->")
prev = h.rindex("\n\n", 0, si)
ei = h.index("          </section>", si) + len("          </section>\n")
h = h[:prev + 1] + h[ei:]
write(ip, h)
print("index.html OK, 删除", ei - prev - 1, "字符")
