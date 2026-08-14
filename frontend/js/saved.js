/**
 * 我的保存独立子页逻辑（阶段二多页架构）
 * 依赖：api.js + common.js（$ / esc / escHtml / jlptBadge / showToast / initPage）
 */

// ── DOM 引用 ──
const essaySavedList = $("#essay-saved-list");
const essaySavedEmpty = $("#essay-saved-empty");
const clozeSavedList = $("#cloze-saved-list");
const clozeSavedEmpty = $("#cloze-saved-empty");
const grammarSavedList = $("#grammar-saved-list");
const grammarSavedEmpty = $("#grammar-saved-empty");

// ── 保存列表通用渲染 + 模态窗 ──
let savedItemsCache = { essay: [], cloze: [], grammar: [] };
let savedModalItem = null;

function renderSavedItems(type, items, listEl, emptyEl, mapper) {
  const searchTerm = ($("#saved-search").value || "").toLowerCase();
  const filtered = items.filter(item => {
    if (!searchTerm) return true;
    const m = mapper(item);
    return (m.title || "").toLowerCase().includes(searchTerm) ||
           (m.preview || "").toLowerCase().includes(searchTerm) ||
           (m.body || "").toLowerCase().includes(searchTerm);
  });

  savedItemsCache[type] = items;

  if (filtered.length === 0) {
    listEl.innerHTML = "";
    emptyEl.style.display = "block";
    return;
  }
  emptyEl.style.display = "none";

  listEl.innerHTML = filtered.map((item, i) => {
    const m = mapper(item);
    return `
    <div class="essay-saved-card" data-type="${type}" data-id="${item.id}">
      <div class="essay-saved-card-header" data-action="view-saved">
        <span class="essay-saved-card-title">
          <span class="saved-card-num">#${i + 1}</span>
          ${esc(m.title)}
        </span>
        <span class="essay-saved-card-meta">
          <span>${m.meta}</span>
          <span>${esc(m.date)}</span>
        </span>
        <div class="essay-saved-card-preview">${m.preview}...</div>
      </div>
      <div class="essay-saved-card-actions">
        <button class="btn btn-outline btn-sm" data-action="view-saved">查看</button>
        <button class="btn btn-outline btn-sm btn-export-saved" data-id="${item.id}" data-type="${type}">导出PDF</button>
        <button class="btn btn-outline btn-sm btn-del-saved" data-id="${item.id}" data-type="${type}">删除</button>
      </div>
    </div>`;
  }).join("");

  // View → modal
  listEl.querySelectorAll('[data-action="view-saved"]').forEach(el => {
    el.addEventListener("click", () => {
      const card = el.closest(".essay-saved-card");
      const id = parseInt(card.dataset.id);
      const tp = card.dataset.type;
      const item = savedItemsCache[tp].find(x => x.id === id);
      if (item) openSavedModal(tp, item);
    });
  });

  // Delete
  listEl.querySelectorAll(".btn-del-saved").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = parseInt(btn.dataset.id);
      const tp = btn.dataset.type;
      if (tp === "essay") deleteSavedEssay(id);
      else if (tp === "cloze") deleteSavedCloze(id);
      else if (tp === "grammar") deleteSavedGrammar(id);
    });
  });

  // Export PDF for saved items
  listEl.querySelectorAll(".btn-export-saved").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = parseInt(btn.dataset.id);
      const tp = btn.dataset.type;
      let url = "";
      if (tp === "essay") url = `/essays/${id}/export/pdf`;
      else if (tp === "cloze") url = `/clozes/${id}/export/pdf`;
      else if (tp === "grammar") url = `/grammar/compares/${id}/export/pdf`;
      if (!url) return;
      try {
        showToast("正在生成 PDF...");
        const { blob, filename } = await api.exportPdf(url);
        const a = document.createElement("a");
        const objUrl = URL.createObjectURL(blob);
        a.href = objUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(objUrl);
      } catch (err) {
        showToast(`导出失败：${err.message}`, "error");
      }
    });
  });
}

