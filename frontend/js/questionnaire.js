/**
 * 科研问卷页逻辑。
 *
 * 三个视图：
 *   1. 列表视图（#qq-list-view）—— 选卷，显示「未填写 / 已完成」
 *   2. 答题视图（#qq-form-view）—— 逐页作答（矩阵量表 / 单选 / 填空 / 多行文本）
 *   3. 已提交视图（#qq-done-view）—— 回顾自己的作答
 *
 * 题目定义全部来自后端（app/questionnaires.py），前端只渲染不硬编码措辞，
 * 避免前后端题目文字不一致导致数据不可用。
 */

// ── DOM ──
const qqListView = $("#qq-list-view");
const qqFormView = $("#qq-form-view");
const qqDoneView = $("#qq-done-view");
const qqCards = $("#qq-cards");
const qqProgressNote = $("#qq-progress-note");
const qqHistory = $("#qq-history");
const qqHistoryTitle = $("#qq-history-title");
const qqFormTitle = $("#qq-form-title");
const qqFormMeta = $("#qq-form-meta");
const qqIntro = $("#qq-intro");
const qqPageBody = $("#qq-page-body");
const qqProgressFill = $("#qq-progress-fill");
const qqProgressText = $("#qq-progress-text");
const qqPrevBtn = $("#qq-prev");
const qqNextBtn = $("#qq-next");
const qqSubmitBtn = $("#qq-submit");
const qqQuitBtn = $("#qq-quit");
const qqHint = $("#qq-hint");
const qqDoneTitle = $("#qq-done-title");
const qqDoneSub = $("#qq-done-sub");
const qqDoneAnswers = $("#qq-done-answers");

// ── 状态 ──
let qqList = [];          // 问卷列表
let qqCurrent = null;     // 当前作答的问卷定义
let qqAnswers = {};       // 条目 key → 作答值
let qqPageIndex = 0;      // 当前页
let qqStartedAt = 0;      // 开始作答时间（算用时）

/** 由 dom id 生成安全的元素 id 片段。 */
function qqSafe(s) {
  return String(s).replace(/[^A-Za-z0-9_-]/g, "_");
}

// ────────────────────────── 列表视图 ──────────────────────────

async function loadList() {
  qqCards.innerHTML = '<div class="empty-state"><p>加载中...</p></div>';
  try {
    const data = await api.questionnaires();
    qqList = data.questionnaires || [];
    renderList(data);
    loadHistory();
  } catch (err) {
    qqCards.innerHTML = `<div class="empty-state"><p>加载失败：${esc(err.message)}</p></div>`;
  }
}

function renderList(data) {
  const done = data.submitted_count || 0;
  qqProgressNote.innerHTML =
    `<div class="qq-progress-note-inner">已完成 <b>${done}</b> / ${data.total || qqList.length} 份` +
    (done === qqList.length ? " 🎉 全部完成，感谢参与！" : "　请点开尚未完成的问卷作答") +
    `</div>`;

  qqCards.innerHTML = qqList
    .map((q) => {
      const badge = q.submitted
        ? '<span class="qq-badge done">✅ 已完成</span>'
        : '<span class="qq-badge todo">⏳ 未填写</span>';
      const time = q.submitted_at
        ? `<div class="qq-card-time">提交于 ${esc(fmtTime(q.submitted_at))}` +
          (q.duration_sec ? `　用时 ${Math.max(1, Math.round(q.duration_sec / 60))} 分钟` : "") +
          "</div>"
        : "";
      const btn = q.submitted
        ? `<button class="btn btn-outline btn-sm" data-qq-view="${esc(q.code)}">查看我的作答</button>`
        : `<button class="btn btn-primary btn-sm" data-qq-start="${esc(q.code)}">开始填写</button>`;
      return `
        <div class="qq-card ${q.submitted ? "is-done" : ""}">
          <div class="qq-card-head">
            <div class="qq-card-name">卷${esc(q.number)} ${esc(q.name)}</div>
            ${badge}
          </div>
          <div class="qq-card-meta">
            <span>👥 ${esc(q.audience)}</span>
            <span>⏱ ${q.minutes} 分钟</span>
            <span>📄 ${q.page_count} 页 / ${q.item_count} 题</span>
          </div>
          <div class="qq-card-timing">填写时机：${esc(q.timing)}</div>
          ${time}
          <div class="qq-card-actions">${btn}</div>
        </div>`;
    })
    .join("");

  qqCards.querySelectorAll("[data-qq-start]").forEach((b) => {
    b.addEventListener("click", () => startFill(b.dataset.qqStart));
  });
  qqCards.querySelectorAll("[data-qq-view]").forEach((b) => {
    b.addEventListener("click", () => showDone(b.dataset.qqView));
  });
}

