/**
 * 多模态日语词汇学习 — 前端主逻辑
 *
 * 单页面应用（SPA），通过显示/隐藏不同 page section 实现页面切换。
 * 核心功能模块（按代码顺序）：
 * - 认证（登录/注册/Token 管理）
 * - 导航切换（switchTab 控制页面显示）
 * - 单词生成（AI 生成 + 保存到词库）
 * - 词库管理（浏览/搜索/删除/合并去重）
 * - 背词（SM-2 间隔重复学习）
 * - 短文生成（AI 生成短文 + 保存）
 * - 完型填空（AI 生成填空练习 + 交互式作答）
 * - 语法分析/纠错/辨析
 * - 我的保存（短文/完型填空/语法）
 * - 成就/设置/管理员
 *
 * 工具函数：
 * - $(sel) / $$(sel) — DOM 查询简写
 * - esc(str) — HTML 转义防 XSS
 * - showToast(msg, type) — 消息提示
 * - streamRequest() — SSE 流式请求（定义在 api.js）
 */

// ===== DOM 查询简写 =====
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// 认证
const authPage = $("#auth-page");
const mainApp = $("#main-app");
const authTitle = $("#auth-title");
const authUsername = $("#auth-username");
const authPassword = $("#auth-password");
const authError = $("#auth-error");
const btnAuthSubmit = $("#btn-auth-submit");
const btnAuthSwitch = $("#btn-auth-switch");
const authSwitchText = $("#auth-switch-text");
const sidebarUsername = $("#sidebar-username");
const btnLogout = $("#btn-logout");

// 导航
const navGenerate = $("#nav-generate");
const navWordbank = $("#nav-wordbank");
const navSettings = $("#nav-settings");
const navAdmin = $("#nav-admin");
const pageGenerate = $("#page-generate");
const navStudy = $("#nav-study");
const pageStudy = $("#page-study");
const navEssay = $("#nav-essay");
const pageEssay = $("#page-essay");
const navGrammar = $("#nav-grammar");
const pageGrammar = $("#page-grammar");
const navSaved = $("#nav-saved");
const pageSaved = $("#page-saved");
const navCloze = $("#nav-cloze");
const pageCloze = $("#page-cloze");
const navImage = $("#nav-image");
const pageImage = $("#page-image");
const navAchievement = $("#nav-achievement");
const navHome = $("#nav-home");
const pageHome = $("#page-home");
const navCommunity = $("#nav-community");
const pageCommunity = $("#page-community");
const navBtns = [navHome, navCommunity, navGenerate, navWordbank, navStudy, navEssay, navCloze, navImage, navGrammar, navSaved, navAchievement, navSettings, navAdmin];
// pageCommunity 已迁移至独立页 /community（阶段二），不在此 SPA 内
// pageWordbank 已迁移至独立页 /wordbank（阶段二）
// pageStudy 已迁移至独立页 /study（阶段二）
// pageGenerate 已迁移至独立页 /generate（阶段二）
// pageEssay 已迁移至独立页 /essay（阶段二）
// pageCloze 已迁移至独立页 /cloze（阶段二）
// pageGrammar 已迁移至独立页 /grammar（阶段二）
// pageImage 已迁移至独立页 /image（阶段二）
const pages = [pageHome, pageSaved];

// 生成页

// 词库页
const studyBadge = $("#study-badge");
const apiStatus = $("#api-status");
const pageLoader = $("#page-loader");

// 页面加载缓存：首次加载显示指示器，再次进入直接用缓存
var pageLoadCache = {};
function withLoader(key, fn) {
  if (pageLoadCache[key]) {
    fn(); // 直接用缓存数据刷新（不显示 loading）
    return;
  }
  pageLoader.style.display = "flex";
  fn().then(function() { pageLoadCache[key] = true; }).finally(function() {
    pageLoader.style.display = "none";
  });
}

// ===== 认证状态 =====
let isRegisterMode = false;
let currentUsername = "";
let isAdmin = false;

// ===== 认证页面切换 =====
function showAuthPage() {
  authPage.style.display = "flex";
  mainApp.style.display = "none";
}

function showMainApp() {
  authPage.style.display = "none";
  mainApp.style.display = "flex";
}

function setAuthError(msg) {
  authError.textContent = msg;
  authError.style.display = "block";
}

