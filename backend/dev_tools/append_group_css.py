# -*- coding: utf-8 -*-
"""追加实验页分组学习样式与假名测试题样式。"""
import io

DESKTOP = r"C:\Users\Administrator\Desktop\11\frontend\css\desktop.css"
MOBILE = r"C:\Users\Administrator\Desktop\11\frontend\css\mobile.css"

CSS = """

/* 学习阶段：两组分区展示 */
.exp-grid { display: block; }
.exp-group { margin-bottom: 26px; }
.exp-group:last-child { margin-bottom: 0; }
.exp-group-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.exp-group-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  font-weight: 700;
  padding: 5px 12px;
  border-radius: 999px;
}
.exp-group-badge.mm { background: linear-gradient(135deg, #eef2ff, #f5f3ff); color: var(--primary); border: 1px solid #c7d2fe; }
.exp-group-badge.plain { background: var(--bg); color: var(--text-muted); border: 1px solid var(--border); }
.exp-group-count { font-size: 12px; color: var(--text-muted); }
.exp-group-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 14px;
}

/* 测试题：只显示假名读音 */
.exp-quiz-kana-main {
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.02em;
}
"""

MOBILE_CSS = """
/* 实验分组（移动端） */
.exp-group-grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
.exp-quiz-kana-main { font-size: 20px; }
"""

with io.open(DESKTOP, "a", encoding="utf-8", newline="\n") as f:
    f.write(CSS)
with io.open(MOBILE, "a", encoding="utf-8", newline="\n") as f:
    f.write(MOBILE_CSS)
print("分组学习与假名测试样式已追加")