async function loadHistory() {
  try {
    const data = await api.questionnaireHistory();
    const items = data.items || [];
    if (!items.length) {
      qqHistoryTitle.style.display = "none";
      qqHistory.innerHTML = "";
      return;
    }
    qqHistoryTitle.style.display = "block";
    qqHistory.innerHTML = items
      .map(
        (it) => `
        <div class="qq-history-item">
          <div class="qq-history-name">卷${esc(it.number)} ${esc(it.name)}</div>
          <div class="qq-history-meta">
            提交于 ${esc(fmtTime(it.submitted_at))}
            ${it.duration_sec ? `　用时 ${Math.max(1, Math.round(it.duration_sec / 60))} 分钟` : ""}
          </div>
        </div>`
      )
      .join("");
  } catch (err) {
    qqHistoryTitle.style.display = "none";
  }
}

// ────────────────────────── 答题视图 ──────────────────────────

async function startFill(code) {
  qqFormView.style.display = "block";
  qqListView.style.display = "none";
  qqDoneView.style.display = "none";
  qqPageBody.innerHTML = '<div class="empty-state"><p>加载题目中...</p></div>';
  try {
    const data = await api.questionnaireGet(code);
    if (data.submitted) {
      showDone(code, data);
      return;
    }
    qqCurrent = data.questionnaire;
    qqAnswers = {};
    qqPageIndex = 0;
    qqStartedAt = Date.now();
    renderFormHead();
    renderPage();
  } catch (err) {
    qqPageBody.innerHTML = `<div class="empty-state"><p>加载失败：${esc(err.message)}</p></div>`;
  }
}

function renderFormHead() {
  const q = qqCurrent;
  qqFormTitle.textContent = `卷${q.number} ${q.name}`;
  qqFormMeta.innerHTML =
    `<span>👥 ${esc(q.audience)}</span><span>⏱ 约 ${q.minutes} 分钟</span>` +
    `<span>📄 ${q.pages.length} 页</span><span>🔒 提交后不可修改</span>`;
  qqIntro.innerHTML = `<div class="qq-intro-title">填写说明</div>` +
    esc(q.intro || "").replace(/\n/g, "<br>");
}