function clearAuthError() {
  authError.style.display = "none";
  authError.textContent = "";
}

btnAuthSwitch.addEventListener("click", () => {
  isRegisterMode = !isRegisterMode;
  if (isRegisterMode) {
    authTitle.textContent = "注册";
    btnAuthSubmit.textContent = "注册";
    authSwitchText.textContent = "已有账号？";
    btnAuthSwitch.textContent = "登录";
  } else {
    authTitle.textContent = "登录";
    btnAuthSubmit.textContent = "登录";
    authSwitchText.textContent = "没有账号？";
    btnAuthSwitch.textContent = "注册";
  }
  clearAuthError();
});

btnAuthSubmit.addEventListener("click", () => doAuth());
authPassword.addEventListener("keydown", (e) => {
  if (e.key === "Enter") doAuth();
});
authUsername.addEventListener("keydown", (e) => {
  if (e.key === "Enter") authPassword.focus();
});

async function doAuth() {
  const username = authUsername.value.trim();
  const password = authPassword.value;

  if (!username || !password) {
    setAuthError("请填写用户名和密码");
    return;
  }

  if (password.length < 4) {
    setAuthError("密码至少4位");
    return;
  }

  btnAuthSubmit.disabled = true;
  clearAuthError();

  try {
    const fn = isRegisterMode ? api.register : api.login;
    const data = await fn(username, password);
    setToken(data.access_token);
    currentUsername = data.username;
    isAdmin = data.is_admin || false;
    sidebarUsername.textContent = data.username;
    if (isAdmin) {
      navAdmin.style.display = "";
    }
    showMainApp();
    initApp();
  } catch (err) {
    setAuthError(err.message);
  } finally {
    btnAuthSubmit.disabled = false;
  }
}

btnLogout.addEventListener("click", async () => {
  try {
    await api.logout();
  } catch (_) {
    /* server unreachable, clear local state anyway */
  }
  clearToken();
  currentUsername = "";
  isAdmin = false;
  navAdmin.style.display = "none";
  showAuthPage();
  authUsername.value = "";
  authPassword.value = "";
});

// ===== 状态 =====
let currentTab = "home";
// 词库分页

// ===== 导航切换 =====
// URL 路由化（阶段一）：tab 与路径一一对应（/community、/generate …），
// 支持分享/收藏/刷新保持页面、浏览器前进后退。
const VALID_TABS = [
  "home", "community", "generate", "wordbank", "study", "essay", "cloze",
  "image", "grammar", "saved", "achievement", "settings", "admin",
];

function tabFromPath() {
  const p = location.pathname.replace(/^\/+|\/+$/g, "");
  return p || "home";  // 根路径默认首页
}

function switchTab(tab, opts = {}) {
  if (!VALID_TABS.includes(tab)) return;
  currentTab = tab;
  navBtns.forEach((b) => b.classList.remove("active"));
  pages.forEach((p) => p.classList.remove("active"));

  // 同步 URL（popstate/初始加载时 noUrl 不重复入历史）
  if (!opts.noUrl) history.pushState({ tab }, "", "/" + tab);

  if (tab === "home") {
    navHome.classList.add("active");
    pageHome.classList.add("active");
    loadHome();
  } else if (tab === "community") {
    // 社区已拆为独立子页（阶段二）
    location.href = "/community";
  } else if (tab === "generate") {
    // 生成已拆为独立子页（阶段二）
    location.href = "/generate";
  } else if (tab === "wordbank") {
    // 词库已拆为独立子页（阶段二）
    location.href = "/wordbank";
  } else if (tab === "study") {
    // 背词已拆为独立子页（阶段二）
    location.href = "/study";
  } else if (tab === "essay") {
    // 短文已拆为独立子页（阶段二）
    location.href = "/essay";
  } else if (tab === "cloze") {
    // 完型已拆为独立子页（阶段二）
    location.href = "/cloze";
  } else if (tab === "image") {
    // 图片已拆为独立子页（阶段二）
    location.href = "/image";
  } else if (tab === "grammar") {
    // 语法已拆为独立子页（阶段二）
    location.href = "/grammar";
  } else if (tab === "saved") {
    navSaved.classList.add("active");
    pageSaved.classList.add("active");
    withLoader("saved", function() {
      return Promise.all([loadSavedEssays(), loadGrammarSaved(), loadClozeSaved()]);
    });
  } else if (tab === "achievement") {
    // 成就已拆为独立子页（阶段二）
    location.href = "/achievement";
  } else if (tab === "settings") {
    // 设置已拆为独立子页（阶段二）
    location.href = "/settings";
  } else if (tab === "admin") {
    // 管理已拆为独立子页（阶段二）
    location.href = "/admin";
  }
}

