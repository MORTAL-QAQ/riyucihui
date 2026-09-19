# -*- coding: utf-8 -*-
"""追加管理页实验数据面板样式。"""
import io

DESKTOP = r"C:\Users\Administrator\Desktop\11\frontend\css\desktop.css"

CSS = """

/* 管理页 · 实验数据面板 */
.exp-admin-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}
.exp-admin-card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 18px;
  background: var(--card-bg);
}
.exp-admin-card.mm { background: linear-gradient(135deg, #eef2ff, #f5f3ff); border-color: #c7d2fe; }
.exp-admin-card.plain { background: var(--bg); }
.exp-admin-card.diff { border-color: var(--primary); }
.exp-admin-card-label { font-size: 12px; color: var(--text-muted); font-weight: 600; }
.exp-admin-card-value {
  font-size: 26px;
  font-weight: 800;
  margin: 6px 0 4px;
  color: var(--primary);
}
.exp-admin-card-sub { font-size: 12px; color: var(--text-muted); }
.exp-admin-table-wrap { overflow-x: auto; }
.exp-admin-table { font-size: 13px; width: 100%; }
"""

with io.open(DESKTOP, "a", encoding="utf-8", newline="\n") as f:
    f.write(CSS)
print("管理页实验样式已追加")
