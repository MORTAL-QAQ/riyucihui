# -*- coding: utf-8 -*-
"""保存页拆分收尾：app.js 移除 saved 逻辑 + switchTab 跳转；index.html 删除 page-saved section 与 content-modal。"""
import io

def read(p):
    return io.open(p, encoding="utf-8").read()

def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)

# ---------- app.js ----------
ap = r"C:\Users\Administrator\Desktop\11\frontend\js\app.js"
a = read(ap)

# 1) 删 pageSaved 变量行
old = 'const pageSaved = $("#page-saved");\n'
assert a.count(old) == 1, "pageSaved 变量行数量异常"
a = a.replace(old, "")

# 2) pages 数组移除 pageSaved
old = "const pages = [pageHome, pageSaved];"
assert a.count(old) == 1, "pages 数组异常"
a = a.replace(old, "const pages = [pageHome];")

# 3) switchTab saved 分支改为跳转
old = '''  } else if (tab === "saved") {
    navSaved.classList.add("active");
    pageSaved.classList.add("active");
    withLoader("saved", function() {
      return Promise.all([loadSavedEssays(), loadGrammarSaved(), loadClozeSaved()]);
    });
  } else if (tab === "achievement") {'''
new = '''  } else if (tab === "saved") {
    // 保存已拆为独立子页（阶段二）
    location.href = "/saved";
  } else if (tab === "achievement") {'''
assert a.count(old) == 1, "switchTab saved 分支异常"
a = a.replace(old, new)

# 4) 删除 essaySavedList/clozeSavedList 顶层引用
old = '''const essaySavedList = $("#essay-saved-list");
const essaySavedEmpty = $("#essay-saved-empty");

const clozeSavedList = $("#cloze-saved-list");
const clozeSavedEmpty = $("#cloze-saved-empty");

'''
assert a.count(old) == 1, "saved 顶层引用异常"
a = a.replace(old, "")

# 5) 删除保存列表渲染/模态窗/搜索/子标签区段（到 updateStudyBadge 之前）
start_marker = "// ── 保存列表通用渲染 + 模态窗 ──"
end_marker = "async function updateStudyBadge()"
si = a.index(start_marker)
ei = a.index(end_marker)
a = a[:si] + a[ei:]
print("保存渲染区段删除:", ei - si, "字符")

# 6) 删除 jlptBadge 定义（common.js 已有，app.js 内已无调用者）
old = '''function jlptBadge(level) {
  if (!level) return "";
  return `<span class="jlpt-badge ${esc(level)}">${esc(level)}</span>`;
}

'''
assert a.count(old) == 1, "jlptBadge 定义异常"
a = a.replace(old, "")

# 7) 删除 loadClozeSaved/renderClozePassageStatic/deleteSavedCloze/deleteSavedGrammar/viewSavedCloze 区段
start_marker = "async function loadClozeSaved() {"
end_marker = "/* ===== 移动端适配 ===== */"
si = a.index(start_marker)
ei = a.index(end_marker)
a = a[:si] + a[ei:]
print("完型保存区段删除:", ei - si, "字符")

write(ap, a)
print("app.js OK")

# ---------- index.html ----------
ip = r"C:\Users\Administrator\Desktop\11\frontend\index.html"
h = read(ip)

# 删除 page-saved section
si = h.index("          <!-- 我的保存页面 -->")
prev = h.rindex("\n\n", 0, si)
ei = h.index("          </section>", si) + len("          </section>\n")
h = h[:prev + 1] + h[ei:]
print("page-saved 删除:", ei - prev - 1, "字符")

# 删除 content-modal 模态窗
si = h.index("          <!-- 内容查看模态窗 -->")
prev = h.rindex("\n\n", 0, si)
ei = h.index("          </div>", si) + len("          </div>\n")
h = h[:prev + 1] + h[ei:]
print("content-modal 删除:", ei - prev - 1, "字符")

write(ip, h)
print("index.html OK")