function openSavedModal(type, item) {
  const modal = $("#content-modal");
  const titleEl = $("#modal-title");
  const bodyEl = $("#modal-body");
  const delBtn = $("#modal-btn-delete");

  savedModalItem = { type, id: item.id };

  if (type === "essay") {
    titleEl.textContent = item.title;
    bodyEl.innerHTML = `<div style="font-size:16px;line-height:2;margin-bottom:16px">${esc(item.content)}</div>
      <div style="border-top:1px solid var(--border);padding-top:12px;color:var(--text-muted)">${esc(item.chinese_translation)}</div>`;
  } else if (type === "cloze") {
    titleEl.textContent = item.title;
    const blanks = typeof item.blanks === "string" ? JSON.parse(item.blanks) : item.blanks;
    const blankMap = {}; (blanks || []).forEach(b => { blankMap[b.id] = b; });
    const passageHtml = (item.passage || "").replace(/____(\d+)____/g, (_, id) => {
      const b = blankMap[parseInt(id)];
      return `<span style="border-bottom:2px dashed var(--primary);padding:0 4px;font-weight:600" title="${b ? b.answer : ''}">＿＿</span>`;
    });
    bodyEl.innerHTML = `<div style="font-size:16px;line-height:2.4;margin-bottom:16px">${passageHtml}</div>
      <div style="font-size:13px;color:var(--text-muted);margin-bottom:8px">答案：${(blanks||[]).map(b => `${b.answer}(${b.kana})`).join(" / ")}</div>
      <div style="border-top:1px solid var(--border);padding-top:12px;color:var(--text-muted)">${esc(item.chinese_translation || "")}</div>`;
  } else if (type === "grammar") {
    titleEl.textContent = item.topic;
    const result = typeof item.result === "string" ? JSON.parse(item.result) : item.result;
    const summary = result.summary || "";
    bodyEl.innerHTML = `<div style="margin-bottom:12px;line-height:1.8">${esc(summary)}</div>
      <div style="overflow-x:auto"><table class="grammar-compare-table"><thead><tr><th>语法</th><th>接续</th><th>含义</th><th>例句</th></tr></thead><tbody>
      ${(result.rows || []).map(r => `<tr><td>${esc(r.grammar)}</td><td>${esc(r.pattern)}</td><td>${esc(r.meaning)}</td><td>${esc(r.example)}<br><span style="color:var(--text-muted);font-size:12px">${esc(r.example_cn||"")}</span></td></tr>`).join("")}
      </tbody></table></div>`;
  }

  modal.style.display = "flex";
  delBtn.onclick = () => {
    if (type === "essay") deleteSavedEssay(item.id);
    else if (type === "cloze") deleteSavedCloze(item.id);
    else if (type === "grammar") deleteSavedGrammar(item.id);
    modal.style.display = "none";
  };
}

// Modal close
(function bindModalClose() {
  const modal = document.getElementById("content-modal");
  if (!modal) return;
  document.getElementById("modal-close").addEventListener("click", () => modal.style.display = "none");
  document.getElementById("modal-btn-close").addEventListener("click", () => modal.style.display = "none");
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.style.display = "none"; });
})();

async function deleteSavedEssay(id) {
  if (!confirm("确定删除这篇短文？")) return;
  try {
    await api.deleteEssay(id);
    showToast("已删除");
    loadSavedEssays();
  } catch (err) {
    showToast(`删除失败：${err.message}`, "error");
  }
}