navGenerate.addEventListener("click", () => switchTab("generate"));
navHome.addEventListener("click", () => switchTab("home"));
navCommunity.addEventListener("click", () => switchTab("community"));
navWordbank.addEventListener("click", () => switchTab("wordbank"));
navStudy.addEventListener("click", () => switchTab("study"));
navEssay.addEventListener("click", () => switchTab("essay"));
navCloze.addEventListener("click", () => switchTab("cloze"));
navImage.addEventListener("click", () => switchTab("image"));
navGrammar.addEventListener("click", () => switchTab("grammar"));
navSaved.addEventListener("click", () => switchTab("saved"));
navAchievement.addEventListener("click", () => switchTab("achievement"));
navSettings.addEventListener("click", () => switchTab("settings"));
navAdmin.addEventListener("click", () => switchTab("admin"));

// URL 路由：直达路径（/community 等）与浏览器前进/后退
(function initRouter() {
  const initTab = tabFromPath();
  if (VALID_TABS.includes(initTab)) {
    switchTab(initTab, { noUrl: true });
  }
  window.addEventListener("popstate", () => {
    const t = tabFromPath();
    if (VALID_TABS.includes(t)) switchTab(t, { noUrl: true });
  });
})();

// ===== 发音 =====
let audioCtx = null;
let audioSource = null;
let speakingBtn = null;

function unlockAudio() {
  if (audioCtx) return;
  try {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();
  } catch {}
}

// AudioContext must be created / resumed during a user gesture.
// Once running, decodeAudioData + source.start() bypass autoplay policy.
document.addEventListener("click", unlockAudio, { once: true });
document.addEventListener("touchstart", unlockAudio, { once: true });

function clearSpeaking() {
  if (speakingBtn) {
    speakingBtn.classList.remove("speaking");
    speakingBtn = null;
  }
  if (audioSource) {
    try { audioSource.stop(); } catch {}
    audioSource = null;
  }
}

function speakWord(japanese, kana, btn) {
  const text = kana || japanese;

  clearSpeaking();

  speakingBtn = btn || null;
  if (btn) btn.classList.add("speaking");

  // Ensure AudioContext is running (may have been suspended by the OS)
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume();
  }

  api
    .voice(text)
    .then((url) =>
      // Re-fetch the blob URL as ArrayBuffer for Web Audio API.
      // This is a local in-memory fetch — no network cost.
      fetch(url)
        .then((r) => r.arrayBuffer())
        .finally(() => URL.revokeObjectURL(url)),
    )
    .then((buf) => {
      if (!audioCtx) {
        // Belt-and-suspenders: create AudioCtx now if unlock didn't fire
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      audioCtx.decodeAudioData(
        buf,
        (decoded) => {
          audioSource = audioCtx.createBufferSource();
          audioSource.buffer = decoded;
          audioSource.connect(audioCtx.destination);
          audioSource.onended = () => {
            if (speakingBtn) speakingBtn.classList.remove("speaking");
            speakingBtn = null;
            audioSource = null;
          };
          audioSource.start(0);
        },
        () => {
          clearSpeaking();
          showToast("语音解码失败", "error");
        },
      );
    })
    .catch((err) => {
      clearSpeaking();
      showToast(`发音失败：${err.message}`, "error");
    });
}

// ===== Toast =====
function showToast(msg, type = "success", duration = 2500) {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  if (duration > 0) {
    setTimeout(() => el.remove(), duration);
  }
  return el;  // 返回元素引用，调用方可手动 remove
}

/**
 * 统一 API/运行时错误处理（#40）：
 * - 错误 toast 提示（风格统一，不再依赖各处拼 `失败：${err.message}`）
 * - console.error 记录，避免静默吞错
 * 返回可展示的消息文本，便于调用方写入错误区域。
 */
