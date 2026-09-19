# -*- coding: utf-8 -*-
"""追加预置套题相关样式。"""
import io

DESKTOP = r"C:\Users\Administrator\Desktop\11\frontend\css\desktop.css"

CSS = """

/* 预置实验套题选择 */
.exp-preset-note {
  font-size: 13px;
  color: #16a34a;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  margin-bottom: 16px;
}
"""

with io.open(DESKTOP, "a", encoding="utf-8", newline="\n") as f:
    f.write(CSS)
print("套题样式已追加")