// ── 保存页面子标签 ──
let savedSubTab = "essay";
function switchSavedTab(tab) {
  savedSubTab = tab;
  $("#saved-subtab-essay").classList.toggle("active", tab === "essay");
  $("#saved-subtab-cloze").classList.toggle("active", tab === "cloze");
  $("#saved-subtab-grammar").classList.toggle("active", tab === "grammar");
  $("#saved-panel-essay").style.display = tab === "essay" ? "block" : "none";
  $("#saved-panel-cloze").style.display = tab === "cloze" ? "block" : "none";
  $("#saved-panel-grammar").style.display = tab === "grammar" ? "block" : "none";
}
$("#saved-subtab-essay").addEventListener("click", () => switchSavedTab("essay"));
$("#saved-subtab-cloze").addEventListener("click", () => switchSavedTab("cloze"));
$("#saved-subtab-grammar").addEventListener("click", () => switchSavedTab("grammar"));

// Saved search live filter（按当前子标签重新渲染）
$("#saved-search").addEventListener("input", () => {
  if (savedSubTab === "essay") loadSavedEssays();
  else if (savedSubTab === "cloze") loadClozeSaved();
  else loadGrammarSaved();
});

// ── 短文记录 ──
async function loadSavedEssays() {
  try {
    const data = await api.listEssays(0, 50);
    renderSavedItems("essay", data.items || [], essaySavedList, essaySavedEmpty, (item) => ({
      id: item.id, title: item.title,
      meta: `${jlptBadge(item.jlpt_level)} · ${item.word_count || "?"}字`,
      date: item.created_at ? item.created_at.slice(0, 10) : "",
      preview: esc((item.content || "").replace(/【[^】]*】/g, "").slice(0, 80)),
      body: item.content,
      type: "essay",
    }));
  } catch (err) {
    showToast(`加载短文失败：${err.message}`, "error");
  }
}

// ── 语法记录 ──
async function loadGrammarSaved() {
  try {
    const data = await api.listGrammarCompares(0, 50);
    renderSavedItems("grammar", data.items || [], grammarSavedList, grammarSavedEmpty, (item) => {
      let result;
      try { result = JSON.parse(item.result); } catch { result = { summary: "", rows: [] }; }
      return {
        id: item.id, title: item.topic,
        meta: `${(result.rows||[]).length} 个语法点`,
        date: item.created_at ? item.created_at.slice(0, 10) : "",
        preview: esc((result.summary || "").slice(0, 80)),
        body: "",
        type: "grammar",
      };
    });
  } catch (err) {
    showToast(`加载语法记录失败：${err.message}`, "error");
  }
}

// ── 完型填空记录 ──
async function loadClozeSaved() {
  try {
    const data = await api.listClozes(0, 50);
    renderSavedItems("cloze", data.clozes || [], clozeSavedList, clozeSavedEmpty, (c) => ({
      id: c.id, title: c.title,
      meta: `${jlptBadge(c.jlpt_level)} · ${c.length}字 · ${(c.blanks||[]).length}个填空`,
      date: c.created_at ? c.created_at.slice(0, 10) : "",
      preview: esc((c.passage || "").replace(/____\d+____/g, "＿＿").slice(0, 80)),
      body: c.passage,
      type: "cloze",
    }));
  } catch (err) {
    console.error("加载完型填空失败:", err);
  }
}

async function deleteSavedCloze(id) {
  if (!confirm("确定删除这个完型填空吗？")) return;
  try {
    await api.deleteCloze(id);
    showToast("已删除");
    loadClozeSaved();
  } catch (err) {
    showToast(`删除失败：${err.message}`, "error");
  }
}

async function deleteSavedGrammar(id) {
  if (!confirm("确定删除这条语法记录吗？")) return;
  try {
    await api.deleteGrammarCompare(id);
    showToast("已删除");
    loadGrammarSaved();
  } catch (err) {
    showToast(`删除失败：${err.message}`, "error");
  }
}

// ── 入口：认证 → 加载全部保存内容 ──
initPage().then((ok) => {
  if (!ok) return;
  Promise.all([loadSavedEssays(), loadGrammarSaved(), loadClozeSaved()]);
});