function handleApiError(err, fallbackMsg = "操作失败，请稍后重试") {
  const msg = (err && err.message) || fallbackMsg;
  console.error("[app]", err);
  showToast(msg, "error", 3500);
  return msg;
}

const essaySavedList = $("#essay-saved-list");
const essaySavedEmpty = $("#essay-saved-empty");

const clozeSavedList = $("#cloze-saved-list");
const clozeSavedEmpty = $("#cloze-saved-empty");


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
document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("content-modal");
  if (!modal) return;
  document.getElementById("modal-close").addEventListener("click", () => modal.style.display = "none");
  document.getElementById("modal-btn-close").addEventListener("click", () => modal.style.display = "none");
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.style.display = "none"; });
});

// Saved search live filter
document.addEventListener("input", (e) => {
  if (e.target.id === "saved-search") {
    if (currentTab === "saved") {
      const subtab = document.querySelector(".study-subtab.active");
      if (subtab) subtab.click();
    }
  }
});

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

function escHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

// ── 语法记录页 ──
async function loadGrammarSaved() {
  try {
    const data = await api.listGrammarCompares(0, 50);
    renderSavedItems("grammar", data.items || [], $("#grammar-saved-list"), $("#grammar-saved-empty"), (item) => {
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

async function updateStudyBadge() {
  try {
    const data = await api.studyDue();
    const count = data.total || 0;
    if (count > 0) {
      studyBadge.textContent = count > 99 ? "99+" : String(count);
      studyBadge.title = `待复习 ${data.due_review || 0} · 今日新词 ${data.new_today || 0}/${data.new_available || 0}`;
      studyBadge.style.display = "inline-flex";
    } else {
      studyBadge.style.display = "none";
    }
  } catch {}
}

// ===== 初始化 =====
async function initApp() {
  try {
    await api.health();
    apiStatus.innerHTML = '<span class="status-dot ok"></span> API 已连接';
  } catch {
    apiStatus.innerHTML = '<span class="status-dot"></span> API 未连接';
  }
  updateStudyBadge();
}

function esc(s) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  return String(s).replace(/[&<>"']/g, (c) => map[c]);
}

/**
 * 统一 SSE 流式处理（#38）：管理流预览框显示/追加/隐藏，并归一事件分发。
 * 原 7 处 AI 生成端点重复的「显示 preview → 追加 chunk → done/error → 隐藏」模板
 * 收敛为单一函数；调用方只需提供 onDone / onError 业务逻辑。
 *
 * @param {string} url        API 路径（如 "/generate"）
 * @param {object} body       请求体（含 stream: true）
 * @param {string} previewId  流预览元素 id（如 "stream-preview"）
 * @param {object} handlers   { onChunk?, onDone?, onError? }
 */
async function runStreamToPreview(url, body, previewId, handlers = {}) {
  const previewEl = $(previewId);
  previewEl.style.display = "block";
  previewEl.textContent = "";
  const { onChunk, onDone, onError } = handlers;
  try {
    await streamRequest(url, body, (event) => {
      if (event.chunk) {
        previewEl.textContent += event.chunk;
        previewEl.scrollTop = previewEl.scrollHeight;
        if (onChunk) onChunk(event.chunk);
      } else if (event.done) {
        if (onDone) onDone(event.result);
      } else if (event.error) {
        if (onError) onError(event.error);
        else throw new Error(event.error);
      }
    });
  } finally {
    previewEl.style.display = "none";
  }
}

function jlptBadge(level) {
  if (!level) return "";
  return `<span class="jlpt-badge ${esc(level)}">${esc(level)}</span>`;
}

// ===== 首页（学习仪表盘） =====
function fmtTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const diff = Math.floor((Date.now() - d.getTime()) / 1000);
  if (diff < 60) return "刚刚";
  if (diff < 3600) return Math.floor(diff / 60) + " 分钟前";
  if (diff < 86400) return Math.floor(diff / 3600) + " 小时前";
  const dt = new Date(iso);
  return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
}

const DAILY_QUOTES = [
  { jp: "継続は力なり。", cn: "坚持就是力量。" },
  { jp: "七転び八起き。", cn: "跌倒了七次，第八次站起来（百折不挠）。" },
  { jp: "努力は裏切らない。", cn: "努力不会背叛你。" },
  { jp: "千里の道も一歩から。", cn: "千里之行，始于足下。" },
  { jp: "石の上にも三年。", cn: "功到自然成。" },
  { jp: "急がば回れ。", cn: "欲速则不达。" },
  { jp: "失敗は成功の母。", cn: "失败是成功之母。" },
  { jp: "三人寄れば文殊の知恵。", cn: "三个臭皮匠，顶个诸葛亮。" },
  { jp: "聞くは一時の恥、聞かぬは一生の恥。", cn: "问是一时之耻，不问是一生之耻。" },
  { jp: "初心忘るべからず。", cn: "勿忘初心。" },
  { jp: "雨降って地固まる。", cn: "雨过地更坚（坏事过后更团结）。" },
  { jp: "案ずるより産むが易し。", cn: "与其焦虑，不如行动（船到桥头自然直）。" },
];

function dailyQuote() {
  const now = new Date();
  const dayNum = now.getFullYear() * 10000 + (now.getMonth() + 1) * 100 + now.getDate();
  return DAILY_QUOTES[dayNum % DAILY_QUOTES.length];
}

async function loadHome() {
  // 问候语（按时段）
  const h = new Date().getHours();
  const greet = h < 6 ? "夜深了" : h < 12 ? "おはよう" : h < 18 ? "こんにちは" : "こんばんは";
  $("#home-welcome-title").textContent = `${greet}、${currentUsername}！`;
  $("#home-welcome-sub").textContent = "今天也要一起加油学习日语哦 (≧∇≦)ﾉ";

  // 统计卡片 + 公告（并行拉取；部分失败不阻塞首页）
  try {
    const [due, stats, posts, achs] = await Promise.all([
      api.studyDue(),
      api.studyStats(),
      api.communityPosts(0, 5),
      api.listAchievements(),
    ]);
    $("#stat-due").textContent = (due.due_review ?? 0) + (due.new_today ?? 0);
    $("#stat-new").textContent = stats.new_available ?? 0;
    $("#stat-learned").textContent = stats.learned ?? 0;
    // 连续学习天数：从成就推断（streak_1/3/7/10/30/100 最大已达成档位）
    const achieved = new Set(
      (achs.achievements || []).filter((a) => a.achieved).map((a) => a.key)
    );
    const streakDays = [100, 30, 10, 7, 3, 1].find((d) => achieved.has(`streak_${d}`)) || 0;
    $("#stat-streak").textContent = streakDays;

    // 最新公告（置顶公告，最多 3 条）
    const ann = (posts.posts || []).filter((p) => p.type === "announcement" && p.is_pinned).slice(0, 3);
    const annEl = $("#home-announcements");
    if (ann.length) {
      annEl.style.display = "block";
      annEl.innerHTML =
        '<div class="home-announcements-title">📢 最新公告</div>' +
        ann.map(
          (p) => `<div class="home-announcement-item" data-id="${p.id}">
            <span class="home-announcement-item-title">${esc(p.title)}</span>
            <span class="home-announcement-item-time">${fmtTime(p.created_at)}</span>
          </div>`
        ).join("");
      annEl.querySelectorAll(".home-announcement-item").forEach((el) => {
        el.addEventListener("click", () => {
          // 公告详情在独立社区页（阶段二）
          location.href = "/community";
        });
      });
    } else {
      annEl.style.display = "none";
    }
  } catch (err) {
    console.error("首页统计数据加载失败:", err);
  }

  // 每日一言
  const q = dailyQuote();
  $("#home-daily-jp").textContent = q.jp;
  $("#home-daily-cn").textContent = q.cn;
  // 发音走通用 speakWord（Web Audio 绕过 autoplay 策略，与词卡/社区一致）
  $("#btn-home-daily-speak").onclick = (e) => speakWord(q.jp, null, e.currentTarget);

  // 推荐词（词库最新一条）
  try {
    const wl = await api.listWords({ limit: 1 });
    const w = wl.words && wl.words[0];
    const rec = $("#home-recommend");
    if (w) {
      rec.style.display = "block";
      $("#home-recommend-word").textContent = w.japanese;
      $("#home-recommend-kana").textContent = w.kana || "";
      $("#home-recommend-cn").textContent = w.chinese || "";
      // 发音走通用 speakWord（与词卡一致）
      $("#btn-home-recommend-speak").onclick = (e) => speakWord(w.japanese, w.kana, e.currentTarget);
    } else {
      rec.style.display = "none";
    }
  } catch (err) {
    $("#home-recommend").style.display = "none";
  }
}

// 快捷入口绑定（事件委托）
$("#page-home").addEventListener("click", (e) => {
  const btn = e.target.closest(".home-quick-btn");
  if (btn) switchTab(btn.dataset.goto);
});

// ===== 启动 =====
(function init() {
  // 为所有带 placeholder 的输入框添加 title 属性，hover 时显示完整提示
  document.querySelectorAll("input[placeholder]").forEach((el) => {
    if (!el.hasAttribute("title")) el.setAttribute("title", el.getAttribute("placeholder"));
  });

  const savedToken = sessionStorage.getItem("token");
  if (savedToken) {
    // 尝试验证已保存的 token
    setToken(savedToken);
    api
      .me()
      .then((data) => {
        currentUsername = data.username;
        isAdmin = data.is_admin || false;
        sidebarUsername.textContent = data.username;
        if (isAdmin) navAdmin.style.display = "";
        // 验证通过，进入主界面
        authPage.style.display = "none";
        mainApp.style.display = "flex";
        initApp();
            // 新成就提醒
        if (data.new_achievements && data.new_achievements.length > 0) {
          data.new_achievements.forEach((a, i) => {
            setTimeout(() => {
              showToast(`${a.icon} 解锁成就：${a.name}`, "achievement");
            }, i * 600);
          });
        }
      })
      .catch(() => {
        // token 过期或无效，清除并显示登录页
        clearToken();
        authPage.style.display = "flex";
        mainApp.style.display = "none";
      });
  } else {
    // 无 token，确保显示登录页（auth-page 默认已可见）
    mainApp.style.display = "none";
  }
})();

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

function renderClozePassageStatic(passage, blanks) {
  let parts = passage.split("____");
  let html = "";
  for (let i = 0; i < parts.length; i++) {
    html += esc(parts[i]);
    if (i < blanks.length) {
      const b = blanks[i];
      html += `<span class="cloze-static-blank">${esc(b.answer)}（${esc(b.kana)}）</span>`;
    }
  }
  return html;
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

function viewSavedCloze(clozes, id) {
  const c = clozes.find((x) => x.id === id);
  if (!c) return;
  currentClozeData = {
    title: c.title,
    passage: c.passage,
    blanks: c.blanks || [],
    chinese_translation: c.chinese_translation || "",
  };
  clozeLastConfig = { topics: c.topics || [], length: c.length || 400, level: c.jlpt_level || "N3" };
  renderClozeResult(currentClozeData);
  clozeResult.style.display = "block";
  clozeResult.scrollIntoView({ behavior: "smooth" });
  switchTab("cloze");
}

/* ===== 移动端适配 ===== */
(function() {
  'use strict';
  var sidebar = document.querySelector('.sidebar');
  var overlay = document.getElementById('sidebar-overlay');
  var hamburger = document.getElementById('hamburger-btn');
  var bottomNav = document.getElementById('mobile-bottom-nav');
  var mainApp = document.getElementById('main-app');
  var moreOverlay = document.getElementById('more-menu-overlay');
  var morePopup = document.getElementById('more-menu-popup');
  var btnMore = document.getElementById('btn-more-menu');

  if (!sidebar || !hamburger) return;

  // ── "更多"弹出菜单 ──
  function showMoreMenu() {
    moreOverlay.classList.add('show');
    morePopup.classList.add('show');
  }
  function hideMoreMenu() {
    moreOverlay.classList.remove('show');
    morePopup.classList.remove('show');
  }
  if (btnMore) {
    btnMore.addEventListener('click', function(e) {
      e.stopPropagation();
      morePopup.classList.contains('show') ? hideMoreMenu() : showMoreMenu();
    });
  }
  if (moreOverlay) {
    moreOverlay.addEventListener('click', hideMoreMenu);
  }

  // 打开侧边栏
  function openSidebar() {
    sidebar.classList.add('open');
    if (overlay) overlay.classList.add('show');
  }

  // 关闭侧边栏
  function closeSidebar() {
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('show');
  }

  // 汉堡按钮点击
  hamburger.addEventListener('click', function() {
    sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
  });

  // 遮罩点击关闭
  if (overlay) {
    overlay.addEventListener('click', closeSidebar);
  }

  // 所有导航按钮（侧边栏+底部导航）点击关闭侧边栏
  document.addEventListener('click', function(e) {
    // 侧边栏导航按钮
    if (e.target.closest('.nav-btn')) {
      closeSidebar();
    }
    // 底部导航按钮
    if (e.target.closest('.mobile-bottom-nav button')) {
      var tab = e.target.closest('button').getAttribute('data-tab');
      if (tab && tab !== 'more') {
        var navBtn = document.querySelector('.nav-btn[data-tab="' + tab + '"]');
        if (navBtn) navBtn.click();
        // 更新底部导航 active（跳过"更多"按钮）
        var btns = bottomNav.querySelectorAll('button');
        btns.forEach(function(b) { b.classList.remove('active'); });
        e.target.closest('button').classList.add('active');
      }
      closeSidebar();
      hideMoreMenu();
    }
    // "更多"弹出菜单中的按钮
    if (e.target.closest('.more-menu-popup button')) {
      var tab2 = e.target.closest('button').getAttribute('data-tab');
      if (tab2) {
        var navBtn2 = document.querySelector('.nav-btn[data-tab="' + tab2 + '"]');
        if (navBtn2) navBtn2.click();
      }
      hideMoreMenu();
      closeSidebar();
    }
  });

  // 主内容区点击也关闭（可选，点击空白区域）
  if (document.querySelector('.main')) {
    document.querySelector('.main').addEventListener('click', function() {
      if (window.innerWidth <= 768) closeSidebar();
    });
  }

  // 监听侧边栏 nav-btn 点击，同步底部导航 active
  var navBtns = document.querySelectorAll('.nav-btn');
  navBtns.forEach(function(btn) {
    btn.addEventListener('click', function() {
      var tab = btn.getAttribute('data-tab');
      if (bottomNav && tab) {
        var mbBtns = bottomNav.querySelectorAll('button');
        mbBtns.forEach(function(b) { b.classList.remove('active'); });
        var target = bottomNav.querySelector('button[data-tab="' + tab + '"]');
        if (target) target.classList.add('active');
      }
    });
  });

  // 窗口大小变化时关闭侧边栏
  window.addEventListener('resize', function() {
    if (window.innerWidth > 768) closeSidebar();
  });
})();

// ══════════════════════════════════════════
// 🥚 彩蛋：连点 Logo 或标题「あ」7次 → 樱花飘落 + 成就解锁
// 同时监听侧边栏 logo 和登录页 logo
// ══════════════════════════════════════════
(function() {
  var clicks = 0;
  var timer = null;
  var fired = false;

  function handleClick() {
    if (fired) return;
    clicks++;
    clearTimeout(timer);
    timer = setTimeout(function() { clicks = 0; }, 1500);
    if (clicks >= 7) {
      fired = true;
      clicks = 0;
      if (typeof api !== 'undefined') {
        api.awardAchievement('konami_code').then(function(res) {
          if (res.awarded) showToast(res.icon + ' 解锁成就：' + res.name, 'achievement');
        }).catch(function(){});
      }
      var container = document.createElement('div');
      container.className = 'sakura-container';
      for (var i = 0; i < 50; i++) {
        var petal = document.createElement('span');
        petal.className = 'sakura-petal';
        petal.textContent = ['🌸','💮','🌺','🍂','✨'][Math.floor(Math.random()*5)];
        petal.style.left = Math.random() * 100 + '%';
        petal.style.animationDelay = Math.random() * 3 + 's';
        petal.style.animationDuration = (Math.random() * 3 + 3) + 's';
        petal.style.fontSize = (Math.random() * 16 + 12) + 'px';
        container.appendChild(petal);
      }
      document.body.appendChild(container);
      showToast('やった！隠し機能を発見した！\n(>ω<)  七回クリックの秘密!', 'achievement');
      setTimeout(function() { container.remove(); fired = false; }, 6000);
    }
  }

  // 用事件代理监听所有 "あ" 图标（侧边栏和登录页）
  document.addEventListener('click', function(e) {
    var target = e.target;
    if (target.classList.contains('logo-icon') || target.classList.contains('auth-brand-icon')) {
      handleClick();
    }
  });
})();
