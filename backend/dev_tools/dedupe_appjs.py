# -*- coding: utf-8 -*-
"""代码整理：index.html 加载 common.js；app.js 删除与 common.js 重复的定义（$ / $$ / esc / fmtTime /
showToast / handleApiError / unlockAudio / clearSpeaking / speakWord / runStreamToPreview / currentUsername / isAdmin）。
"""
import io, re

def read(p):
    return io.open(p, encoding="utf-8").read()

def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)

# ---------- index.html：加载 common.js（app.js 之前） ----------
ip = r"C:\Users\Administrator\Desktop\11\frontend\index.html"
h = read(ip)
old = '<script src="/js/api.js?v={api_version}"></script>\n    <script src="/js/app.js?v={app_version}"></script>'
assert h.count(old) == 1, "index.html script 引用异常"
h = h.replace(old, '<script src="/js/api.js?v={api_version}"></script>\n    <script src="/js/common.js?v={app_version}"></script>\n    <script src="/js/app.js?v={app_version}"></script>')
write(ip, h)
print("index.html OK：已加载 common.js")

# ---------- app.js：删除重复定义 ----------
ap = r"C:\Users\Administrator\Desktop\11\frontend\js\app.js"
a = read(ap)

# 1) 删除 $ / $$ 定义
old = 'const $ = (sel) => document.querySelector(sel);\nconst $$ = (sel) => document.querySelectorAll(sel);\n'
assert a.count(old) == 1, "$ 定义异常"
a = a.replace(old, "")

# 2) 删除 currentUsername / isAdmin 声明
for decl in ['let currentUsername = "";\n', "let isAdmin = false;\n"]:
    assert a.count(decl) == 1, f"声明异常: {decl}"
    a = a.replace(decl, "")

# 3) 删除函数定义（配对大括号提取）
def remove_func(src, name, pattern=None):
    if pattern is None:
        pattern = r"function " + name + r"\([^)]*\) \{"
    m = re.search(pattern, src)
    if not m:
        raise AssertionError(f"未找到函数: {name}")
    start = m.start()
    i = src.index("{", start)
    depth = 0
    j = i
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    # 删除函数 + 其后跟随的注释行/空行（最多两个空行）
    end = j + 1
    while end < len(src) and src[end] in " \t\r\n":
        end += 1
    # 保留一个空行分隔
    return src[:start].rstrip() + "\n\n" + src[end:].lstrip("\n"), end - start

for fn in ["esc", "fmtTime", "showToast", "handleApiError", "unlockAudio",
           "clearSpeaking", "speakWord"]:
    a, _ = remove_func(a, fn)
    print(f"删除 function {fn}")

# runStreamToPreview 是 async function
a, _ = remove_func(a, "runStreamToPreview", pattern=r"async function runStreamToPreview\([^)]*\) \{")
print("删除 async function runStreamToPreview")

write(ap, a)
print("app.js OK")
