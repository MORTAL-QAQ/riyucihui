# -*- coding: utf-8 -*-
"""追加自主生成耗时提示的警告样式。"""
import io

DESKTOP = r"C:\Users\Administrator\Desktop\11\frontend\css\desktop.css"

CSS = """

/* 自主生成模式耗时提示（警告样式） */
.exp-preset-note.warn {
  color: #b45309;
  background: #fffbeb;
  border-color: #fcd34d;
  line-height: 1.8;
}
"""

with io.open(DESKTOP, "a", encoding="utf-8", newline="\n") as f:
    f.write(CSS)
print("警告提示样式已追加")