function renderPage() {
  const q = qqCurrent;
  const page = q.pages[qqPageIndex];
  const total = q.pages.length;

  qqProgressFill.style.width = `${((qqPageIndex + 1) / total) * 100}%`;
  qqProgressText.textContent = `第 ${qqPageIndex + 1} / ${total} 页 · ${page.title}`;

  let html = `<div class="qq-page-title">${esc(page.title)}</div>`;
  page.items.forEach((item, idx) => {
    html += renderItem(item, `${qqPageIndex + 1}-${idx + 1}`);
  });
  qqPageBody.innerHTML = html;
  bindItemEvents();

  qqPrevBtn.style.display = qqPageIndex === 0 ? "none" : "inline-flex";
  const last = qqPageIndex === total - 1;
  qqNextBtn.style.display = last ? "none" : "inline-flex";
  qqSubmitBtn.style.display = last ? "inline-flex" : "none";
  qqHint.textContent = last ? "提交后不可修改，请确认无误" : "带 * 的题目为必答";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderItem(item, no) {
  const required = item.required ? '<span class="qq-req">*</span>' : '<span class="qq-opt">（选填）</span>';
  const head = `<div class="qq-q-text"><span class="qq-q-no">${no}</span>${esc(item.text)}${required}</div>`;

  if (item.type === "matrix") {
    const scale = item.scale || {};
    const labels = scale.labels || {};
    const values = [];
    for (let v = scale.min; v <= scale.max; v += 1) values.push(v);
    const headCells = values
      .map((v) => `<th>${labels[v] ? `<span class="qq-scale-cap">${esc(labels[v])}</span>` : ""}${v}</th>`)
      .join("");

    const renderRows = (rows, startIdx) =>
      rows
        .map((row, i) => {
          const key = `${item.key}_r${startIdx + i}`;
          const cells = values
            .map(
              (v) => `<td><label class="qq-radio"><input type="radio" name="${qqSafe(key)}" data-qq-key="${esc(key)}" value="${v}"${
                String(qqAnswers[key]) === String(v) ? " checked" : ""
              }><span></span></label></td>`
            )
            .join("");
          return `<tr><td class="qq-row-label">${esc(row)}</td>${cells}</tr>`;
        })
        .join("");

    let body = "";
    if (item.blocks && item.blocks.length) {
      // 行号跨块连续且从 1 开始（后端与必答校验都按 r1..rN 编号）
      let offset = 1;
      item.blocks.forEach((block) => {
        body += `<tr class="qq-block-row"><td colspan="${values.length + 1}">${esc(block.title)}</td></tr>`;
        body += renderRows(block.rows, offset);
        offset += block.rows.length;
      });
    } else {
      body = renderRows(item.rows, 1);
    }

    const scaleHint =
      scale.min_label && scale.max_label
        ? `<div class="qq-scale-hint">${scale.min} = ${esc(scale.min_label)} → ${scale.max} = ${esc(scale.max_label)}</div>`
        : "";
    return `<div class="qq-q" data-qq-item="${esc(item.key)}">${head}${scaleHint}
      <div class="qq-matrix-wrap"><table class="qq-matrix"><thead><tr><th></th>${headCells}</tr></thead>
      <tbody>${body}</tbody></table></div></div>`;
  }

  if (item.type === "radio") {
    const opts = (item.options || [])
      .map(
        (o) =>
          `<label class="qq-option"><input type="radio" name="${qqSafe(item.key)}" data-qq-key="${esc(item.key)}" value="${esc(o)}"${
            String(qqAnswers[item.key]) === String(o) ? " checked" : ""
          }><span>${esc(o)}</span></label>`
      )
      .join("");
    return `<div class="qq-q" data-qq-item="${esc(item.key)}">${head}<div class="qq-options">${opts}</div></div>`;
  }

  if (item.type === "textarea") {
    return `<div class="qq-q" data-qq-item="${esc(item.key)}">${head}
      <textarea class="qq-textarea" data-qq-input="${esc(item.key)}" rows="3"
        placeholder="${esc(item.placeholder || "")}">${esc(qqAnswers[item.key] || "")}</textarea></div>`;
  }

  return `<div class="qq-q" data-qq-item="${esc(item.key)}">${head}
    <input type="text" class="qq-input" data-qq-input="${esc(item.key)}"
      placeholder="${esc(item.placeholder || "")}" value="${esc(qqAnswers[item.key] || "")}" /></div>`;
}

/** 绑定作答事件：即时把作答写入 qqAnswers，避免切页丢失。 */
function bindItemEvents() {
  qqPageBody.querySelectorAll('input[type="radio"][data-qq-key]').forEach((el) => {
    el.addEventListener("change", () => {
      qqAnswers[el.dataset.qqKey] = el.value;
      el.closest(".qq-q")?.classList.remove("qq-q-missing");
    });
  });
  qqPageBody.querySelectorAll("[data-qq-input]").forEach((el) => {
    el.addEventListener("input", () => {
      qqAnswers[el.dataset.qqInput] = el.value;
      el.closest(".qq-q")?.classList.remove("qq-q-missing");
    });
  });
}

/** 当前页必答校验；返回未答条目 key 列表。 */
function missingOnPage() {
  const page = qqCurrent.pages[qqPageIndex];
  const missing = [];
  page.items.forEach((item) => {
    if (!item.required) return;
    if (item.type === "matrix") {
      for (let i = 1; i <= item.rows.length; i += 1) {
        const key = `${item.key}_r${i}`;
        if (!qqAnswers[key]) missing.push(key);
      }
    } else if (!qqAnswers[item.key]) {
      missing.push(item.key);
    }
  });
  return missing;
}

function highlightMissing(keys) {
  const set = new Set(keys);
  qqPageBody.querySelectorAll(".qq-q").forEach((el) => {
    const itemKey = el.dataset.qqItem;
    const hit = [...set].some((k) => k === itemKey || k.startsWith(`${itemKey}_r`));
    el.classList.toggle("qq-q-missing", hit);
  });
  const first = qqPageBody.querySelector(".qq-q-missing");
  if (first) first.scrollIntoView({ behavior: "smooth", block: "center" });
}

// ────────────────────────── 提交与回顾 ──────────────────────────

async function submitForm() {
  const missing = missingOnPage();
  if (missing.length) {
    highlightMissing(missing);
    showToast(`本页还有 ${missing.length} 题未作答`, "error");
    return;
  }
  if (!window.confirm("提交后不可修改，确认提交问卷？")) return;

  qqSubmitBtn.disabled = true;
  qqSubmitBtn.textContent = "提交中...";
  try {
    const duration = Math.round((Date.now() - qqStartedAt) / 1000);
    await api.questionnaireSubmit(qqCurrent.code, qqAnswers, duration);
    showToast("问卷提交成功，感谢参与！", "success");
    await loadList();
    showDone(qqCurrent.code);
  } catch (err) {
    handleApiError(err, "提交失败");
  } finally {
    qqSubmitBtn.disabled = false;
    qqSubmitBtn.textContent = "提交问卷";
  }
}

async function showDone(code, preloaded) {
  qqListView.style.display = "none";
  qqFormView.style.display = "none";
  qqDoneView.style.display = "block";
  qqDoneAnswers.innerHTML = '<div class="empty-state"><p>加载中...</p></div>';
  try {
    const data = preloaded || (await api.questionnaireGet(code));
    const q = data.questionnaire;
    const answers = data.my_answers || {};
    qqDoneTitle.textContent = `卷${q.number} ${q.name} · 已提交`;
    qqDoneSub.textContent = data.submitted_at
      ? `提交时间：${fmtTime(data.submitted_at)}` +
        (data.duration_sec ? `　用时 ${Math.max(1, Math.round(data.duration_sec / 60))} 分钟` : "")
      : "";

    let html = "";
    q.pages.forEach((page, pi) => {
      html += `<div class="qq-done-page">第 ${pi + 1} 页 · ${esc(page.title)}</div>`;
      page.items.forEach((item) => {
        if (item.type === "matrix") {
          const rows = item.rows
            .map((row, i) => {
              const v = answers[`${item.key}_r${i + 1}`];
              return `<tr><td class="qq-row-label">${esc(row)}</td>
                <td class="qq-done-val">${v === undefined || v === "" ? "—" : esc(v)}</td></tr>`;
            })
            .join("");
          html += `<div class="qq-done-q">${esc(item.text)}</div>
            <table class="qq-done-table">${rows}</table>`;
        } else {
          const v = answers[item.key];
          html += `<div class="qq-done-q">${esc(item.text)}</div>
            <div class="qq-done-text">${v === undefined || v === "" ? "—" : esc(v).replace(/\n/g, "<br>")}</div>`;
        }
      });
    });
    qqDoneAnswers.innerHTML = html;
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    qqDoneAnswers.innerHTML = `<div class="empty-state"><p>加载失败：${esc(err.message)}</p></div>`;
  }
}

function backToList() {
  qqFormView.style.display = "none";
  qqDoneView.style.display = "none";
  qqListView.style.display = "block";
  qqCurrent = null;
  qqAnswers = {};
  loadList();
}

// ────────────────────────── 事件与入口 ──────────────────────────

qqNextBtn.addEventListener("click", () => {
  const missing = missingOnPage();
  if (missing.length) {
    highlightMissing(missing);
    showToast(`本页还有 ${missing.length} 题未作答`, "error");
    return;
  }
  qqPageIndex = Math.min(qqPageIndex + 1, qqCurrent.pages.length - 1);
  renderPage();
});

qqPrevBtn.addEventListener("click", () => {
  qqPageIndex = Math.max(qqPageIndex - 1, 0);
  renderPage();
});

qqSubmitBtn.addEventListener("click", submitForm);
qqQuitBtn.addEventListener("click", () => {
  if (qqCurrent && Object.keys(qqAnswers).length && !window.confirm("返回将丢失本页已填内容，确定吗？")) return;
  backToList();
});
$("#qq-done-back").addEventListener("click", backToList);

initPage().then((ok) => {
  if (ok) loadList();
});
