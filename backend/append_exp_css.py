# -*- coding: utf-8 -*-
"""追加实验页样式到 desktop.css / mobile.css（UTF-8 安全）。"""
import io

DESKTOP = r"C:\Users\Administrator\Desktop\11\frontend\css\desktop.css"
MOBILE = r"C:\Users\Administrator\Desktop\11\frontend\css\mobile.css"

CSS = """

/* ═══════════════════════════════════════════════════════════════════
   多模态记忆实验页
   ═══════════════════════════════════════════════════════════════════ */
.exp-panel {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px 26px;
  box-shadow: var(--shadow-sm);
  margin-bottom: 20px;
}
.exp-config-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.exp-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  min-width: 72px;
}
.exp-input {
  flex: 1;
  min-width: 220px;
  padding: 10px 14px;
  font-size: 14px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  color: var(--text);
  outline: none;
}
.exp-input:focus { border-color: var(--primary); }
.exp-select {
  padding: 10px 14px;
  font-size: 14px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  color: var(--text);
  outline: none;
}
.exp-note {
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-muted);
  background: var(--primary-light);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  margin-bottom: 18px;
}
.exp-hint { font-size: 13px; color: var(--text-muted); margin-left: 12px; }
.exp-section-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin: 24px 0 12px;
}

/* 进度条 */
.exp-progress-bar { margin-bottom: 18px; }
.exp-progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text);
  font-weight: 600;
  margin-bottom: 8px;
}
.exp-progress-track {
  height: 8px;
  background: var(--border);
  border-radius: 4px;
  overflow: hidden;
}
.exp-progress-fill {
  height: 100%;
  width: 0;
  background: linear-gradient(90deg, var(--primary), #8b5cf6);
  transition: width 0.3s ease;
}
.exp-progress-hint { font-size: 12px; color: var(--text-muted); margin-top: 6px; }

/* 学习卡片 */
.exp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 14px;
}
.exp-card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  background: var(--card-bg);
  transition: box-shadow var(--transition), border-color var(--transition);
}
.exp-card:hover { box-shadow: var(--shadow-md); border-color: var(--primary); }
.exp-card-mm { border-left: 4px solid var(--primary); }
.exp-card-plain { border-left: 4px solid var(--border); }
.exp-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.exp-card-jp { font-size: 20px; font-weight: 700; color: var(--text); }
.exp-speak {
  border: 1px solid var(--border);
  background: transparent;
  border-radius: 8px;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 14px;
}
.exp-speak:hover { border-color: var(--primary); }
.exp-card-kana { font-size: 13px; color: var(--text-muted); margin-top: 2px; }
.exp-card-img {
  margin: 10px 0;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--bg);
  min-height: 90px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.exp-card-img img { width: 100%; height: auto; display: block; }
.exp-img-loading { font-size: 12px; color: var(--text-muted); padding: 30px 0; }
.exp-card-ex { font-size: 13px; color: var(--text); line-height: 1.7; margin-top: 6px; }
.exp-card-ex-cn { font-size: 12px; color: var(--text-muted); line-height: 1.6; margin-top: 2px; }

/* 测试题 */
.exp-test-list { display: flex; flex-direction: column; gap: 16px; }
.exp-quiz-item {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 18px;
}
.exp-quiz-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 12px; }
.exp-quiz-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px; height: 24px;
  border-radius: 50%;
  background: var(--primary-light);
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
}
.exp-quiz-jp { font-size: 20px; font-weight: 700; color: var(--text); }
.exp-quiz-kana { font-size: 13px; color: var(--text-muted); }
.exp-quiz-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}
.exp-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  transition: all var(--transition);
}
.exp-option:hover { border-color: var(--primary); background: var(--primary-light); }
.exp-option input { accent-color: var(--primary); }

/* 结果 */
.exp-result-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}
.exp-result-card {
  border-radius: var(--radius);
  padding: 20px 22px;
  text-align: center;
  border: 1px solid var(--border);
}
.exp-result-card.mm { background: linear-gradient(135deg, #eef2ff, #f5f3ff); border-color: #c7d2fe; }
.exp-result-card.plain { background: var(--bg); }
.exp-result-label { font-size: 14px; font-weight: 700; color: var(--text); }
.exp-result-rate {
  font-size: 34px;
  font-weight: 800;
  margin: 8px 0 4px;
  background: linear-gradient(135deg, var(--primary), #8b5cf6);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.exp-result-sub { font-size: 13px; color: var(--text); }
.exp-result-desc { font-size: 12px; color: var(--text-muted); margin-top: 6px; }
.exp-result-verdict {
  font-size: 14px;
  line-height: 1.9;
  color: var(--text);
  background: var(--primary-light);
  border-left: 4px solid var(--primary);
  border-radius: var(--radius-sm);
  padding: 14px 18px;
}
.exp-verdict-note { font-size: 12px; color: var(--text-muted); }
.exp-detail-table-wrap { overflow-x: auto; }
.exp-detail-table { font-size: 13px; }
.exp-ok { color: #16a34a; font-weight: 700; }
.exp-bad { color: var(--danger); font-weight: 700; }

/* 历史记录 */
.exp-history { display: flex; flex-direction: column; gap: 10px; }
.exp-history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  font-size: 13px;
}
.exp-history-main { display: flex; align-items: center; gap: 12px; }
.exp-history-topic { font-weight: 600; color: var(--text); }
.exp-history-time { color: var(--text-muted); font-size: 12px; }
.exp-history-scores { display: flex; gap: 10px; }
.exp-score { padding: 3px 10px; border-radius: 999px; font-size: 12px; }
.exp-score.mm { background: var(--primary-light); color: var(--primary); font-weight: 600; }
.exp-score.plain { background: var(--bg); color: var(--text-muted); }
.exp-history-pending { color: var(--text-muted); font-size: 12px; }
.exp-history-empty { color: var(--text-muted); font-size: 13px; padding: 12px 0; }
"""

MOBILE_CSS = """
/* 实验页（移动端） */
.exp-panel { padding: 18px 16px; }
.exp-grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
.exp-card-jp { font-size: 17px; }
.exp-quiz-jp { font-size: 17px; }
.exp-quiz-options { grid-template-columns: 1fr; }
.exp-result-rate { font-size: 28px; }
.exp-history-item { flex-direction: column; align-items: flex-start; }
"""

with io.open(DESKTOP, "a", encoding="utf-8", newline="\n") as f:
    f.write(CSS)
with io.open(MOBILE, "a", encoding="utf-8", newline="\n") as f:
    f.write(MOBILE_CSS)
print("实验页样式已追加到 desktop.css 与 mobile.css")
