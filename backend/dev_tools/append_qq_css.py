# -*- coding: utf-8 -*-
"""向 frontend/css/desktop.css 追加问卷页样式（UTF-8 写入，幂等：已存在则不重复追加）。

用法：cd backend && python dev_tools/append_qq_css.py
"""
import io
import os

CSS = """

/* ══════════════ 科研问卷页（/questionnaire） ══════════════ */
.qq-progress-note {
  margin: 4px 0 18px;
}
.qq-progress-note-inner {
  display: inline-block;
  padding: 9px 16px;
  border-radius: var(--radius);
  background: var(--primary-light);
  color: var(--primary-hover);
  font-size: 13.5px;
  border: 1px solid rgba(99, 102, 241, 0.18);
}

/* ── 问卷卡片列表 ── */
.qq-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}
.qq-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 18px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: box-shadow var(--transition), border-color var(--transition);
}
.qq-card:hover {
  box-shadow: var(--shadow-md);
  border-color: rgba(99, 102, 241, 0.35);
}
.qq-card.is-done {
  background: #fbfcff;
}
.qq-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.qq-card-name {
  font-size: 15.5px;
  font-weight: 700;
  color: var(--text);
}
.qq-badge {
  flex: none;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 999px;
  white-space: nowrap;
}
.qq-badge.done {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}
.qq-badge.todo {
  background: #fffbeb;
  color: #b45309;
  border: 1px solid #fde68a;
}
.qq-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  font-size: 12.5px;
  color: var(--text-muted);
}
.qq-card-timing,
.qq-card-time {
  font-size: 12.5px;
  color: var(--text-muted);
}
.qq-card-time {
  color: #047857;
}
.qq-card-actions {
  margin-top: 4px;
}

/* ── 提交记录 ── */
.qq-section-title {
  margin: 30px 0 12px;
  font-size: 16px;
  color: var(--text);
}
.qq-history {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.qq-history-item {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-left: 3px solid var(--primary);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
}
.qq-history-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}
.qq-history-meta {
  font-size: 12.5px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* ── 答题视图 ── */
.qq-form-head {
  margin-bottom: 10px;
}
.qq-form-title {
  font-size: 21px;
  font-weight: 700;
  color: var(--text);
}
.qq-form-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin-top: 6px;
  font-size: 12.5px;
  color: var(--text-muted);
}
.qq-intro {
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 16px;
  font-size: 13px;
  line-height: 1.75;
  color: #475569;
  margin: 14px 0 18px;
}
.qq-intro-title {
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}
.qq-pagebar {
  position: sticky;
  top: 64px;
  z-index: 5;
  background: var(--bg);
  padding: 8px 0 10px;
}
.qq-progress-track {
  height: 6px;
  border-radius: 999px;
  background: var(--border);
  overflow: hidden;
}
.qq-progress-fill {
  height: 100%;
  width: 0;
  border-radius: 999px;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  transition: width var(--transition);
}
.qq-progress-text {
  margin-top: 6px;
  font-size: 12.5px;
  color: var(--text-muted);
}
.qq-page-title {
  margin: 8px 0 14px;
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

/* ── 题目 ── */
.qq-q {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  margin-bottom: 12px;
}
.qq-q-missing {
  border-color: var(--danger);
  background: var(--danger-light);
}
.qq-q-text {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text);
  margin-bottom: 10px;
}
.qq-q-no {
  display: inline-block;
  min-width: 34px;
  font-weight: 700;
  color: var(--primary);
}
.qq-req {
  color: var(--danger);
  margin-left: 4px;
}
.qq-opt {
  color: var(--text-muted);
  font-size: 12.5px;
  margin-left: 4px;
}
.qq-scale-hint {
  font-size: 12.5px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

/* ── 矩阵量表 ── */
.qq-matrix-wrap {
  overflow-x: auto;
}
.qq-matrix {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.qq-matrix th {
  padding: 6px 4px;
  font-weight: 600;
  color: var(--text-muted);
  font-size: 12.5px;
  text-align: center;
  min-width: 46px;
}
.qq-scale-cap {
  display: block;
  font-size: 11px;
  font-weight: 400;
}
.qq-matrix td {
  padding: 7px 6px;
  border-top: 1px solid var(--border);
  text-align: center;
}
.qq-row-label {
  text-align: left;
  color: var(--text);
  line-height: 1.6;
  min-width: 220px;
}
.qq-block-row td {
  background: #f8fafc;
  font-weight: 700;
  color: var(--primary-hover);
  font-size: 12.5px;
  text-align: left;
  padding: 6px 8px;
}
.qq-radio {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.qq-radio input {
  width: 17px;
  height: 17px;
  accent-color: var(--primary);
  cursor: pointer;
  margin: 0;
}

/* ── 单选 / 填空 ── */
.qq-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
}
.qq-option {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13.5px;
  color: var(--text);
  cursor: pointer;
}
.qq-option input {
  width: 16px;
  height: 16px;
  accent-color: var(--primary);
  cursor: pointer;
}
.qq-input,
.qq-textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 9px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 13.5px;
  font-family: inherit;
  color: var(--text);
  background: #fff;
}
.qq-input:focus,
.qq-textarea:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
}
.qq-textarea {
  resize: vertical;
  line-height: 1.7;
}
.qq-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin: 20px 0 40px;
}
.qq-hint {
  font-size: 12.5px;
  color: var(--text-muted);
}

/* ── 已提交回顾 ── */
.qq-done-card {
  background: var(--card-bg);
  border: 1px solid #a7f3d0;
  border-radius: var(--radius);
  padding: 26px 20px;
  text-align: center;
  box-shadow: var(--shadow-sm);
}
.qq-done-icon {
  font-size: 40px;
  line-height: 1;
}
.qq-done-title {
  margin-top: 10px;
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
}
.qq-done-sub {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-muted);
}
.qq-done-page {
  margin: 22px 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  font-weight: 700;
  color: var(--primary-hover);
}
.qq-done-q {
  margin: 10px 0 6px;
  font-size: 13.5px;
  color: var(--text);
  line-height: 1.65;
}
.qq-done-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-bottom: 12px;
}
.qq-done-table td {
  padding: 6px 8px;
  border-top: 1px solid var(--border);
}
.qq-done-val {
  text-align: center;
  font-weight: 700;
  color: var(--primary-hover);
  width: 70px;
}
.qq-done-text {
  font-size: 13.5px;
  color: #475569;
  background: #f8fafc;
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  margin-bottom: 12px;
  line-height: 1.7;
}

@media (max-width: 768px) {
  .qq-row-label {
    min-width: 130px;
    font-size: 12.5px;
  }
  .qq-matrix th {
    min-width: 38px;
  }
  .qq-cards {
    grid-template-columns: 1fr;
  }
}
"""


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, "frontend", "css", "desktop.css")
    with io.open(path, encoding="utf-8") as f:
        text = f.read()
    if "科研问卷页（/questionnaire）" in text:
        print("问卷样式已存在，跳过")
        return 0
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.rstrip("\n") + "\n" + CSS)
    print(f"已追加问卷样式，{len(CSS)} 字符 → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
