# -*- coding: utf-8 -*-
"""管理页拆分收尾：app.js 移除 pageAdmin + admin 逻辑 + switchTab 跳转；index.html 删除 page-admin section。"""
import io

def read(p):
    return io.open(p, encoding="utf-8").read()

def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)

# ---------- app.js ----------
ap = r"C:\Users\Administrator\Desktop\11\frontend\js\app.js"
a = read(ap)

# 1) 删 pageAdmin 变量行
old = 'const pageAdmin = $("#page-admin");\n'
assert a.count(old) == 1, "pageAdmin 变量行数量异常"
a = a.replace(old, "")

# 2) pages 数组移除 pageAdmin
old = "const pages = [pageHome, pageSaved, pageAdmin];"
assert a.count(old) == 1, "pages 数组异常"
a = a.replace(old, "const pages = [pageHome, pageSaved];")

# 3) switchTab admin 分支改为跳转
old = '''  } else if (tab === "admin") {
    navAdmin.classList.add("active");
    pageAdmin.classList.add("active");
    loadAdmin();
  }
}'''
new = '''  } else if (tab === "admin") {
    // 管理已拆为独立子页（阶段二）
    location.href = "/admin";
  }
}'''
assert a.count(old) == 1, "switchTab admin 分支异常"
a = a.replace(old, new)

# 4) 删除管理员逻辑区段（// ===== 管理员页 ===== 到 // ===== 初始化 =====）
start_marker = "// ===== 管理员页 ====="
end_marker = "// ===== 初始化 ====="
si = a.index(start_marker)
ei = a.index(end_marker)
a = a[:si] + a[ei:]
print("admin 逻辑删除:", ei - si, "字符")

write(ap, a)
print("app.js OK")

# ---------- index.html ----------
ip = r"C:\Users\Administrator\Desktop\11\frontend\index.html"
h = read(ip)

si = h.index("          <!-- 管理员页面 -->")
prev = h.rindex("\n\n", 0, si)
ei = h.index("          </section>", si) + len("          </section>\n")
h = h[:prev + 1] + h[ei:]
write(ip, h)
print("index.html OK, 删除", ei - prev - 1, "字符")
