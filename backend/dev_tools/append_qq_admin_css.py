# -*- coding: utf-8 -*-
"""向 frontend/css/desktop.css 追加「管理页问卷面板」样式（UTF-8，幂等）。

用法：cd backend && python dev_tools/append_qq_admin_css.py
"""
import io
import os

CSS = """

/* ══════════════ 管理页 · 问卷回答情况 ══════════════ */
.qq-admin-title {
  margin: 34px 0 12px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
  font-size: 16px;
  color: var(--text);
}
.qq-admin-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.qq-admin-label {
  font-size: 13px;
  color: var(--text-muted);
}
.qq-admin-select {
  padding: 7px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  background: #fff;
  color: var(--text);
  min-width: 240px;
}
.qq-admin-note {
  font-size: 12.5px;
  color: var(--text-muted);
}
.qq-admin-row {
  cursor: pointer;
}
.qq-admin-row:hover {
  background: var(--primary-light);
}
.qq-admin-detail td {
  background: #f8fafc;
  padding: 12px 14px;
}
.qq-score-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.qq-score-chip {
  font-size: 12px;
  padding: 3px 9px;
  border-radius: 999px;
  background: #eef2ff;
  color: var(--primary-hover);
  border: 1px solid rgba(99, 102, 241, 0.2);
  white-space: nowrap;
}
"""


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, "frontend", "css", "desktop.css")
    with io.open(path, encoding="utf-8") as f:
        text = f.read()
    if "管理页 · 问卷回答情况" in text:
        print("管理页问卷样式已存在，跳过")
        return 0
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.rstrip("\n") + "\n" + CSS)
    print(f"已追加管理页问卷样式，{len(CSS)} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
