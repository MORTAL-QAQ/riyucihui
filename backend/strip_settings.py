# -*- coding: utf-8 -*-
"""从 app.js 删除设置页区段。"""
path = r"C:\Users\Administrator\Desktop\11\frontend\js\app.js"
text = open(path, encoding="utf-8").read()

start_marker = "// ===== 设置页 ====="
end_marker = "const essaySavedList = $(\"#essay-saved-list\");"
si = text.index(start_marker)
ei = text.index(end_marker)
text = text[:si] + text[ei:]
print("设置区段删除:", ei - si, "字符")

open(path, "w", encoding="utf-8", newline="\n").write(text)
print("done")
