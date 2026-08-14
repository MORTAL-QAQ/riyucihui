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
const pageWordbank = $("#page-wordbank");
const pageSettings = $("#page-settings");
const pageAdmin = $("#page-admin");
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
const pageAchievement = $("#page-achievement");
const navHome = $("#nav-home");
const pageHome = $("#page-home");
const navCommunity = $("#nav-community");
const pageCommunity = $("#page-community");
const navBtns = [navHome, navCommunity, navGenerate, navWordbank, navStudy, navEssay, navCloze, navImage, navGrammar, navSaved, navAchievement, navSettings, navAdmin];
const pages = [pageHome, pageCommunity, pageGenerate, pageWordbank, pageStudy, pageEssay, pageCloze, pageImage, pageGrammar, pageSaved, pageAchievement, pageSettings, pageAdmin];

// 生成页
const topicInput = $("#topic-input");
const difficultySelect = $("#difficulty-select");
const wordCountSelect = $("#word-count-select");
const extraInput = $("#extra-input");
const btnGenerate = $("#btn-generate");
const loadingEl = $("#loading");
const resultArea = $("#result-area");
const resultTopic = $("#result-topic");
const wordCards = $("#word-cards");
const btnSelectAll = $("#btn-select-all");
const btnSave = $("#btn-save");
const btnGenerateMore = $("#btn-generate-more");
const selectedCount = $("#selected-count");
const generateError = $("#generate-error");
const generateWelcome = $("#generate-welcome");

// 词库页
const topicList = $("#topic-list");
const searchInput = $("#search-input");
const wordbankCards = $("#wordbank-cards");
const wordbankInfo = $("#wordbank-info");
const emptyState = $("#empty-state");
const btnGoGenerate = $("#btn-go-generate");
const quotaBar = $("#quota-bar");
const quotaText = $("#quota-text");
const quotaProgressFill = $("#quota-progress-fill");
const wbPagination = $("#wordbank-pagination");
const wbPrev = $("#wb-prev");
const wbNext = $("#wb-next");
const wbPageInfo = $("#wb-page-info");
const wbJumpInput = $("#wb-jump-input");
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
    loadGenerateQuota();
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
let generatedWords = [];
let generatedDifficulty = null;  // 当前生成结果的 JLPT 等级
let selectedSet = new Set();
let savedWordIndices = new Set();  // 已快速收藏的单词索引
let currentTab = "generate";
let currentTopic = "";
let currentSearch = "";
// 词库分页
let wordbankPage = 1;
const WORD_PAGE_SIZE = 10;
let essaySelectedTopics = [];
let essayLastConfig = null;

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
    navCommunity.classList.add("active");
    pageCommunity.classList.add("active");
    withLoader("community", loadCommunity);
  } else if (tab === "generate") {
    navGenerate.classList.add("active");
    pageGenerate.classList.add("active");
    loadGenerateQuota();
  } else if (tab === "wordbank") {
    navWordbank.classList.add("active");
    pageWordbank.classList.add("active");
    withLoader("wordbank", loadWordbank);
  } else if (tab === "study") {
    navStudy.classList.add("active");
    pageStudy.classList.add("active");
    updateStudyBadge();
    withLoader("study", loadStudyPick);
  } else if (tab === "essay") {
    navEssay.classList.add("active");
    pageEssay.classList.add("active");
    withLoader("essay", loadEssayPick);
  } else if (tab === "cloze") {
    navCloze.classList.add("active");
    pageCloze.classList.add("active");
    withLoader("cloze", loadClozePick);
  } else if (tab === "image") {
    navImage.classList.add("active");
    pageImage.classList.add("active");
    withLoader("image", loadImageCards);
  } else if (tab === "grammar") {
    navGrammar.classList.add("active");
    pageGrammar.classList.add("active");
  } else if (tab === "saved") {
    navSaved.classList.add("active");
    pageSaved.classList.add("active");
    withLoader("saved", function() {
      return Promise.all([loadSavedEssays(), loadGrammarSaved(), loadClozeSaved()]);
    });
  } else if (tab === "achievement") {
    navAchievement.classList.add("active");
    pageAchievement.classList.add("active");
    withLoader("achievement", loadAchievements);
  } else if (tab === "settings") {
    navSettings.classList.add("active");
    pageSettings.classList.add("active");
    loadSettings();
  } else if (tab === "admin") {
    navAdmin.classList.add("active");
    pageAdmin.classList.add("active");
    loadAdmin();
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
btnGoGenerate.addEventListener("click", () => switchTab("generate"));

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

// ===== 生成单词 =====
btnGenerate.addEventListener("click", () => doGenerate());
topicInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") doGenerate();
});
extraInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") doGenerate();
});

document.addEventListener("click", (e) => {
  if (e.target.classList.contains("tag")) {
    topicInput.value = e.target.dataset.topic;
    doGenerate();
  }
});

async function loadGenerateQuota() {
  try {
    const q = await api.generateQuota();

    const remaining = q.remaining;
    const limit = q.daily_limit;
    const used = q.today_generated;

    if (q.is_admin || limit === null) {
      // 管理员或不限
      quotaText.className = "quota-text unlimited";
      quotaText.innerHTML = `今日已生成 <span class="quota-highlight">${used}</span> 个单词 · <span class="quota-highlight">不限</span>`;
      quotaProgressFill.style.width = "0%";
      quotaProgressFill.className = "quota-progress-fill";
    } else {
      const pct = Math.min(100, (used / limit) * 100);
      quotaProgressFill.style.width = pct + "%";

      if (remaining <= 0) {
        quotaText.className = "quota-text danger";
        quotaProgressFill.className = "quota-progress-fill danger";
      } else if (pct >= 80) {
        quotaText.className = "quota-text warning";
        quotaProgressFill.className = "quota-progress-fill warning";
      } else {
        quotaText.className = "quota-text";
        quotaProgressFill.className = "quota-progress-fill";
      }

      quotaText.innerHTML = `今日已生成 <span class="quota-highlight">${used}</span> / <span class="quota-highlight">${limit}</span> 个单词（剩余 <span class="quota-highlight">${remaining}</span> 个）`;
    }
  } catch {
    // API 不可用时保留默认显示（HTML 初始值："今日可生成 100 个单词"）
  }
}

async function doGenerate() {
  const topic = topicInput.value.trim();
  if (!topic) {
    topicInput.focus();
    return;
  }
  currentTopic = topic;  // 记住主题，供快速收藏和批量保存使用
  savedWordIndices = new Set();  // 重置收藏状态

  const difficulty = difficultySelect.value;
  generatedDifficulty = difficulty || null;
  const extra = extraInput.value.trim();
  const count = parseInt(wordCountSelect.value) || 10;

  btnGenerate.disabled = true;
  loadingEl.style.display = "block";
  resultArea.style.display = "none";
  generateError.style.display = "none";

  try {
    await runStreamToPreview("/generate", {
      topic, difficulty: difficulty || undefined, extra: extra || undefined, count, stream: true,
    }, "stream-preview", {
      onDone: (result) => {
        generatedWords = result;
        // 确保每个单词都有 jlpt_level（服务端流式模式可能未注入时兜底）
        if (generatedDifficulty) {
          generatedWords.forEach(w => { if (!w.jlpt_level) w.jlpt_level = generatedDifficulty; });
        }
        selectedSet = new Set(generatedWords.map((_, i) => i));
        renderResultCards(topic);
        loadingEl.style.display = "none";
        resultArea.style.display = "block";
        generateWelcome.style.display = "none";
        resultArea.scrollIntoView({ behavior: "smooth" });
        loadGenerateQuota();
      },
      onError: (msg) => { throw new Error(msg); },
    });
  } catch (err) {
    loadingEl.style.display = "none";
    generateError.style.display = "block";
    generateError.textContent = `生成失败：${err.message}`;
    showToast("生成失败，请重试", "error");
  } finally {
    btnGenerate.disabled = false;
  }
}

function renderResultCards(topic) {
  resultTopic.textContent = topic;
  wordCards.innerHTML = "";

  generatedWords.forEach((w, i) => {
    const card = document.createElement("div");
    card.className = `word-card ${selectedSet.has(i) ? "selected" : ""}`;
    const saved = savedWordIndices.has(i);
    card.innerHTML = `
      <div class="checkbox">✓</div>
      <div class="card-body">
        <div class="card-main">
          <button class="speak-btn" data-speak="${esc(w.japanese)}" data-kana="${esc(w.kana)}" title="发音">▶</button>
          <span class="card-jp">${esc(w.japanese)}</span>
          <span class="card-kana">${esc(w.kana)}</span>
          <span class="card-chinese">${esc(w.chinese)}</span>
          ${jlptBadge(w.jlpt_level)}
          <button class="star-btn ${saved ? 'saved' : ''}" data-index="${i}" title="${saved ? '已收藏' : '收藏到词库'}">${saved ? '★' : '☆'}</button>
        </div>
        <div class="card-example">
          <span>${esc(w.example_ja)}</span>
          <span class="example-cn">${esc(w.example_cn)}</span>
        </div>
      </div>`;
    card.addEventListener("click", (e) => {
      if (e.target.closest(".speak-btn") || e.target.closest(".star-btn")) return;
      toggleCard(i, card);
    });
    wordCards.appendChild(card);
  });

  updateSaveButton();
}

wordCards.addEventListener("click", (e) => {
  const speakBtn = e.target.closest(".speak-btn");
  if (speakBtn) {
    speakWord(speakBtn.dataset.speak, speakBtn.dataset.kana, speakBtn);
    return;
  }
  const starBtn = e.target.closest(".star-btn");
  if (starBtn) {
    e.stopPropagation();
    const idx = parseInt(starBtn.dataset.index);
    quickSaveWord(idx, starBtn);
  }
});

async function quickSaveWord(index, btn) {
  const w = generatedWords[index];
  if (!w) return;
  btn.disabled = true;
  try {
    await api.saveWords(currentTopic || w.japanese, [w], generatedDifficulty);
    savedWordIndices.add(index);
    btn.classList.add("saved");
    btn.textContent = "★";
    btn.title = "已收藏";
    showToast("已收藏到词库");
  } catch (err) {
    showToast(`收藏失败：${err.message}`, "error");
  } finally {
    btn.disabled = false;
  }
}

function toggleCard(index, card) {
  if (selectedSet.has(index)) {
    selectedSet.delete(index);
    card.classList.remove("selected");
  } else {
    selectedSet.add(index);
    card.classList.add("selected");
  }
  updateSaveButton();
}

function updateSaveButton() {
  const count = selectedSet.size;
  selectedCount.textContent = count;
  btnSave.disabled = count === 0;
}

btnSelectAll.addEventListener("click", () => {
  const all = generatedWords.length;
  if (selectedSet.size === all) {
    selectedSet.clear();
    wordCards.querySelectorAll(".word-card").forEach((c) => c.classList.remove("selected"));
  } else {
    selectedSet = new Set(generatedWords.map((_, i) => i));
    wordCards.querySelectorAll(".word-card").forEach((c) => c.classList.add("selected"));
  }
  updateSaveButton();
});

btnSave.addEventListener("click", async () => {
  if (selectedSet.size === 0) return;

  const topic = topicInput.value.trim();
  const sortedIndices = [...selectedSet].sort((a, b) => b - a); // descending for splice
  const words = sortedIndices.slice().reverse().map((i) => generatedWords[i]);

  btnSave.disabled = true;
  try {
    await api.saveWords(topic, words, generatedDifficulty);
    showToast(`成功保存 ${words.length} 个单词到词库`);
    // 从列表中移除已保存的单词
    for (const i of sortedIndices) {
      generatedWords.splice(i, 1);
    }
    selectedSet.clear();
    if (generatedWords.length > 0) {
      renderResultCards(topic);
    } else {
      wordCards.innerHTML = "";
      resultArea.style.display = "none";
      generateWelcome.style.display = "";
      updateSaveButton();
      showToast("所有单词已保存", "success");
    }
  } catch (err) {
    showToast(`保存失败：${err.message}`, "error");
  } finally {
    btnSave.disabled = false;
  }
});

btnGenerateMore.addEventListener("click", async () => {
  const topic = topicInput.value.trim();
  if (!topic) return;

  const existingWords = generatedWords.map((w) => w.japanese);
  const difficulty = difficultySelect.value;
  generatedDifficulty = difficulty || null;
  const extra = extraInput.value.trim();
  const count = parseInt(wordCountSelect.value) || 10;

  btnGenerateMore.disabled = true;
  try {
    await runStreamToPreview("/generate", {
      topic, difficulty: difficulty || undefined, extra: extra || undefined, count, exclude_words: existingWords, stream: true,
    }, "stream-preview", {
      onDone: (result) => {
        const oldLen = generatedWords.length;
        if (generatedDifficulty) {
          result.forEach(w => { if (!w.jlpt_level) w.jlpt_level = generatedDifficulty; });
        }
        generatedWords.push(...result);
        for (let i = oldLen; i < generatedWords.length; i++) {
          selectedSet.add(i);
        }
        renderResultCards(topic);
        showToast(`新增 ${result.length} 个单词`);
        loadGenerateQuota();
      },
      onError: (msg) => { throw new Error(msg); },
    });
  } catch (err) {
    showToast(`生成失败：${err.message}`, "error");
  } finally {
    btnGenerateMore.disabled = false;
  }
});

// ===== 词库 =====
async function loadWordbank(reset = true) {
  try {
    if (reset) {
      wordbankPage = 1;
    }
    const offset = (wordbankPage - 1) * WORD_PAGE_SIZE;
    const [wordsData, topicsData] = await Promise.all([
      api.listWords({
        topic: currentTopic,
        search: currentSearch,
        offset,
        limit: WORD_PAGE_SIZE,
      }),
      api.listTopics(),
    ]);
    renderTopics(topicsData);
    renderWordbankCards(wordsData);
    // Load study status in background after cards are rendered
    if (wordsData.words.length > 0) {
      loadStudyStatus(wordsData.words);
    }
  } catch (err) {
    showToast(`加载词库失败：${err.message}`, "error");
  }
}

async function loadStudyStatus(words) {
  const ids = words.map(w => w.id);
  try {
    const statusList = await api.studyWordsStatus(ids);
    const statusMap = {};
    statusList.forEach(s => { statusMap[s.word_id] = s; });
    words.forEach(w => {
      const row = wordbankCards.querySelector(`.wordbank-study-row[data-word-id="${w.id}"]`);
      if (!row) return;
      renderStudyRow(row, statusMap[w.id]);
    });
  } catch (_) { /* status load is non-critical */ }
}

function renderStudyRow(row, s) {
  if (!s) {
    row.innerHTML = '<span style="font-size:11px;color:#bbb">未学习</span>';
    return;
  }
  let dotsHtml = '<span class="study-stage-bar">';
  for (let i = 0; i < 7; i++) {
    const filled = i < s.stage;
    const cls = s.stage >= 7 ? "mastered" : filled ? "filled" : "";
    dotsHtml += `<span class="study-stage-dot ${cls}"></span>`;
  }
  dotsHtml += "</span>";
  let reviewHtml = "";
  if (s.next_review_date) {
    const nextDate = new Date(s.next_review_date + "T00:00:00");
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diffDays = Math.round((nextDate - today) / 86400000);
    let cls = "", label;
    if (s.stage >= 7) { label = "已掌握"; }
    else if (diffDays < 0) { cls = "overdue"; label = `逾期${Math.abs(diffDays)}天`; }
    else if (diffDays === 0) { cls = "today"; label = "今天复习"; }
    else if (diffDays === 1) { label = "明天复习"; }
    else { label = `${diffDays}天后复习`; }
    reviewHtml = `<span class="study-next-review ${cls}">${label}</span>`;
  }
  row.innerHTML = dotsHtml + reviewHtml;
}

function goWordbankPage(page) {
  wordbankPage = page;
  loadWordbank(false);
  wordbankCards.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderWordbankCards(data) {
  const { words, total } = data;
  const totalPages = Math.ceil(total / WORD_PAGE_SIZE);

  if (total === 0) {
    wordbankCards.innerHTML = "";
    wordbankInfo.textContent = "";
    emptyState.style.display = "block";
    wbPagination.style.display = "none";
    return;
  }

  emptyState.style.display = "none";
  wordbankInfo.textContent = `共 ${total} 个单词`;

  // Pagination
  wbPagination.style.display = totalPages > 1 ? "flex" : "none";
  wbPrev.disabled = wordbankPage <= 1;
  wbNext.disabled = wordbankPage >= totalPages;
  wbPageInfo.textContent = `${wordbankPage} / ${totalPages}`;
  wbJumpInput.max = totalPages;
  wbJumpInput.value = wordbankPage;

  const html = words
    .map(
      (w) => `
    <div class="wordbank-card" data-id="${w.id}">
      <div class="card-body">
        <div class="card-main">
          <button class="speak-btn" data-speak="${esc(w.japanese)}" data-kana="${esc(w.kana)}" title="发音">▶</button>
          <span class="card-jp">${esc(w.japanese)}</span>
          <span class="card-kana">${esc(w.kana)}</span>
          <span class="card-chinese">${esc(w.chinese)}</span>
          ${jlptBadge(w.jlpt_level)}
          ${w.image_base64
            ? `<button class="img-gen-btn has-image" data-id="${w.id}">展示图片</button>`
            : `<button class="img-gen-btn" data-id="${w.id}">生成图片</button>`
          }
        </div>
        <div class="card-example">
          <span>${esc(w.example_ja)}</span><button class="example-speak-btn" data-speak="${esc(w.example_ja)}" title="朗读例句">▶</button>
          <span class="example-cn">${esc(w.example_cn)}</span>
        </div>
        <div class="wordbank-study-row" data-word-id="${w.id}"></div>
      </div>
      <button class="delete-btn" data-id="${w.id}" title="删除">✕</button>
    </div>
  `,
    )
    .join("");

  wordbankCards.innerHTML = html;
}

function renderTopics(topics) {
  topicList.innerHTML = `<div class="topic-item ${currentTopic ? "" : "active"}" data-topic="">
    <span>全部</span>
  </div>`;

  topics.forEach((t) => {
    const div = document.createElement("div");
    div.className = `topic-item ${t.topic === currentTopic ? "active" : ""}`;
    div.dataset.topic = t.topic;
    div.innerHTML = `
      <span>${esc(t.topic)} ${jlptBadge(t.jlpt_level)} <span class="topic-count">${t.count}</span></span>
      <button class="topic-delete" data-topic="${esc(t.topic)}" title="删除词单">×</button>`;
    topicList.appendChild(div);
  });
}

topicList.addEventListener("click", async (e) => {
  const delBtn = e.target.closest(".topic-delete");
  if (delBtn) {
    e.stopPropagation();
    const topic = delBtn.dataset.topic;
    if (!confirm(`确定删除整个"${topic}"词单吗？此操作不可恢复。`)) return;
    try {
      await api.deleteTopic(topic);
      showToast(`已删除"${topic}"词单`);
      loadWordbank();
    } catch (err) {
      showToast(`删除失败：${err.message}`, "error");
    }
    return;
  }

  const item = e.target.closest(".topic-item");
  if (!item) return;

  topicList.querySelectorAll(".topic-item").forEach((b) => b.classList.remove("active"));
  item.classList.add("active");
  currentTopic = item.dataset.topic;
  loadWordbank();
});

let searchTimer;
searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    currentSearch = searchInput.value.trim();
    loadWordbank();
  }, 300);
});

wbPrev.addEventListener("click", () => {
  if (wordbankPage > 1) goWordbankPage(wordbankPage - 1);
});
wbNext.addEventListener("click", () => {
  goWordbankPage(wordbankPage + 1);
});

wbJumpInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const page = parseInt(wbJumpInput.value);
    if (page >= 1 && page <= parseInt(wbJumpInput.max)) {
      goWordbankPage(page);
    } else {
      wbJumpInput.value = wordbankPage;
    }
  }
});

wordbankCards.addEventListener("click", async (e) => {
  const speakBtn = e.target.closest(".speak-btn");
  if (speakBtn) {
    speakWord(speakBtn.dataset.speak, speakBtn.dataset.kana, speakBtn);
    return;
  }

  // 例句朗读按钮
  const exSpeakBtn = e.target.closest(".example-speak-btn");
  if (exSpeakBtn) {
    speakWord(exSpeakBtn.dataset.speak, "", exSpeakBtn);
    return;
  }

  // 生成/展示配图按钮
  const imgBtn = e.target.closest(".img-gen-btn");
  if (imgBtn) {
    const id = parseInt(imgBtn.dataset.id);
    const card = imgBtn.closest(".wordbank-card");

    // 已有图片 → 展开/收起内嵌图片（懒加载：点击时从 API 获取）
    if (imgBtn.classList.contains("has-image")) {
      const existingImg = card.querySelector(".wordbank-card-inline-img");
      if (existingImg) {
        existingImg.remove();
        imgBtn.textContent = "展示图片";
        return;
      }
      // Fetch image data on demand (lazy load)
      imgBtn.disabled = true;
      imgBtn.textContent = "加载中...";
      api.getImageCardData(id).then(data => {
        if (!data.image_base64) {
          imgBtn.textContent = "无图片";
          imgBtn.disabled = false;
          return;
        }
        const imgWrap = document.createElement("div");
        imgWrap.className = "wordbank-card-inline-img";
        imgWrap.innerHTML = `<img src="${esc(data.image_base64)}" alt="" />`;
        imgWrap.querySelector("img").addEventListener("click", () => showImageLightbox(data.image_base64));
        card.appendChild(imgWrap);
        imgBtn.textContent = "收起图片";
        imgBtn.disabled = false;
      }).catch(() => {
        imgBtn.textContent = "加载失败";
        imgBtn.disabled = false;
      });
      return;
    }

    // 生成图片（带安抚进度条）
    imgBtn.disabled = true;
    imgBtn.textContent = "生成中...";

    // 创建行内进度条
    var progressWrap = document.createElement("div");
    progressWrap.className = "img-gen-progress";
    progressWrap.innerHTML = '<div class="img-gen-progress-track"><div class="img-gen-progress-bar"></div></div><span class="img-gen-progress-text">0%</span>';
    card.appendChild(progressWrap);

    var bar = progressWrap.querySelector(".img-gen-progress-bar");
    var text = progressWrap.querySelector(".img-gen-progress-text");
    var progress = 0;
    var stalls = [0, 15, 32, 48, 67, 78, 90]; // 停顿点（含起终点）
    var stage = 0;
    var timer = null;

    function nextStage() {
      if (stage >= stalls.length - 1) return; // 已到 90%，等待 API
      var from = stalls[stage];
      var to = stalls[stage + 1];
      var steps = 8 + Math.floor(Math.random() * 12); // 8~20 小步
      var duration = 1000 + Math.random() * 2000;        // 段耗时 1~3s
      var stepSize = (to - from) / steps;
      var stepDelay = duration / steps;
      var i = 0;

      function step() {
        if (stage >= stalls.length - 1) return;
        i++;
        progress = from + stepSize * i;
        if (progress >= to) { progress = to; stage++; }
        bar.style.width = progress + "%";
        text.textContent = Math.round(progress) + "%";
        if (progress < to && progress < 90) {
          timer = setTimeout(step, stepDelay);
        } else if (stage < stalls.length - 1) {
          // 段间停顿 0.3~0.8s
          timer = setTimeout(nextStage, 600 + Math.random() * 1000);
        }
      }
      step();
    }
    nextStage();

    // Toast 提示
    var waitToast = showToast("⏳ 正在生成配图，请勿离开此页面...", "info", 0);

    // 同时发起图片生成
    api.generateWordImage(id).then(function(result) {
      clearTimeout(timer);
      progress = 100; stage = stalls.length;
      bar.style.width = "100%";
      text.textContent = "100%";
      waitToast.remove();
      setTimeout(function() { progressWrap.remove(); showToast("配图生成成功"); }, 400);
      imgBtn.disabled = false;
      imgBtn.textContent = "展示图片";
      imgBtn.classList.add("has-image");
      imgBtn.dataset.img = result.image_base64;
    }).catch(function(err) {
      clearTimeout(timer);
      waitToast.remove();
      bar.style.width = "100%";
      bar.style.background = "#ef4444";
      text.textContent = "失败";
      text.style.color = "#ef4444";
      setTimeout(function() {
        progressWrap.remove();
        imgBtn.disabled = false;
        imgBtn.textContent = "生成图片";
      }, 600);
      showToast("配图生成失败：" + err.message, "error");
    });
    return;
  }

  // 点击已生成的图片可放大查看（旧版兼容）
  const imgEl = e.target.closest(".wordbank-card-img");
  if (imgEl) {
    showImageLightbox(imgEl.src);
    return;
  }

  const delBtn = e.target.closest(".delete-btn");
  if (!delBtn) return;

  const id = parseInt(delBtn.dataset.id);
  if (!confirm("确定删除这个单词吗？")) return;

  try {
    await api.deleteWord(id);
    showToast("删除成功");
    loadWordbank();
  } catch (err) {
    showToast(`删除失败：${err.message}`, "error");
  }
});

// 图片灯箱（点击放大查看）
function showImageLightbox(src) {
  const existing = document.querySelector(".image-lightbox");
  if (existing) existing.remove();

  const lb = document.createElement("div");
  lb.className = "image-lightbox";
  lb.innerHTML = `
    <div class="image-lightbox-bg"></div>
    <img class="image-lightbox-img" src="${src}" />
    <button class="image-lightbox-close">✕</button>
  `;
  document.body.appendChild(lb);

  const close = () => lb.remove();
  lb.querySelector(".image-lightbox-bg").addEventListener("click", close);
  lb.querySelector(".image-lightbox-close").addEventListener("click", close);
  document.addEventListener("keydown", function onEsc(e) {
    if (e.key === "Escape") { close(); document.removeEventListener("keydown", onEsc); }
  });
}

// ===== 词库管理 =====
const addWordForm = $("#add-word-form");
const btnShowAddForm = $("#btn-show-add-form");
const btnAddWord = $("#btn-add-word");
const addWordTopic = $("#add-word-topic");
const addJapanese = $("#add-japanese");
const addKana = $("#add-kana");
const addChinese = $("#add-chinese");
const addExampleJa = $("#add-example-ja");
const addExampleCn = $("#add-example-cn");

btnShowAddForm.addEventListener("click", () => {
  const visible = addWordForm.style.display !== "none";
  addWordForm.style.display = visible ? "none" : "block";
  btnShowAddForm.textContent = visible ? "＋ 添加单词" : "－ 收起";
  if (!visible) populateAddTopicOptions();
});

const btnMergeDuplicates = $("#btn-merge-duplicates");
btnMergeDuplicates.addEventListener("click", async () => {
  if (!confirm("将合并词库中相同的单词（保留最早添加的），确定继续？")) return;
  try {
    const res = await api.mergeDuplicates();
    showToast(res.message);
    if (res.removed > 0) loadWordbank();
  } catch (err) {
    showToast(`合并失败：${err.message}`, "error");
  }
});

// ── PDF 导出对话框 ──
const exportModal = $("#export-modal");
const exportPanelBody = $("#export-panel-options");
const exportGeneratingEl = $("#export-generating");
const exportDoneEl = $("#export-done");
const exportFooter = $("#export-modal-footer");
const exportConfirmBtn = $("#export-modal-confirm");

let _exportWordCount = 0;
let _exportTopic = "";

function openExportDialog() {
  // Reset to options view
  exportPanelBody.style.display = "block";
  exportGeneratingEl.style.display = "none";
  exportDoneEl.style.display = "none";
  exportFooter.style.display = "flex";
  exportConfirmBtn.disabled = false;
  exportConfirmBtn.textContent = "📥 导出 PDF";

  // Reset progress bar
  $("#export-progress-fill").style.width = "0%";

  // Read current topic from sidebar
  const activeEl = document.querySelector(".topic-item.active");
  _exportTopic = activeEl ? activeEl.dataset.topic : "";
  const label = _exportTopic || "全部词单";
  // 主题名来自用户数据，必须转义防存储型 XSS（#36）
  $("#export-topic-label").innerHTML = esc(label) + ' · <span id="export-word-count">--</span> 个单词';

  // Default: table layout
  document.querySelector("input[name='export-layout'][value='table']").checked = true;
  $("#export-include-images").checked = true;
  $("#export-include-examples").checked = true;

  // Fetch word count
  const token = getToken();
  const qs = _exportTopic ? "?topic=" + encodeURIComponent(_exportTopic) + "&limit=1" : "?limit=1";
  fetch(BASE + "/words" + qs, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  }).then(r => r.json()).then(data => {
    _exportWordCount = data.total || 0;
    var countEl = $("#export-word-count");
    if (countEl) countEl.textContent = _exportWordCount;
    if (_exportWordCount === 0) {
      exportConfirmBtn.disabled = true;
      exportConfirmBtn.textContent = "没有可导出的单词";
    }
  }).catch(() => {});

  exportModal.style.display = "flex";
}

function closeExportDialog() {
  exportModal.style.display = "none";
}

$("#export-modal-close").addEventListener("click", closeExportDialog);
$("#export-modal-cancel").addEventListener("click", closeExportDialog);
exportModal.addEventListener("click", function(e) {
  if (e.target === exportModal) closeExportDialog();
});

// Progress bar animation
var _progressTimer = null;
function startProgress() {
  var w = 0;
  $("#export-progress-fill").style.width = "0%";
  _progressTimer = setInterval(function() {
    w += (100 - w) * 0.08;
    if (w > 95) w = 95;
    $("#export-progress-fill").style.width = w + "%";
  }, 200);
}
function finishProgress() {
  clearInterval(_progressTimer);
  $("#export-progress-fill").style.width = "100%";
}

// Confirm button → start export
exportConfirmBtn.addEventListener("click", function() {
  if (_exportWordCount === 0) return;

  var layout = document.querySelector("input[name='export-layout']:checked");
  layout = layout ? layout.value : "table";
  var includeImages = $("#export-include-images").checked;
  var includeExamples = $("#export-include-examples").checked;

  // Switch to loading state
  exportPanelBody.style.display = "none";
  exportGeneratingEl.style.display = "block";
  exportFooter.style.display = "none";
  var label = _exportTopic || "全部词单";
  $("#export-generating-detail").textContent = "正在导出「" + label + "」的 " + _exportWordCount + " 个单词";
  startProgress();

  var params = {};
  if (_exportTopic) params.topic = _exportTopic;
  params.layout = layout;
  params.include_images = includeImages;

  api.exportPdf("/words/export/pdf", params).then(function(result) {
    finishProgress();

    // Download
    var url = URL.createObjectURL(result.blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = result.filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    // Show done state
    exportGeneratingEl.style.display = "none";
    exportDoneEl.style.display = "block";
    exportFooter.style.display = "flex";
    exportConfirmBtn.textContent = "✅ 完成";
    exportConfirmBtn.disabled = true;

    // Auto close
    setTimeout(function() {
      if (exportModal.style.display !== "none") closeExportDialog();
    }, 2000);
  }).catch(function(err) {
    // Restore options on error
    clearInterval(_progressTimer);
    exportGeneratingEl.style.display = "none";
    exportPanelBody.style.display = "block";
    exportFooter.style.display = "flex";
    showToast("导出失败：" + err.message, "error");
  });
});

// 导出词单 PDF
$("#btn-export-pdf").addEventListener("click", openExportDialog);

async function populateAddTopicOptions() {
  try {
    const topics = await api.listTopics();
    const current = addWordTopic.value;
    addWordTopic.innerHTML = topics
      .map(
        (t) =>
          `<option value="${esc(t.topic)}" ${t.topic === current ? "selected" : ""}>${esc(t.topic)} (${t.count})</option>`,
      )
      .join("");
  } catch {}
}

btnAddWord.addEventListener("click", async () => {
  const topic = addWordTopic.value;
  const japanese = addJapanese.value.trim();
  const kana = addKana.value.trim();
  const chinese = addChinese.value.trim();
  const exampleJa = addExampleJa.value.trim();
  const exampleCn = addExampleCn.value.trim();

  if (!topic || !japanese || !kana) {
    showToast("请至少填写词单、日文汉字和假名", "error");
    return;
  }

  try {
    await api.addWord(topic, {
      japanese,
      kana,
      chinese: chinese || "-",
      example_ja: exampleJa || "-",
      example_cn: exampleCn || "-",
    });
    showToast(`已添加"${japanese}"到"${topic}"`);
    addJapanese.value = "";
    addKana.value = "";
    addChinese.value = "";
    addExampleJa.value = "";
    addExampleCn.value = "";
    loadWordbank();
  } catch (err) {
    showToast(`添加失败：${err.message}`, "error");
  }
});

// ===== 背词页 =====
const studyPick = $("#study-pick");
const studySession = $("#study-session");
const studyDone = $("#study-done");
const studyTopicGrid = $("#study-topic-grid");
const studyTopicWrap = $("#study-topic-wrap");
const btnStudyToggleTopics = $("#btn-study-toggle-topics");
const studyToggleCount = $("#study-toggle-count");
const studyStats = $("#study-stats");
const studySubtitle = $("#study-subtitle");
const btnStartStudy = $("#btn-start-study");
const modeBtns = $$(".mode-btn");
const flashcard = $("#flashcard-inner");
const flashcardFront = $("#flashcard-front");
const flashcardBack = $("#flashcard-back");
const qualityBtns = $$(".btn-quality");
const studyProgressText = $("#study-progress-text");
const studyBarFill = $("#study-bar-fill");
const studyDoneMsg = $("#study-done-msg");
const btnStudyAgain = $("#btn-study-again");
const studySubtabNew = $("#study-subtab-new");
const studySubtabReview = $("#study-subtab-review");
const studyCalendar = $("#study-calendar");
const studyCalendarGrid = $("#study-calendar-grid");
const studyCalendarNewHint = $("#study-calendar-new-hint");
const studyBadge = $("#study-badge");
const btnStudyUndo = $("#btn-study-undo");
const studySessionStats = $("#study-session-stats");
const listeningActions = $("#study-listening-actions");
const btnListeningPlay = $("#btn-listening-play");
const btnListeningReveal = $("#btn-listening-reveal");
const flashcardHint = $("#flashcard-hint");

let studyMode = "kanji2kana";
let studyWords = [];
let studyIndex = 0;
let selectedTopics = [];
let showBack = false;
let studySubTab = "new";
let studyHistory = [];    // [{word_id, quality, prevStage, newStage}, ...] 会话统计
let studyListeningAudio = false;  // 听力模式：是否已播放音频
let lastReviewResult = null;      // 最近一次评分结果，用于撤销

modeBtns.forEach((b) => {
  b.addEventListener("click", () => {
    modeBtns.forEach((mb) => mb.classList.remove("active"));
    b.classList.add("active");
    studyMode = b.dataset.mode;
  });
});

studySubtabNew.addEventListener("click", () => {
  if (studySubTab === "new") return;
  studySubTab = "new";
  studySubtabNew.classList.add("active");
  studySubtabReview.classList.remove("active");
  selectedTopics = [];
  btnStartStudy.textContent = "开始背诵";
  studyTopicGrid
    .querySelectorAll(".study-topic-card")
    .forEach((c) => c.classList.remove("selected"));
  loadStudyPick();
});

studySubtabReview.addEventListener("click", () => {
  if (studySubTab === "review") return;
  studySubTab = "review";
  studySubtabReview.classList.add("active");
  studySubtabNew.classList.remove("active");
  selectedTopics = [];
  btnStartStudy.textContent = "开始背诵";
  studyTopicGrid
    .querySelectorAll(".study-topic-card")
    .forEach((c) => c.classList.remove("selected"));
  loadStudyPick();
});

btnStudyToggleTopics.addEventListener("click", () => {
  const visible = studyTopicWrap.style.display !== "none";
  studyTopicWrap.style.display = visible ? "none" : "block";
  btnStudyToggleTopics.classList.toggle("expanded", !visible);
});

async function loadStudyPick() {
  try {
    const [topics, stats, calData] = await Promise.all([
      api.studyTopics(studySubTab),
      api.studyStats(),
      studySubTab === "review" ? api.studyCalendar(14) : Promise.resolve(null),
    ]);
    if (studySubTab === "new") {
      studyStats.innerHTML = `
        <div class="study-stat-card"><div class="study-stat-num">${stats.new_available}</div><div class="study-stat-label">可学新词</div></div>
        <div class="study-stat-card"><div class="study-stat-num">${stats.new_today}</div><div class="study-stat-label">今日可学</div></div>
        <div class="study-stat-card"><div class="study-stat-num">${stats.learned}</div><div class="study-stat-label">已学单词</div></div>
      `;
    } else {
      studyStats.innerHTML = `
        <div class="study-stat-card"><div class="study-stat-num">${stats.due_review}</div><div class="study-stat-label">今日待复习</div></div>
        <div class="study-stat-card"><div class="study-stat-num">${stats.learned}</div><div class="study-stat-label">已学单词</div></div>
        <div class="study-stat-card"><div class="study-stat-num">${stats.mastering}</div><div class="study-stat-label">已掌握</div></div>
      `;
    }

    studyToggleCount.textContent = topics.length ? `(${topics.length} 个词单)` : "";

    if (topics.length === 0) {
      btnStudyToggleTopics.style.display = "none";
      studyTopicWrap.style.display = "block";
      studyTopicGrid.innerHTML =
        '<div class="study-all-done">很棒，今天已经学完啦！～(∠・ω< )⌒☆</div>';
      btnStartStudy.disabled = true;
      btnStartStudy.textContent = studySubTab === "new" ? "没有可学词单" : "没有待复习词单";
    } else {
      btnStudyToggleTopics.style.display = "";
      btnStartStudy.disabled = false;
      btnStartStudy.textContent = "开始背诵";
      studyTopicGrid.innerHTML = topics
      .map(
        (t) => `
      <div class="study-topic-card ${selectedTopics.includes(t.topic) ? "selected" : ""}" data-topic="${esc(t.topic)}">
        <div class="stc-name">${esc(t.topic)} ${jlptBadge(t.jlpt_level)}</div>
        <div class="stc-count">${t.count} 词</div>
      </div>
    `,
      )
      .join("");

      studyTopicGrid.querySelectorAll(".study-topic-card").forEach((card) => {
        card.addEventListener("click", () => {
          card.classList.toggle("selected");
          const t = card.dataset.topic;
          if (card.classList.contains("selected")) {
            if (!selectedTopics.includes(t)) selectedTopics.push(t);
          } else {
            selectedTopics = selectedTopics.filter((x) => x !== t);
          }
          btnStartStudy.textContent = selectedTopics.length
            ? `开始背诵（已选 ${selectedTopics.length} 个词单）`
            : "开始背诵";
        });
      });
    }

    if (studySubTab === "review" && calData) {
      studyCalendar.style.display = "block";
      renderCalendar(calData);
    } else {
      studyCalendar.style.display = "none";
    }

    studySubtitle.textContent = studySubTab === "new" ? "选择词单，学习新词" : "选择词单，复习旧词";
    showStudyView("pick");
  } catch (err) {
    showToast(`加载失败：${err.message}`, "error");
  }
}

function renderCalendar(calData) {
  const today = new Date();
  const todayStr = today.toISOString().slice(0, 10);

  studyCalendarNewHint.textContent = `可学新词：${calData.new_available}`;

  studyCalendarGrid.innerHTML = calData.days
    .map((d) => {
      const dObj = new Date(d.date + "T00:00:00");
      const isToday = d.date === todayStr;
      const dayNum = dObj.getDate();
      const monthNum = dObj.getMonth() + 1;
      const diffDays = Math.round((dObj - today) / 86400000);

      let label;
      if (diffDays === 0) label = "今日";
      else if (diffDays === 1) label = "明天";
      else if (diffDays === 2) label = "后天";
      else {
        const weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
        label = weekdays[dObj.getDay()];
      }

      return `
      <div class="study-calendar-day ${isToday ? "today" : ""}">
        <div class="study-calendar-day-label">${label}</div>
        <div class="study-calendar-day-date">${monthNum}/${dayNum}</div>
        <div class="study-calendar-day-count ${d.count === 0 ? "zero" : ""}">${d.count}</div>
      </div>
    `;
    })
    .join("");
}

function showStudyView(view) {
  studyPick.style.display = view === "pick" ? "block" : "none";
  studySession.style.display = view === "session" ? "block" : "none";
  studyDone.style.display = view === "done" ? "block" : "none";
  if (view !== "session") {
    listeningActions.style.display = "none";
    flashcardHint.style.display = "";
  }
}

btnStartStudy.addEventListener("click", async () => {
  try {
    studyWords = await api.startStudy(
      selectedTopics.length ? selectedTopics : undefined,
      20,
      studySubTab,
    );
    if (studyWords.length === 0) {
      showToast("没有需要背诵的单词，你已经全部掌握了！", "error");
      return;
    }

    studyIndex = 0;
    showBack = false;
    studyHistory = [];
    lastReviewResult = null;
    btnStudyUndo.style.display = "none";
    showStudyView("session");
    renderFlashcard();
  } catch (err) {
    showToast(`开始失败：${err.message}`, "error");
  }
});

let studyReviewing = false;  // 防止连击

function renderFlashcard() {
  const w = studyWords[studyIndex];
  flashcard.classList.remove("flipped");
  showBack = false;
  studyReviewing = false;
  studyListeningAudio = false;
  btnStudyUndo.style.display = lastReviewResult ? "" : "none";
  btnStudyUndo.textContent = "↩ 返回上一个单词";

  // 听力模式：显示专用按钮，隐藏翻牌提示；其他模式反之
  if (studyMode === "listening") {
    listeningActions.style.display = "";
    flashcardHint.style.display = "none";
    flashcardFront.innerHTML = `<span style="font-size:48px">🔊</span><br><span style="font-size:14px;color:#9ca3af">听听看，想起这个单词了吗？</span>`;
    // 自动播放发音
    setTimeout(() => {
      if (!showBack && !studyListeningAudio && studySession.style.display !== "none") {
        studyListeningAudio = true;
        speakWord(w.japanese, w.kana, null);
      }
    }, 300);
  } else {
    listeningActions.style.display = "none";
    flashcardHint.style.display = "";
    if (studyMode === "kanji2kana") {
      flashcardFront.textContent = w.japanese;
    } else if (studyMode === "kana2kanji") {
      flashcardFront.textContent = w.kana;
    }
  }

  // 背面：答案 + 例句 + 进度（复习时不显示图片以免提示）
  const backMain = $("#flashcard-back-main");
  if (studyMode === "listening") {
    backMain.innerHTML = `<div class="flashcard-answer" style="font-size:28px">${esc(w.japanese)} <span style="font-size:16px;color:#9ca3af">${esc(w.kana)}</span></div><div class="flashcard-meaning">${esc(w.chinese)}</div>`;
  } else if (studyMode === "kanji2kana") {
    backMain.innerHTML = `<div class="flashcard-answer">${esc(w.kana)}</div><div class="flashcard-meaning">${esc(w.chinese)}</div>`;
  } else {
    backMain.innerHTML = `<div class="flashcard-answer">${esc(w.japanese)}</div><div class="flashcard-meaning">${esc(w.chinese)}</div>`;
  }

  // 例句
  const exampleDiv = $("#flashcard-example");
  if (w.example_ja) {
    exampleDiv.style.display = "block";
    exampleDiv.innerHTML = `<div class="flashcard-example-ja">${esc(w.example_ja)}</div><div class="flashcard-example-cn">${esc(w.example_cn)}</div>`;
  } else {
    exampleDiv.style.display = "none";
  }

  // 图片 — 复习时隐藏，避免视觉提示干扰记忆提取
  const imgDiv = $("#flashcard-img");
  const isReview = (w.stage ?? 0) > 0;
  if (w.image_base64 && !isReview) {
    imgDiv.style.display = "block";
    imgDiv.innerHTML = `<img src="${esc(w.image_base64)}" alt="${esc(w.japanese)}" />`;
    imgDiv.querySelector("img").addEventListener("click", (e) => {
      e.stopPropagation();
      showImageLightbox(w.image_base64);
    });
  } else {
    imgDiv.style.display = "none";
  }

  // 学习进度
  const infoDiv = $("#flashcard-study-info");
  const s = w.stage ?? 0;
  const dots = Array.from({length: 7}, (_, i) =>
    `<span class="study-stage-dot ${s >= 7 ? 'mastered' : i < s ? 'filled' : ''}"></span>`
  ).join("");
  infoDiv.innerHTML = `<span>阶段 ${s}/7</span><span class="study-stage-bar">${dots}</span><span>复习 ${w.review_count || 0} 次</span>`;

  // 朗读按钮
  const speakBtn = $("#flashcard-speak-btn");
  speakBtn.dataset.speak = w.japanese;
  speakBtn.dataset.kana = w.kana;

  studyProgressText.textContent = `${studyIndex + 1} / ${studyWords.length}`;
  studyBarFill.style.width = `${((studyIndex + 1) / studyWords.length) * 100}%`;

  // 启用评分按钮
  qualityBtns.forEach(b => b.disabled = false);
}

// 点击翻牌（听力模式下点击卡片也可翻牌）
let touchStartX = 0, touchStartY = 0, touchMoved = false;

flashcard.addEventListener("touchstart", (e) => {
  touchStartX = e.touches[0].clientX;
  touchStartY = e.touches[0].clientY;
  touchMoved = false;
}, { passive: true });

flashcard.addEventListener("touchmove", (e) => {
  const dx = e.touches[0].clientX - touchStartX;
  const dy = e.touches[0].clientY - touchStartY;
  if (Math.abs(dx) > 5 || Math.abs(dy) > 5) touchMoved = true;
}, { passive: true });

flashcard.addEventListener("click", () => {
  if (studyReviewing) return;
  if (touchMoved) return; // 滑动不触发点击
  if (studyMode === "listening" && !showBack) {
    revealListeningAnswer();
    return;
  }
  if (showBack) return;
  flashcard.classList.add("flipped");
  showBack = true;
  const speakBtn = $("#flashcard-speak-btn");
  speakWord(speakBtn.dataset.speak, speakBtn.dataset.kana, speakBtn);
});

// 滑动评分：背面状态下左滑=忘了(1) 右滑=掌握(5)
flashcard.addEventListener("touchend", (e) => {
  if (!showBack || studyReviewing || !touchMoved) return;
  const dx = e.changedTouches[0].clientX - touchStartX;
  if (Math.abs(dx) < 50) return; // 滑动距离不够
  if (dx > 0) {
    // 右滑 → 掌握
    recordReview(5);
  } else {
    // 左滑 → 忘了
    recordReview(1);
  }
  touchMoved = false;
});

// 听力模式：播放音频按钮
btnListeningPlay.addEventListener("click", (e) => {
  e.stopPropagation();
  const w = studyWords[studyIndex];
  studyListeningAudio = true;
  speakWord(w.japanese, w.kana, null);
  flashcardFront.innerHTML = `<span style="font-size:48px">🔊</span><br><span style="font-size:14px;color:#6366f1">正在播放… 想起来了吗？</span>`;
});

// 听力模式：显示答案按钮
btnListeningReveal.addEventListener("click", (e) => {
  e.stopPropagation();
  revealListeningAnswer();
});

function revealListeningAnswer() {
  if (studyReviewing || showBack) return;
  flashcard.classList.add("flipped");
  showBack = true;
  listeningActions.style.display = "none";
  flashcardHint.style.display = "";
  const speakBtn = $("#flashcard-speak-btn");
  speakWord(speakBtn.dataset.speak, speakBtn.dataset.kana, speakBtn);
}

// 朗读按钮
$("#flashcard-speak-btn").addEventListener("click", (e) => {
  e.stopPropagation();
  const btn = e.currentTarget;
  speakWord(btn.dataset.speak, btn.dataset.kana, btn);
});

// 评分按钮
qualityBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    if (!showBack || studyReviewing) return;  // 未翻牌或正在提交则忽略
    recordReview(parseInt(btn.dataset.quality));
  });
});

async function recordReview(quality) {
  if (studyReviewing) return;
  studyReviewing = true;
  qualityBtns.forEach(b => b.disabled = true);
  btnStudyUndo.style.display = "none";

  const w = studyWords[studyIndex];
  const prevStage = w.stage ?? 0;
  let result;
  try {
    result = await api.recordStudy(w.id, quality);
  } catch (err) {
    studyReviewing = false;
    qualityBtns.forEach(b => b.disabled = false);
    if (lastReviewResult) btnStudyUndo.style.display = "";
    showToast(`记录失败：${err.message}`, "error");
    return;
  }

  // 保存撤销信息
  lastReviewResult = {
    wordId: w.id,
    japanese: w.japanese,
    kana: w.kana,
    quality: quality,
  };

  // 记录会话历史
  studyHistory.push({
    japanese: w.japanese,
    kana: w.kana,
    quality: quality,
    prevStage: prevStage,
    newStage: result.stage,
  });
  // 更新当前单词的阶段数据
  w.stage = result.stage;
  w.review_count = (w.review_count || 0) + 1;

  // 检查成就
  if (result.new_achievements) {
    result.new_achievements.forEach(a => showToast(`🏆 ${a.name}`, "achievement"));
  }

  studyIndex++;
  if (studyIndex >= studyWords.length) {
    renderSessionStats();
    showStudyView("done");
  } else {
    renderFlashcard();
  }
}

function renderSessionStats() {
  const total = studyHistory.length;
  if (total === 0) {
    studySessionStats.innerHTML = "";
    studyDoneMsg.textContent = "本轮完成！";
    return;
  }

  const correct = studyHistory.filter(h => h.quality >= 3).length;
  const accuracy = Math.round((correct / total) * 100);
  const newlyGraduated = studyHistory.filter(h => h.prevStage <= 0 && h.newStage >= 1).length;
  const mastered = studyHistory.filter(h => h.newStage >= 7).length;

  // 评分分布
  const distLabels = ["完全忘了", "不太记得", "有点印象", "勉强正确", "比较顺畅", "完全掌握"];
  const distColors = ["#6b7280", "#b91c1c", "#c2410c", "#a16207", "#15803d", "#14532d"];
  const dist = [0, 0, 0, 0, 0, 0];
  studyHistory.forEach(h => dist[h.quality]++);

  let emoji, comment;
  if (accuracy >= 90) { emoji = "🌟"; comment = "太厉害了！"; }
  else if (accuracy >= 70) { emoji = "👍"; comment = "表现不错！"; }
  else if (accuracy >= 50) { emoji = "💪"; comment = "继续加油！"; }
  else { emoji = "📚"; comment = "多复习就会进步的！"; }

  studyDoneMsg.innerHTML = `${emoji} ${comment}<br><span style="font-size:14px;font-weight:400;color:#9ca3af">正确率 ${accuracy}% (${correct}/${total})</span>`;

  let statsHtml = '<div class="session-stats-grid">';

  // 正确率环形图（CSS实现）
  statsHtml += `
    <div class="session-stat-card">
      <div class="session-ring-wrap">
        <svg width="80" height="80" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r="34" fill="none" stroke="#e5e7eb" stroke-width="8"/>
          <circle cx="40" cy="40" r="34" fill="none" stroke="url(#grad)" stroke-width="8"
            stroke-dasharray="${(accuracy/100)*213.6} 213.6" stroke-linecap="round"
            transform="rotate(-90 40 40)" style="transition: stroke-dasharray 0.8s ease"/>
          <defs><linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#6366f1"/><stop offset="100%" stop-color="#8b5cf6"/>
          </linearGradient></defs>
          <text x="40" y="36" text-anchor="middle" font-size="18" font-weight="800" fill="#1f2937">${accuracy}%</text>
          <text x="40" y="52" text-anchor="middle" font-size="9" fill="#9ca3af">正确率</text>
        </svg>
      </div>
    </div>`;

  // 统计数字
  statsHtml += `
    <div class="session-stat-card">
      <div class="session-stat-num">${total}</div>
      <div class="session-stat-label">本轮背诵</div>
    </div>`;
  if (newlyGraduated > 0) {
    statsHtml += `
    <div class="session-stat-card">
      <div class="session-stat-num" style="color:#10b981">+${newlyGraduated}</div>
      <div class="session-stat-label">新掌握的单词</div>
    </div>`;
  }
  if (mastered > 0) {
    statsHtml += `
    <div class="session-stat-card">
      <div class="session-stat-num" style="color:#8b5cf6">${mastered}</div>
      <div class="session-stat-label">已完全掌握</div>
    </div>`;
  }
  statsHtml += '</div>';

  // 评分分布条
  statsHtml += '<div class="session-dist">';
  dist.forEach((count, i) => {
    const pct = total > 0 ? Math.round((count / total) * 100) : 0;
    statsHtml += `
      <div class="session-dist-item">
        <span class="session-dist-label">${distLabels[i]}</span>
        <div class="session-dist-bar-wrap">
          <div class="session-dist-bar" style="width:${pct}%;background:${distColors[i]}"></div>
        </div>
        <span class="session-dist-count">${count}</span>
      </div>`;
  });
  statsHtml += '</div>';

  studySessionStats.innerHTML = statsHtml;
}

// 撤销按钮
btnStudyUndo.addEventListener("click", () => undoReview());

async function undoReview() {
  if (studyReviewing || !lastReviewResult) return;
  studyReviewing = true;
  btnStudyUndo.style.display = "none";
  try {
    await api.undoStudy();
    // 回退 history
    studyHistory.pop();
    // 回退 index
    studyIndex--;
    // 清除撤销状态
    lastReviewResult = null;
    showToast("已撤销上一次评分", "info");
    // 重新渲染
    renderFlashcard();
  } catch (err) {
    studyReviewing = false;
    if (lastReviewResult) btnStudyUndo.style.display = "";
    showToast(`撤销失败：${err.message}`, "error");
  }
}

// 键盘快捷键：空格翻牌，1-6评分，Ctrl+Z撤销
document.addEventListener("keydown", (e) => {
  if (studySession.style.display === "none") return;  // 只在背诵阶段生效
  // 忽略输入框内的按键
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;

  if (e.code === "Space") {
    e.preventDefault();
    if (!showBack) {
      flashcard.click();
    }
  } else if (e.key >= "1" && e.key <= "6") {
    e.preventDefault();
    const quality = parseInt(e.key) - 1;  // 1→0, 2→1, ..., 6→5
    if (showBack && !studyReviewing) {
      recordReview(quality);
    }
  } else if (e.ctrlKey && e.key === "z") {
    e.preventDefault();
    if (lastReviewResult && !studyReviewing) {
      undoReview();
    }
  }
});

btnStudyAgain.addEventListener("click", () => {
  studyHistory = [];
  lastReviewResult = null;
  btnStudyUndo.style.display = "none";
  showStudyView("pick");
  loadStudyPick();
});

// ===== 设置页 =====
const settingSpeaker = $("#setting-speaker");
const settingSpeed = $("#setting-speed");
const settingPitch = $("#setting-pitch");
const settingIntonation = $("#setting-intonation");
const settingVolume = $("#setting-volume");
const btnPreview = $("#btn-preview");
const btnSaveSettings = $("#btn-save-settings");

const valSpeed = $("#val-speed");
const valPitch = $("#val-pitch");
const valIntonation = $("#val-intonation");
const valVolume = $("#val-volume");

const sliders = [
  { el: settingSpeed, val: valSpeed },
  { el: settingPitch, val: valPitch },
  { el: settingIntonation, val: valIntonation },
  { el: settingVolume, val: valVolume },
];

sliders.forEach(({ el, val }) => {
  el.addEventListener("input", () => {
    val.textContent = parseFloat(el.value).toFixed(2);
  });
});

async function loadSettings() {
  try {
    const [settings, speakers] = await Promise.all([
      api.getSettings(),
      api.getSpeakers(),
    ]);

    settingSpeaker.innerHTML = "";
    speakers.forEach((sp) => {
      sp.styles.forEach((st) => {
        const opt = document.createElement("option");
        opt.value = st.id;
        opt.textContent = `${sp.name} — ${st.name || st.id}`;
        if (st.id === settings.speaker) opt.selected = true;
        settingSpeaker.appendChild(opt);
      });
    });

    settingSpeed.value = settings.speed;
    settingPitch.value = settings.pitch;
    settingIntonation.value = settings.intonation;
    settingVolume.value = settings.volume;
    valSpeed.textContent = settings.speed.toFixed(2);
    valPitch.textContent = settings.pitch.toFixed(2);
    valIntonation.textContent = settings.intonation.toFixed(2);
    valVolume.textContent = settings.volume.toFixed(2);
  } catch (err) {
    showToast(`加载设置失败：${err.message}`, "error");
  }
}

btnSaveSettings.addEventListener("click", async () => {
  const data = {
    speaker: parseInt(settingSpeaker.value),
    speed: parseFloat(settingSpeed.value),
    pitch: parseFloat(settingPitch.value),
    intonation: parseFloat(settingIntonation.value),
    volume: parseFloat(settingVolume.value),
  };

  try {
    await api.saveSettings(data);
    showToast("设置已保存");
  } catch (err) {
    showToast(`保存失败：${err.message}`, "error");
  }
});

btnPreview.addEventListener("click", () => {
  btnSaveSettings.click();
  setTimeout(() => speakWord("こんにちは", "", null), 300);
});

// ===== 短文页 =====
const essayTopicGrid = $("#essay-topic-grid");
const essayTopicWrap = $("#essay-topic-wrap");
const btnEssayToggleTopics = $("#btn-essay-toggle-topics");
const essayToggleCount = $("#essay-toggle-count");
const btnGenerateEssay = $("#btn-generate-essay");
const essayWordCount = $("#essay-word-count");
const essayLevel = $("#essay-level");
const essayGenre = $("#essay-genre");
const essayTitleInput = $("#essay-title-input");
const essayLoading = $("#essay-loading");
const essayResult = $("#essay-result");
const essayTitle = $("#essay-title");
const essayContent = $("#essay-content");
const essayWordsUsed = $("#essay-words-used");
const essayTranslation = $("#essay-translation");
const btnEssayRegenerate = $("#btn-essay-regenerate");
const essayError = $("#essay-error");
const btnEssaySave = $("#btn-essay-save");
const essaySavedList = $("#essay-saved-list");
const essaySavedEmpty = $("#essay-saved-empty");
const essayWordPicker = $("#essay-word-picker");
const essayWordChips = $("#essay-word-chips");
const essayWordHint = $("#essay-word-hint");
const btnEssaySelectAll = $("#btn-essay-select-all-words");
const btnEssayDeselectAll = $("#btn-essay-deselect-all-words");
let currentEssayData = null;
let essaySelectedWords = new Set();  // Set of "japanese(kana)" strings
let essayTopicWords = [];  // [{japanese, kana, topic}]

// ===== 完型填空页 =====
const clozeTopicGrid = $("#cloze-topic-grid");
const clozeTopicWrap = $("#cloze-topic-wrap");
const btnClozeToggleTopics = $("#btn-cloze-toggle-topics");
const clozeToggleCount = $("#cloze-toggle-count");
const btnGenerateCloze = $("#btn-generate-cloze");
const clozeLength = $("#cloze-length");
const clozeLengthCustom = $("#cloze-length-custom");
const clozeLevel = $("#cloze-level");
const clozeLoading = $("#cloze-loading");
const clozeResult = $("#cloze-result");
const clozeTitle = $("#cloze-title");
const clozePassage = $("#cloze-passage");
const clozeScore = $("#cloze-score");
const clozeAnswers = $("#cloze-answers");
const clozeAnswersCard = $("#cloze-answers-card");
const clozeTranslation = $("#cloze-translation");
const clozeTranslationCard = $("#cloze-translation-card");
const clozeError = $("#cloze-error");
const btnClozeCheck = $("#btn-cloze-check");
const btnClozeReveal = $("#btn-cloze-reveal");
const btnClozeReset = $("#btn-cloze-reset");
const btnClozeSave = $("#btn-cloze-save");
const btnClozeRegenerate = $("#btn-cloze-regenerate");
const clozeWordPicker = $("#cloze-word-picker");
const clozeWordChips = $("#cloze-word-chips");
const clozeWordHint = $("#cloze-word-hint");
const btnClozeSelectAll = $("#btn-cloze-select-all-words");
const btnClozeDeselectAll = $("#btn-cloze-deselect-all-words");
const clozeSavedList = $("#cloze-saved-list");
const clozeSavedEmpty = $("#cloze-saved-empty");

let clozeSelectedTopics = [];
let clozeSelectedWords = new Set();
let clozeTopicWords = [];
let currentClozeData = null;
let clozeLastConfig = null;
let clozeUserAnswers = {};

btnClozeToggleTopics.addEventListener("click", () => {
  const visible = clozeTopicWrap.style.display !== "none";
  clozeTopicWrap.style.display = visible ? "none" : "block";
  btnClozeToggleTopics.classList.toggle("expanded", !visible);
});

clozeLength.addEventListener("change", () => {
  clozeLengthCustom.style.display = clozeLength.value === "custom" ? "block" : "none";
});

btnGenerateCloze.addEventListener("click", () => doGenerateCloze());
btnClozeCheck.addEventListener("click", () => checkClozeAnswers());
btnClozeReveal.addEventListener("click", () => revealClozeAnswers());
btnClozeReset.addEventListener("click", () => resetCloze());
btnClozeSave.addEventListener("click", () => saveClozeResult());
btnClozeRegenerate.addEventListener("click", () => doGenerateCloze());

btnEssayToggleTopics.addEventListener("click", () => {
  const visible = essayTopicWrap.style.display !== "none";
  essayTopicWrap.style.display = visible ? "none" : "block";
  btnEssayToggleTopics.classList.toggle("expanded", !visible);
});

async function loadEssayPick() {
  try {
    const topics = await api.listTopics();

    essayToggleCount.textContent = topics.length ? `(${topics.length} 个词单)` : "";

    essayTopicGrid.innerHTML = topics
      .map(
        (t) => `
      <div class="essay-topic-card ${essaySelectedTopics.includes(t.topic) ? "selected" : ""}" data-topic="${esc(t.topic)}">
        <div class="stc-name">${esc(t.topic)} ${jlptBadge(t.jlpt_level)}</div>
        <div class="stc-count">${t.count} 词</div>
      </div>
    `,
      )
      .join("");

    essayTopicGrid.querySelectorAll(".essay-topic-card").forEach((card) => {
      card.addEventListener("click", () => {
        card.classList.toggle("selected");
        const t = card.dataset.topic;
        if (card.classList.contains("selected")) {
          if (!essaySelectedTopics.includes(t)) essaySelectedTopics.push(t);
        } else {
          essaySelectedTopics = essaySelectedTopics.filter((x) => x !== t);
        }
        btnGenerateEssay.disabled = essaySelectedTopics.length === 0;
        btnGenerateEssay.textContent = essaySelectedTopics.length
          ? `生成短文（已选 ${essaySelectedTopics.length} 个词单）`
          : "生成短文";
        refreshEssayWordPicker();
      });
    });
  } catch (err) {
    showToast(`加载词单失败：${err.message}`, "error");
  }
}

async function refreshEssayWordPicker() {
  if (essaySelectedTopics.length === 0) {
    essayWordPicker.style.display = "none";
    essayTopicWords = [];
    essaySelectedWords.clear();
    return;
  }

  try {
    // Fetch words for all selected topics
    const allWords = [];
    for (const topic of essaySelectedTopics) {
      const data = await api.listWords({ topic, limit: 200 });
      for (const w of data.words) {
        allWords.push({ japanese: w.japanese, kana: w.kana, chinese: w.chinese, topic: w.topic });
      }
    }

    essayTopicWords = allWords;

    if (allWords.length === 0) {
      essayWordPicker.style.display = "none";
      essaySelectedWords.clear();
      return;
    }

    // Default: select all words
    const defaultWordKeys = allWords.map((w) => `${w.japanese}(${w.kana})`);
    essaySelectedWords = new Set(defaultWordKeys);

    renderEssayWordChips();
    essayWordPicker.style.display = "block";
  } catch (err) {
    console.error("加载单词列表失败:", err);
    essayWordPicker.style.display = "none";
  }
}

function renderEssayWordChips() {
  const allKeys = essayTopicWords.map((w) => `${w.japanese}(${w.kana})`);
  const total = allKeys.length;
  const selected = essaySelectedWords.size;

  essayWordHint.textContent = `（已选 ${selected} / ${total} 个）`;
  essayWordChips.innerHTML = essayTopicWords
    .map((w) => {
      const key = `${w.japanese}(${w.kana})`;
      const sel = essaySelectedWords.has(key) ? " selected" : "";
      return `<span class="essay-word-chip${sel}" data-key="${esc(key)}">
        ${esc(w.japanese)}<span class="chip-kana">${esc(w.kana)}</span>
        <span style="font-size:11px;color:var(--text-muted);margin-left:4px">${esc(w.chinese)}</span>
      </span>`;
    })
    .join("");

  essayWordChips.querySelectorAll(".essay-word-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const key = chip.dataset.key;
      if (essaySelectedWords.has(key)) {
        essaySelectedWords.delete(key);
        chip.classList.remove("selected");
      } else {
        essaySelectedWords.add(key);
        chip.classList.add("selected");
      }
      essayWordHint.textContent = `（已选 ${essaySelectedWords.size} / ${essayTopicWords.length} 个）`;
      updateEssayGenerateBtn();
    });
  });

  updateEssayGenerateBtn();
}

function updateEssayGenerateBtn() {
  const hasTopics = essaySelectedTopics.length > 0;
  btnGenerateEssay.disabled = !hasTopics;
  if (hasTopics) {
    const extra = essaySelectedWords.size < essayTopicWords.length ? ` (${essaySelectedWords.size}词)` : "";
    btnGenerateEssay.textContent = `生成短文（已选 ${essaySelectedTopics.length} 个词单${extra}）`;
  } else {
    btnGenerateEssay.textContent = "生成短文";
  }
}

btnEssaySelectAll.addEventListener("click", () => {
  essaySelectedWords = new Set(essayTopicWords.map((w) => `${w.japanese}(${w.kana})`));
  essayWordChips.querySelectorAll(".essay-word-chip").forEach((c) => c.classList.add("selected"));
  essayWordHint.textContent = `（已选 ${essaySelectedWords.size} / ${essayTopicWords.length} 个）`;
  updateEssayGenerateBtn();
});

btnEssayDeselectAll.addEventListener("click", () => {
  essaySelectedWords.clear();
  essayWordChips.querySelectorAll(".essay-word-chip").forEach((c) => c.classList.remove("selected"));
  essayWordHint.textContent = `（已选 0 / ${essayTopicWords.length} 个）`;
  updateEssayGenerateBtn();
});

btnGenerateEssay.addEventListener("click", () => doGenerateEssay());

async function doGenerateEssay() {
  if (essaySelectedTopics.length === 0) return;

  btnGenerateEssay.disabled = true;
  essayLoading.style.display = "block";
  essayResult.style.display = "none";
  essayError.style.display = "none";

  const wordCount = parseInt(essayWordCount.value);
  const level = essayLevel.value;
  const genre = essayGenre.value;
  const customTitle = essayTitleInput.value.trim();
  essayLastConfig = { topics: [...essaySelectedTopics], wordCount, level, genre, customTitle };

  try {
    const words = essaySelectedWords.size > 0 ? [...essaySelectedWords] : null;
    await runStreamToPreview("/essay", {
      topics: essaySelectedTopics, words, word_count: wordCount, jlpt_level: level,
      genre: genre || undefined, title: customTitle || undefined, stream: true,
    }, "essay-stream-preview", {
      onDone: (result) => {
        renderEssayResult(result);
        essayLoading.style.display = "none";
        essayResult.style.display = "block";
        essayResult.scrollIntoView({ behavior: "smooth" });
      },
      onError: (msg) => { throw new Error(msg); },
    });
  } catch (err) {
    essayLoading.style.display = "none";
    essayError.style.display = "block";
    essayError.textContent = `生成失败：${err.message}`;
    showToast("短文生成失败，请重试", "error");
  } finally {
    btnGenerateEssay.disabled = false;
  }
}

function renderEssayResult(data) {
  currentEssayData = data;
  btnEssaySave.style.display = "";
  essayTitle.textContent = data.title;

  let essayHtml = esc(data.essay);
  essayHtml = essayHtml.replace(/【(.+?)】/g, '<span class="essay-vocab-highlight">$1</span>');
  essayContent.innerHTML = essayHtml;

  essayWordsUsed.innerHTML = data.words_used
    .map((w) => `<span class="essay-word-tag">${esc(w)}</span>`)
    .join("");

  essayTranslation.textContent = data.chinese_translation;
}

btnEssayRegenerate.addEventListener("click", () => {
  doGenerateEssay();
});

btnEssaySave.addEventListener("click", () => saveCurrentEssay());

async function saveCurrentEssay() {
  if (!currentEssayData) return;
  const config = essayLastConfig || { topics: [], wordCount: 300 };
  try {
    await api.saveEssay({
      title: currentEssayData.title,
      content: currentEssayData.essay,
      chinese_translation: currentEssayData.chinese_translation,
      words_used: currentEssayData.words_used,
      topics: config.topics,
      word_count: config.wordCount,
      jlpt_level: config.level || "N3",
    });
    showToast("短文已保存");
    btnEssaySave.style.display = "none";
    loadSavedEssays();
  } catch (err) {
    showToast(`保存失败：${err.message}`, "error");
  }
}

async function loadSavedEssays() {
  try {
    const data = await api.listEssays(0, 50);
    renderSavedItems("essay", data.essays || [], essaySavedList, essaySavedEmpty, (e) => ({
      id: e.id, title: e.title,
      meta: `${jlptBadge(e.jlpt_level)} · ${e.word_count}字 · ${esc((e.topics||[]).join(", "))}`,
      date: e.created_at ? e.created_at.slice(0, 10) : "",
      preview: esc(e.content.slice(0, 80)),
      body: esc(e.content),
      translation: esc(e.chinese_translation),
      type: "essay",
    }));
  } catch (err) {
    console.error("加载已保存短文失败:", err);
  }
}

function viewSavedEssay(essays, id) {
  const e = essays.find((x) => x.id === id);
  if (!e) return;
  currentEssayData = {
    title: e.title,
    essay: e.content,
    chinese_translation: e.chinese_translation,
    words_used: e.words_used,
  };
  essayLastConfig = { topics: e.topics, wordCount: e.word_count, level: e.jlpt_level };
  renderEssayResult(currentEssayData);
  essayResult.style.display = "block";
  essayResult.scrollIntoView({ behavior: "smooth" });
}

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

// ===== 语法页 =====
const grammarAnalyzeInput = $("#grammar-analyze-input");
const grammarCorrectInput = $("#grammar-correct-input");
const grammarCompareInput = $("#grammar-compare-input");
const btnGrammarAnalyze = $("#btn-grammar-analyze");
const btnGrammarCorrect = $("#btn-grammar-correct");
const btnGrammarCompare = $("#btn-grammar-compare");

let grammarSubTab = "analyze";
let currentCompareData = null;  // { topic, summary, rows }

function switchGrammarTab(tab) {
  grammarSubTab = tab;
  ["analyze", "correct", "compare"].forEach((t) => {
    $(`#grammar-subtab-${t}`).classList.toggle("active", t === tab);
    $(`#grammar-panel-${t}`).style.display = t === tab ? "block" : "none";
  });
}

$("#grammar-subtab-analyze").addEventListener("click", () => switchGrammarTab("analyze"));
$("#grammar-subtab-correct").addEventListener("click", () => switchGrammarTab("correct"));
$("#grammar-subtab-compare").addEventListener("click", () => switchGrammarTab("compare"));

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

// ── 语法分析 ──
btnGrammarAnalyze.addEventListener("click", async () => {
  const sentence = grammarAnalyzeInput.value.trim();
  if (!sentence) return;

  btnGrammarAnalyze.disabled = true;
  const loadingEl = $("#grammar-analyze-loading");
  loadingEl.style.display = "block";
  $("#grammar-analyze-result").style.display = "none";
  $("#grammar-analyze-error").style.display = "none";

  try {
    await runStreamToPreview("/grammar/analyze", { sentence, stream: true }, "grammar-analyze-stream-preview", {
      onDone: (result) => {
        $("#grammar-points-list").innerHTML = result.points
          .map(
            (p) => `
          <div class="grammar-point-card">
        <div class="gp-header">
          <span class="gp-name">${escHtml(p.grammar)}</span>
          <span class="gp-level">${escHtml(p.level)}</span>
          <span class="gp-meaning">${escHtml(p.meaning)}</span>
        </div>
        <div class="gp-explain">${escHtml(p.explanation)}</div>
        ${p.example ? `<div class="gp-example">📝 ${escHtml(p.example)}<br>💬 ${escHtml(p.example_cn)}</div>` : ""}
      </div>`,
          )
          .join("");
        loadingEl.style.display = "none";
        $("#grammar-analyze-result").style.display = "block";
      },
      onError: (msg) => { throw new Error(msg); },
    });
  } catch (err) {
    loadingEl.style.display = "none";
    $("#grammar-analyze-error").style.display = "block";
    $("#grammar-analyze-error").textContent = `分析失败：${err.message}`;
    showToast("语法分析失败，请重试", "error");
  } finally {
    btnGrammarAnalyze.disabled = false;
  }
});

grammarAnalyzeInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") btnGrammarAnalyze.click();
});

// ── 语法纠错 ──
btnGrammarCorrect.addEventListener("click", async () => {
  const sentence = grammarCorrectInput.value.trim();
  if (!sentence) return;

  btnGrammarCorrect.disabled = true;
  const loadingEl = $("#grammar-correct-loading");
  loadingEl.style.display = "block";
  $("#grammar-correct-result").style.display = "none";
  $("#grammar-correct-error").style.display = "none";

  try {
    await runStreamToPreview("/grammar/correct", { sentence, stream: true }, "grammar-correct-stream-preview", {
      onDone: (result) => {
        const data = result;
        let errorsHtml = "";
        if (data.errors.length === 0) {
          errorsHtml = '<div class="no-errors-badge">✓ 句子完全正确，没有语法错误</div>';
        } else {
          errorsHtml =
            '<h3 style="margin-bottom:8px">发现 ' +
            data.errors.length +
            " 处问题：</h3>" +
            data.errors
              .map(
                (e) => `
          <div class="grammar-error-item">
            <span class="ge-type">${escHtml(e.type)}</span>
            <strong>${escHtml(e.fragment)}</strong> — ${escHtml(e.description)}
            <br><em>→ ${escHtml(e.suggestion)}</em>
          </div>`,
              )
              .join("");
        }

        $("#grammar-correct-card").innerHTML = `
          <div class="gc-original">
            <strong>原文：</strong>${escHtml(data.original)}
          </div>
          <div class="gc-corrected">
            <strong>改正：</strong><span class="gc-text">${escHtml(data.corrected)}</span>
          </div>
          ${errorsHtml}
        `;
        loadingEl.style.display = "none";
        $("#grammar-correct-result").style.display = "block";
      },
      onError: (msg) => { throw new Error(msg); },
    });
  } catch (err) {
    loadingEl.style.display = "none";
    $("#grammar-correct-error").style.display = "block";
    $("#grammar-correct-error").textContent = `纠错失败：${err.message}`;
    showToast("语法纠错失败，请重试", "error");
  } finally {
    btnGrammarCorrect.disabled = false;
  }
});

grammarCorrectInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") btnGrammarCorrect.click();
});

// ── 语法辨析 ──
btnGrammarCompare.addEventListener("click", async () => {
  const topic = grammarCompareInput.value.trim();
  if (!topic) return;

  btnGrammarCompare.disabled = true;
  const loadingEl = $("#grammar-compare-loading");
  loadingEl.style.display = "block";
  $("#grammar-compare-result").style.display = "none";
  $("#grammar-compare-error").style.display = "none";

  try {
    await runStreamToPreview("/grammar/compare", { topic, stream: true }, "grammar-compare-stream-preview", {
      onDone: (result) => {
        const data = result;
        currentCompareData = { topic: data.topic, summary: data.summary, rows: data.rows };
        const saveBtn = $("#btn-grammar-save-compare");
        saveBtn.disabled = false;
        saveBtn.textContent = "保存结果";
        $("#grammar-compare-topic-label").textContent = `「${data.topic}」辨析`;
        $("#grammar-compare-summary").innerHTML = `<strong>📋 总结：</strong>${escHtml(data.summary)}`;
        $("#grammar-compare-table").innerHTML = `
          <thead>
            <tr>
              <th>语法</th>
              <th>接续</th>
              <th>含义</th>
              <th>例句</th>
            </tr>
          </thead>
          <tbody>
            ${data.rows
              .map(
                (r) => `
          <tr>
            <td><strong>${escHtml(r.grammar)}</strong></td>
            <td class="gct-pattern">${escHtml(r.pattern)}</td>
            <td>${escHtml(r.meaning)}</td>
            <td>${escHtml(r.example)}<br><small>${escHtml(r.example_cn)}</small></td>
          </tr>`,
              )
              .join("")}
          </tbody>
        `;
        loadingEl.style.display = "none";
        $("#grammar-compare-result").style.display = "block";
      },
      onError: (msg) => { throw new Error(msg); },
    });
  } catch (err) {
    loadingEl.style.display = "none";
    $("#grammar-compare-error").style.display = "block";
    $("#grammar-compare-error").textContent = `辨析失败：${err.message}`;
    showToast("语法辨析失败，请重试", "error");
  } finally {
    btnGrammarCompare.disabled = false;
  }
});

grammarCompareInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") btnGrammarCompare.click();
});

// ── 保存语法辨析 ──
$("#btn-grammar-save-compare").addEventListener("click", async () => {
  if (!currentCompareData) return;
  const btn = $("#btn-grammar-save-compare");
  btn.disabled = true;
  btn.textContent = "保存中...";
  try {
    await api.saveGrammarCompare(
      currentCompareData.topic,
      JSON.stringify({ summary: currentCompareData.summary, rows: currentCompareData.rows }),
    );
    btn.textContent = "已保存";
    showToast('保存完毕，请在「语法」查看');
  } catch (err) {
    btn.disabled = false;
    btn.textContent = "保存结果";
    showToast(`保存失败：${err.message}`, "error");
  }
});

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

// ── 成就页 ──
async function loadAchievements() {
  try {
    const data = await api.listAchievements();
    const items = data.achievements;
    const categories = data.categories || {};

    const achieved = items.filter((a) => a.achieved).length;
    $("#achievement-stats-row").innerHTML = `
      <div class="achievement-stat">
        <div class="achievement-stat-num">${achieved}</div>
        <div class="achievement-stat-label">已解锁</div>
      </div>
      <div class="achievement-stat">
        <div class="achievement-stat-num">${items.length - achieved}</div>
        <div class="achievement-stat-label">未解锁</div>
      </div>
    `;

    // Group by category
    const grouped = {};
    const catOrder = [];
    for (const a of items) {
      if (!grouped[a.category]) {
        grouped[a.category] = [];
        catOrder.push(a.category);
      }
      grouped[a.category].push(a);
    }

    $("#achievement-grid").innerHTML = catOrder
      .map((cat) => {
        const label = categories[cat] || cat;
        const catAchieved = grouped[cat].filter((a) => a.achieved).length;
        const catTotal = grouped[cat].length;
        const cards = grouped[cat]
          .map((a) => {
            const dateStr = a.achieved_at ? a.achieved_at.slice(0, 10) : "";
            return `
          <div class="achievement-card ${a.achieved ? "" : "locked"}">
            <div class="achievement-icon">${a.icon}</div>
            <div class="achievement-name">${esc(a.name)}</div>
            <div class="achievement-desc">${esc(a.description)}</div>
            ${a.achieved ? `<div class="achievement-date">${dateStr}</div>` : '<div class="achievement-date" style="color:var(--text-muted)">未解锁</div>'}
          </div>`;
          })
          .join("");
        return `
        <div class="achievement-category expanded">
          <div class="achievement-cat-header" data-action="toggle-cat">
            <span class="achievement-cat-header-left">
              <span class="achievement-cat-arrow">▶</span>
              <span>${label}</span>
            </span>
            <span class="achievement-cat-progress">${catAchieved}/${catTotal}</span>
          </div>
          <div class="achievement-cat-cards">${cards}</div>
        </div>`;
      })
      .join("");

    // Click handler for category collapse/expand
    $("#achievement-grid").querySelectorAll('[data-action="toggle-cat"]').forEach((header) => {
      header.addEventListener("click", () => {
        header.parentElement.classList.toggle("expanded");
      });
    });
  } catch (err) {
    showToast(`加载成就失败：${err.message}`, "error");
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

// ===== 管理员页 =====
const adminCardsGrid = $("#admin-cards-grid");
const adminTabUsers = $("#admin-tab-users");
const adminTabLogins = $("#admin-tab-logins");
const adminPanelUsers = $("#admin-panel-users");
const adminPanelLogins = $("#admin-panel-logins");
const adminLoginReports = $("#admin-login-reports");

let adminUsersCache = [];

adminTabUsers.addEventListener("click", () => switchAdminTab("users"));
adminTabLogins.addEventListener("click", () => switchAdminTab("logins"));

// 管理员创建用户
$("#btn-admin-create-user").addEventListener("click", async () => {
  const uname = prompt("请输入新用户名（2-50个字符）：");
  if (!uname) return;
  if (uname.length < 2 || uname.length > 50) { showToast("用户名需2-50个字符", "error"); return; }
  const pw1 = prompt("请输入密码（至少6位）：");
  if (!pw1) return;
  if (pw1.length < 6) { showToast("密码至少6位", "error"); return; }
  const pw2 = prompt("请再次输入密码确认：");
  if (pw1 !== pw2) { showToast("两次密码不一致", "error"); return; }
  try {
    const res = await api.adminCreateUser(uname, pw1);
    showToast(res.message);
    loadAdmin();
  } catch (err) {
    showToast(`创建失败：${err.message}`, "error");
  }
});

function switchAdminTab(tab) {
  adminTabUsers.classList.toggle("active", tab === "users");
  adminTabLogins.classList.toggle("active", tab === "logins");
  adminPanelUsers.style.display = tab === "users" ? "block" : "none";
  adminPanelLogins.style.display = tab === "logins" ? "block" : "none";
  if (tab === "users") renderAdminCards();
  if (tab === "logins") loadAdminLogins();
}

async function loadAdminLogins() {
  try {
    const reports = await api.adminLoginHistory();
    if (!reports || reports.length === 0) {
      adminLoginReports.innerHTML =
        '<div class="empty-state"><div class="empty-icon">📭</div><p>暂无登录记录</p></div>';
      return;
    }

    let html = "";
    reports.forEach((r) => {
      html += `
      <div class="login-report-card">
        <div class="login-report-header" data-user="${r.user_id}">
          <div class="login-report-user">
            <span class="login-report-avatar">👤</span>
            <div>
              <div class="login-report-username">${esc(r.username)}</div>
              <div class="login-report-meta">
                共 <strong>${r.login_count}</strong> 次登录 ·
                首次 ${formatDate(r.first_login)} ·
                最近 ${formatDate(r.last_login)}
              </div>
            </div>
          </div>
          <span class="login-report-toggle">▶</span>
        </div>
        <div class="login-report-body" style="display:none">
          <table class="admin-table login-table">
            <thead>
              <tr><th>#</th><th>登录时间</th><th>IP 地址</th></tr>
            </thead>
            <tbody>
              ${r.logins.map((l, i) => `
                <tr>
                  <td>${i + 1}</td>
                  <td>${formatDateTime(l.login_at)}</td>
                  <td>${esc(l.ip_address || "N/A")}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </div>`;
    });

    adminLoginReports.innerHTML = html;

    // 点击展开/折叠
    adminLoginReports.querySelectorAll(".login-report-header").forEach((hdr) => {
      hdr.addEventListener("click", () => {
        const body = hdr.nextElementSibling;
        const toggle = hdr.querySelector(".login-report-toggle");
        const visible = body.style.display !== "none";
        body.style.display = visible ? "none" : "block";
        toggle.textContent = visible ? "▶" : "▼";
      });
    });
  } catch (err) {
    adminLoginReports.innerHTML =
      `<div class="error-msg">加载失败：${esc(err.message)}</div>`;
  }
}

function formatDateTime(isoStr) {
  if (!isoStr) return "N/A";
  const d = new Date(isoStr);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function formatDate(isoStr) {
  if (!isoStr) return "N/A";
  const d = new Date(isoStr);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
}

async function loadAdmin() {
  try {
    const stats = await api.adminStats();
    $("#stat-users").textContent = stats.total_users;
    $("#stat-words").textContent = stats.total_words;
    $("#stat-ai").textContent = stats.total_ai_calls;
    $("#stat-tokens").textContent = formatTokens(stats.total_tokens);

    const users = await api.adminUsers();
    adminUsersCache = users;
    renderAdminCards();
  } catch (err) {
    showToast(`加载管理页失败：${err.message}`, "error");
  }
}

function formatTokens(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
  if (n >= 1000) return (n / 1000).toFixed(1) + "K";
  return String(n);
}

function effectiveLimit(dbValue, defaultValue) {
  if (dbValue !== null && dbValue !== undefined) return dbValue;
  return defaultValue;
}

function formatLimit(v, effectiveDefault) {
  const eff = effectiveLimit(v, effectiveDefault);
  if (eff === null || eff === undefined) return "不限";
  return String(eff) + "/天";
}

function limitUsageClass(used, limit) {
  if (limit === null || limit === undefined || limit <= 0) return "";
  if (used >= limit) return "full";
  if (used / limit >= 0.8) return "warn";
  return "";
}

function limitBarPct(used, limit) {
  if (!limit) return 0;
  return Math.min(100, (used / limit) * 100);
}

function renderLimitRow(opts) {
  const { icon, label, used, total, limit, effectiveDefault, kind, selectOptions } = opts;
  const eff = effectiveLimit(limit, effectiveDefault);
  const pct = limitBarPct(used, eff);
  const barClass = limitUsageClass(used, eff);
  const usedClass = limitUsageClass(used, eff);

  const usedDisplay = eff != null ? `${used}<span class="dim"> / ${eff}</span>` : `${used}<span class="dim"> / 不限</span>`;
  const countLabel = total != null ? `<span class="dim">总${total}</span>` : "";

  return `
    <div class="admin-limit-row">
      <span class="admin-limit-icon">${icon}</span>
      <span class="admin-limit-label">${label}</span>
      <div class="admin-limit-bar-wrap">
        <div class="admin-limit-bar-fill ${barClass}" style="width:${pct}%"></div>
      </div>
      <span class="admin-limit-usage">
        <span class="${usedClass}">${usedDisplay}</span>
        ${countLabel}
      </span>
      <select class="admin-limit-select" data-kind="${kind}" data-userid="${opts.userId}" data-username="${opts.username}">
        <option value="">设置</option>
        ${selectOptions.map(o => `<option value="${o.val}">${o.label}</option>`).join("")}
      </select>
    </div>`;
}

function renderAdminCards() {
  const grid = adminCardsGrid;
  const users = adminUsersCache;

  // Limit preset options
  const aiOptions = [
    { val: "0", label: "AI: 0次" },
    { val: "10", label: "AI: 10次" },
    { val: "25", label: "AI: 25次" },
    { val: "50", label: "AI: 50次" },
    { val: "100", label: "AI: 100次" },
    { val: "-1", label: "AI: 不限" },
  ];
  const voiceOptions = [
    { val: "0", label: "语音: 0次" },
    { val: "20", label: "语音: 20次" },
    { val: "50", label: "语音: 50次" },
    { val: "100", label: "语音: 100次" },
    { val: "-1", label: "语音: 不限" },
  ];
  const wordOptions = [
    { val: "0", label: "单词: 0个" },
    { val: "50", label: "单词: 50个" },
    { val: "100", label: "单词: 100个" },
    { val: "200", label: "单词: 200个" },
    { val: "500", label: "单词: 500个" },
    { val: "-1", label: "单词: 不限" },
  ];
  const imageOptions = [
    { val: "0", label: "图片: 0张" },
    { val: "3", label: "图片: 3张" },
    { val: "10", label: "图片: 10张" },
    { val: "30", label: "图片: 30张" },
    { val: "-1", label: "图片: 不限" },
  ];

  grid.innerHTML = users.map((u) => {
    const usage = u.usage || {};
    const aid = u.id;
    const unm = esc(u.username);

    return `
    <div class="admin-user-card">
      <div class="admin-card-header">
        <div class="admin-card-user">
          <span class="admin-card-avatar">${u.is_admin ? "🛡" : "👤"}</span>
          <span class="admin-card-username">${unm}</span>
          <span class="admin-card-role ${u.is_admin ? "admin" : "user"}">${u.is_admin ? "管理员" : "用户"}</span>
        </div>
        <div class="admin-card-meta">
          <span>ID:${aid}</span>
          <span>单词:${u.word_count}</span>
          <span>学习:${u.study_count}</span>
        </div>
      </div>
      <div class="admin-card-remark" data-userid="${aid}">
        <span class="admin-card-remark-text">${u.remark ? esc(u.remark) : '<span class="dim">无备注</span>'}</span>
        <button class="admin-card-remark-edit" data-action="edit-remark" data-id="${aid}" data-username="${unm}" data-remark="${u.remark ? esc(u.remark) : ''}">✎</button>
      </div>
      <div class="admin-card-body">
        ${renderLimitRow({
          icon: "🤖", label: "AI调用", kind: "ai",
          used: usage.today_ai || 0, total: usage.total_ai || 0,
          limit: u.daily_ai_limit, effectiveDefault: u.is_admin ? null : 25,
          userId: aid, username: unm, selectOptions: aiOptions,
        })}
        ${renderLimitRow({
          icon: "🎤", label: "语音", kind: "voice",
          used: usage.today_voice || 0, total: usage.total_voice || 0,
          limit: u.daily_voice_limit, effectiveDefault: null,
          userId: aid, username: unm, selectOptions: voiceOptions,
        })}
        ${renderLimitRow({
          icon: "📝", label: "单词", kind: "word",
          used: usage.today_word || 0, total: usage.total_word || 0,
          limit: u.daily_word_limit, effectiveDefault: u.is_admin ? null : 100,
          userId: aid, username: unm, selectOptions: wordOptions,
        })}
        ${renderLimitRow({
          icon: "🖼", label: "图片", kind: "image",
          used: usage.today_image || 0, total: usage.total_image || 0,
          limit: u.daily_image_limit, effectiveDefault: u.is_admin ? null : 3,
          userId: aid, username: unm, selectOptions: imageOptions,
        })}
      </div>
      <div class="admin-card-actions">
        <button class="btn btn-outline btn-sm" data-action="toggle-admin" data-id="${aid}" data-username="${unm}" data-current="${u.is_admin}">
          ${u.is_admin ? "取消管理" : "设为管理"}
        </button>
        <button class="btn btn-outline btn-sm" data-action="reset-password" data-id="${aid}" data-username="${unm}">重置密码</button>
        <button class="btn-sm-danger" data-action="delete-user" data-id="${aid}" data-username="${unm}">删除</button>
      </div>
    </div>`;
  }).join("");

  // Toggle admin
  grid.querySelectorAll('[data-action="toggle-admin"]').forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = parseInt(btn.dataset.id);
      const username = btn.dataset.username;
      if (!confirm(`确定修改 ${username} 的管理员状态吗？`)) return;
      try {
        const res = await api.toggleAdmin(id);
        showToast(res.message);
        loadAdmin();
      } catch (err) {
        showToast(`操作失败：${err.message}`, "error");
      }
    });
  });

  // Reset password
  grid.querySelectorAll('[data-action="reset-password"]').forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = parseInt(btn.dataset.id);
      const username = btn.dataset.username;
      const pw1 = prompt(`请输入「${username}」的新密码（至少6位）：`);
      if (!pw1) return;
      if (pw1.length < 6) { showToast("密码至少需要6位", "error"); return; }
      const pw2 = prompt("请再次输入新密码确认：");
      if (!pw2) return;
      if (pw1 !== pw2) { showToast("两次输入的密码不一致", "error"); return; }
      try {
        const res = await api.resetUserPassword(id, pw1);
        showToast(res.message);
      } catch (err) {
        showToast(`重置失败：${err.message}`, "error");
      }
    });
  });

  // Delete user
  grid.querySelectorAll('[data-action="delete-user"]').forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = parseInt(btn.dataset.id);
      const username = btn.dataset.username;
      if (!confirm(`确定删除用户「${username}」及其所有数据吗？此操作不可恢复！`)) return;
      try {
        const res = await api.deleteUser(id);
        showToast(res.message);
        loadAdmin();
      } catch (err) {
        showToast(`删除失败：${err.message}`, "error");
      }
    });
  });

  // Edit remark
  grid.querySelectorAll('[data-action="edit-remark"]').forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = parseInt(btn.dataset.id);
      const username = btn.dataset.username;
      const current = btn.dataset.remark || "";
      const remark = prompt(`「${username}」的备注（最多200字）：`, current);
      if (remark === null) return; // cancelled
      if (remark.length > 200) { showToast("备注不能超过200字", "error"); return; }
      try {
        await api.setUserRemark(id, remark || null);
        showToast("备注已更新");
        loadAdmin();
      } catch (err) {
        showToast(`备注保存失败：${err.message}`, "error");
      }
    });
  });

  // Set limits — per-row select
  grid.querySelectorAll('.admin-limit-select').forEach((sel) => {
    sel.addEventListener("change", async () => {
      const val = sel.value;
      if (!val) return;
      const kind = sel.dataset.kind;
      const limitVal = val === "-1" ? null : parseInt(val);
      const userId = parseInt(sel.dataset.userid);
      const username = sel.dataset.username;

      const user = adminUsersCache.find((u) => u.id === userId);
      if (!user) return;

      const aiLimit = kind === "ai" ? limitVal : user.daily_ai_limit;
      const voiceLimit = kind === "voice" ? limitVal : user.daily_voice_limit;
      const wordLimit = kind === "word" ? limitVal : user.daily_word_limit;
      const imageLimit = kind === "image" ? limitVal : user.daily_image_limit;

      try {
        // Use extended setUserLimits with image support
        await request("/admin/users/" + userId + "/limits", {
          method: "PUT",
          body: JSON.stringify({
            daily_ai_limit: aiLimit,
            daily_voice_limit: voiceLimit,
            daily_word_limit: wordLimit,
            daily_image_limit: imageLimit,
          }),
        });
        showToast(`已更新 ${username} 的限额`);
        sel.value = "";
        loadAdmin();
      } catch (err) {
        showToast(`设置失败：${err.message}`, "error");
        sel.value = "";
      }
    });
  });
}

function formatLimit(v) {
  if (v === null || v === undefined) return "不限";
  return String(v) + "/天";
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
        el.addEventListener("click", () => openCommunityDetail(parseInt(el.dataset.id, 10)));
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

// ===== 社区 =====
let communityOffset = 0;
let communityHasMore = true;
let currentCommunityDetail = null;

const communityModalEl = $("#community-modal");

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

function communityCardHtml(p) {
  const isAnnouncement = p.type === "announcement";
  const preview = p.content.length > 200 ? p.content.slice(0, 200) + "…" : p.content;
  return `
    <div class="community-post ${isAnnouncement ? "announcement" : ""}" data-id="${p.id}">
      <div class="community-post-head">
        ${isAnnouncement ? '<span class="community-tag">📢 公告</span>' : ""}
        ${p.is_pinned ? '<span class="community-tag pin">📌 置顶</span>' : ""}
        <span class="community-post-title">${esc(p.title)}</span>
      </div>
      <div class="community-post-meta">
        <span>👤 ${esc(p.username)}</span>
        <span>🕐 ${fmtTime(p.created_at)}</span>
        <span>👍 ${p.like_count}</span>
        <span>💬 ${p.comment_count}</span>
      </div>
      <div class="community-post-content">${esc(preview)}</div>
    </div>`;
}

async function loadCommunity(reset = true) {
  // 管理员才显示「发布公告」入口
  communityEl("btn-announcement-submit").style.display = isAdmin ? "" : "none";
  if (reset) {
    communityOffset = 0;
    communityHasMore = true;
  }
  try {
    const data = await api.communityPosts(communityOffset);
    const listEl = communityEl("community-list");
    const annEl = communityEl("community-announcements");

    // 公告区：置顶公告单独展示（最多 3 条）
    const pinned = data.posts.filter((p) => p.type === "announcement" && p.is_pinned).slice(0, 3);
    if (pinned.length) {
      annEl.style.display = "block";
      annEl.innerHTML =
        '<div class="community-announcements-title">📢 重要公告</div>' +
        pinned.map(communityCardHtml).join("");
    } else {
      annEl.style.display = "none";
      annEl.innerHTML = "";
    }

    if (reset) listEl.innerHTML = "";
    listEl.innerHTML += data.posts.map(communityCardHtml).join("");

    communityEl("community-empty").style.display = data.posts.length === 0 ? "block" : "none";
    communityHasMore = communityOffset + data.posts.length < data.total;
    communityEl("community-load-more").style.display = communityHasMore ? "block" : "none";
    communityOffset += data.posts.length;
  } catch (err) {
    handleApiError(err, "社区加载失败");
  }
}

async function submitCommunityPost(isAnnouncement) {
  const title = communityEl("community-title-input").value.trim();
  const content = communityEl("community-content-input").value.trim();
  if (!title || !content) {
    showToast("请填写标题和内容", "error");
    return;
  }
  const btn = communityEl(isAnnouncement ? "btn-announcement-submit" : "btn-community-submit");
  btn.disabled = true;
  try {
    if (isAnnouncement) {
      await api.createAnnouncement(title, content, true);
      showToast("公告已发布");
    } else {
      await api.createCommunityPost(title, content);
      showToast("发布成功");
    }
    communityEl("community-title-input").value = "";
    communityEl("community-content-input").value = "";
    await loadCommunity(true);
  } catch (err) {
    handleApiError(err, isAnnouncement ? "公告发布失败" : "发布失败");
  } finally {
    btn.disabled = false;
  }
}

async function openCommunityDetail(postId) {
  try {
    const data = await api.communityPostDetail(postId);
    currentCommunityDetail = data;
    communityEl("community-modal-title").textContent = data.post.title;
    communityEl("community-modal-body").innerHTML = `
      <div class="community-detail-meta">
        <span>👤 ${esc(data.post.username)}</span>
        <span>🕐 ${fmtTime(data.post.created_at)}</span>
        ${data.post.type === "announcement" ? '<span class="community-tag">📢 公告</span>' : ""}
      </div>
      <div class="community-detail-content">${esc(data.post.content)}</div>
      <div class="community-detail-like-bar">👍 ${data.post.like_count} · 💬 ${data.post.comment_count}</div>
      <div class="community-comments-title">评论（${data.comments.length}）</div>
      <div class="community-comments" id="community-comments">
        ${data.comments.length
          ? data.comments
              .map(
                (c) => `
          <div class="community-comment">
            <span class="community-comment-user">${esc(c.username)}</span>
            <span class="community-comment-text">${esc(c.content)}</span>
            <span class="community-comment-time">${fmtTime(c.created_at)}</span>
            ${c.username === currentUsername || data.is_admin
              ? `<button class="community-comment-del" data-del="${c.id}">×</button>` : ""}
          </div>`
              )
              .join("")
          : '<div class="community-no-comments">还没有评论</div>'}
      </div>
      <div class="community-comment-form">
        <input type="text" id="community-comment-input" class="topic-input"
               placeholder="写下你的评论…" maxlength="1000" autocomplete="off" />
        <button class="btn btn-primary btn-sm" id="community-comment-submit">评论</button>
      </div>`;

    const likeBtn = communityEl("community-modal-like");
    likeBtn.textContent = `${data.liked ? "❤️" : "👍"} ${data.post.like_count}`;
    likeBtn.classList.toggle("liked", data.liked);
    communityEl("community-modal-pin").style.display = data.is_admin ? "" : "none";
    communityEl("community-modal-pin").textContent = data.post.is_pinned ? "📌 取消置顶" : "📌 置顶";
    communityEl("community-modal-delete").style.display =
      data.is_owner || data.is_admin ? "" : "none";

    communityEl("community-modal-like").onclick = () => toggleCommunityLike(postId);
    communityEl("community-modal-pin").onclick = () => toggleCommunityPin(postId);
    communityEl("community-modal-delete").onclick = () => deleteCommunityPost(postId);
    communityEl("community-modal-close-btn").onclick = closeCommunityModal;
    communityEl("community-modal-close").onclick = closeCommunityModal;
    communityEl("community-comment-submit").onclick = () => submitCommunityComment(postId);
    communityEl("community-comment-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter") submitCommunityComment(postId);
    });
    communityEl("community-comments").querySelectorAll(".community-comment-del").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        deleteCommunityComment(parseInt(btn.dataset.del), postId);
      });
    });

    communityModalEl.style.display = "flex";
  } catch (err) {
    handleApiError(err, "帖子加载失败");
  }
}

function closeCommunityModal() {
  communityModalEl.style.display = "none";
  currentCommunityDetail = null;
}

async function toggleCommunityLike(postId) {
  try {
    const r = await api.toggleCommunityLike(postId);
    const likeBtn = communityEl("community-modal-like");
    likeBtn.textContent = `${r.liked ? "❤️" : "👍"} ${r.like_count}`;
    likeBtn.classList.toggle("liked", r.liked);
  } catch (err) {
    handleApiError(err, "操作失败");
  }
}

async function toggleCommunityPin(postId) {
  if (!currentCommunityDetail) return;
  const target = !currentCommunityDetail.post.is_pinned;
  try {
    await api.pinCommunityPost(postId, target);
    showToast(target ? "已置顶" : "已取消置顶");
    await openCommunityDetail(postId);
    loadCommunity(true);
  } catch (err) {
    handleApiError(err, "操作失败");
  }
}

async function deleteCommunityPost(postId) {
  if (!confirm("确定删除该帖子？")) return;
  try {
    await api.deleteCommunityPost(postId);
    showToast("帖子已删除");
    closeCommunityModal();
    loadCommunity(true);
  } catch (err) {
    handleApiError(err, "删除失败");
  }
}

async function submitCommunityComment(postId) {
  const input = communityEl("community-comment-input");
  const content = input.value.trim();
  if (!content) return;
  try {
    await api.createCommunityComment(postId, content);
    input.value = "";
    await openCommunityDetail(postId);
  } catch (err) {
    handleApiError(err, "评论失败");
  }
}

async function deleteCommunityComment(commentId, postId) {
  if (!confirm("确定删除该评论？")) return;
  try {
    await api.deleteCommunityComment(commentId);
    showToast("评论已删除");
    await openCommunityDetail(postId);
  } catch (err) {
    handleApiError(err, "删除失败");
  }
}

// 社区事件绑定（初始化时执行一次；列表点击用事件委托）
communityEl("btn-community-submit").addEventListener("click", () => submitCommunityPost(false));
communityEl("btn-announcement-submit").addEventListener("click", () => submitCommunityPost(true));
communityEl("community-list").addEventListener("click", (e) => {
  const card = e.target.closest(".community-post");
  if (card) openCommunityDetail(parseInt(card.dataset.id, 10));
});
communityEl("btn-community-more").addEventListener("click", () => loadCommunity(false));

function communityEl(id) {
  return document.getElementById(id);
}

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
        loadGenerateQuota();
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

// ===== 完型填空功能 =====

async function loadClozePick() {
  try {
    const topics = await api.listTopics();
    clozeToggleCount.textContent = topics.length ? `(${topics.length} 个词单)` : "";
    clozeTopicGrid.innerHTML = topics
      .map((t) => `
      <div class="essay-topic-card ${clozeSelectedTopics.includes(t.topic) ? "selected" : ""}" data-topic="${esc(t.topic)}">
        <div class="stc-name">${esc(t.topic)} ${jlptBadge(t.jlpt_level)}</div>
        <div class="stc-count">${t.count} 词</div>
      </div>
    `)
      .join("");

    clozeTopicGrid.querySelectorAll(".essay-topic-card").forEach((card) => {
      card.addEventListener("click", () => {
        card.classList.toggle("selected");
        const t = card.dataset.topic;
        if (card.classList.contains("selected")) {
          if (!clozeSelectedTopics.includes(t)) clozeSelectedTopics.push(t);
        } else {
          clozeSelectedTopics = clozeSelectedTopics.filter((x) => x !== t);
        }
        btnGenerateCloze.disabled = clozeSelectedTopics.length === 0;
        btnGenerateCloze.textContent = clozeSelectedTopics.length
          ? `生成完型填空（已选 ${clozeSelectedTopics.length} 个词单）`
          : "生成完型填空";
        refreshClozeWordPicker();
      });
    });
  } catch (err) {
    showToast(`加载词单失败：${err.message}`, "error");
  }
}

async function refreshClozeWordPicker() {
  if (clozeSelectedTopics.length === 0) {
    clozeWordPicker.style.display = "none";
    clozeSelectedWords = new Set();
    return;
  }
  try {
    clozeTopicWords = [];
    for (const topic of clozeSelectedTopics) {
      const data = await api.listWords({ topic, limit: 200 });
      data.words.forEach((w) => clozeTopicWords.push({ ...w, _topic: topic }));
    }
    const wordCount = clozeTopicWords.length;
    clozeWordHint.textContent = wordCount ? `点击选择要考察的单词（共 ${wordCount} 个，不选则全部使用）` : "";
    renderClozeWordChips();
    clozeWordPicker.style.display = "block";
  } catch (err) {
    console.error("加载词单单词失败:", err);
  }
}

function renderClozeWordChips() {
  clozeWordChips.innerHTML = clozeTopicWords
    .map((w) => {
      const key = `${w.japanese}(${w.kana})`;
      const sel = clozeSelectedWords.has(key) ? "selected" : "";
      return `<span class="essay-word-chip ${sel}" data-key="${esc(key)}">${esc(w.japanese)}<small>${esc(w.kana)}</small></span>`;
    })
    .join("");

  clozeWordChips.querySelectorAll(".essay-word-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const key = chip.dataset.key;
      if (clozeSelectedWords.has(key)) {
        clozeSelectedWords.delete(key);
      } else {
        clozeSelectedWords.add(key);
      }
      chip.classList.toggle("selected");
      clozeWordHint.textContent = clozeSelectedWords.size
        ? `已选择 ${clozeSelectedWords.size} 个单词重点考察`
        : `点击选择要考察的单词（共 ${clozeTopicWords.length} 个，不选则全部使用）`;
    });
  });

  btnClozeSelectAll.addEventListener("click", () => {
    clozeTopicWords.forEach((w) => clozeSelectedWords.add(`${w.japanese}(${w.kana})`));
    renderClozeWordChips();
  });
  btnClozeDeselectAll.addEventListener("click", () => {
    clozeSelectedWords = new Set();
    renderClozeWordChips();
  });
}

async function doGenerateCloze() {
  if (clozeSelectedTopics.length === 0) return;

  btnGenerateCloze.disabled = true;
  clozeLoading.style.display = "block";
  clozeResult.style.display = "none";
  clozeError.style.display = "none";
  clozeUserAnswers = {};
  clozeScore.style.display = "none";
  clozeAnswersCard.style.display = "none";
  clozeTranslationCard.style.display = "none";

  const rawLength = clozeLength.value;
  const length = rawLength === "custom" ? parseInt(clozeLengthCustom.value) || 400 : parseInt(rawLength);
  const level = clozeLevel.value;
  clozeLastConfig = { topics: [...clozeSelectedTopics], length, level };

  try {
    const words = clozeSelectedWords.size > 0 ? [...clozeSelectedWords] : null;
    await runStreamToPreview("/cloze", {
      topics: clozeSelectedTopics, words, length, jlpt_level: level, stream: true,
    }, "cloze-stream-preview", {
      onDone: (result) => {
        renderClozeResult(result);
        clozeLoading.style.display = "none";
        clozeResult.style.display = "block";
        clozeResult.scrollIntoView({ behavior: "smooth" });
      },
      onError: (msg) => { throw new Error(msg); },
    });
  } catch (err) {
    clozeLoading.style.display = "none";
    clozeError.style.display = "block";
    clozeError.textContent = `生成失败：${err.message}`;
    showToast("完型填空生成失败，请重试", "error");
  } finally {
    btnGenerateCloze.disabled = false;
  }
}

function renderClozeResult(data) {
  currentClozeData = data;
  btnClozeSave.style.display = "";
  clozeTitle.textContent = data.title;
  clozeUserAnswers = {};

  // Normalize blanks: ensure id is sequential
  const blanks = (data.blanks || []).map((b, i) => ({ ...b, id: i }));

  // Replace ____ with input fields
  let parts = data.passage.split("____");
  let html = "";
  for (let i = 0; i < parts.length; i++) {
    html += esc(parts[i]);
    if (i < blanks.length) {
      html += `<input type="text" class="cloze-blank-input" id="cloze-blank-${i}"
                data-blank-id="${i}" placeholder="?" autocomplete="off" />`;
    }
  }
  clozePassage.innerHTML = html;

  // Track user input
  clozePassage.querySelectorAll(".cloze-blank-input").forEach((input) => {
    input.addEventListener("input", () => {
      clozeUserAnswers[parseInt(input.dataset.blankId)] = input.value.trim();
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        // Move focus to next blank
        const allInputs = [...clozePassage.querySelectorAll(".cloze-blank-input")];
        const idx = allInputs.indexOf(input);
        if (idx < allInputs.length - 1) allInputs[idx + 1].focus();
      }
    });
  });

  // Build answers
  clozeAnswers.innerHTML = blanks
    .map((b) => `
      <div class="cloze-answer-row">
        <span class="cloze-answer-num">${b.id + 1}.</span>
        <span class="cloze-answer-word">${esc(b.answer)}</span>
        <span class="cloze-answer-kana">${esc(b.kana)}</span>
        ${b.hint ? `<span class="cloze-answer-hint">(${esc(b.hint)})</span>` : ""}
      </div>
    `)
    .join("");

  clozeTranslation.textContent = data.chinese_translation || "";
  clozeScore.style.display = "none";
  clozeAnswersCard.style.display = "none";
  clozeTranslationCard.style.display = "none";
}

function checkClozeAnswers() {
  if (!currentClozeData) return;
  const blanks = currentClozeData.blanks || [];
  let correct = 0;
  const total = blanks.length;

  clozePassage.querySelectorAll(".cloze-blank-input").forEach((input) => {
    const id = parseInt(input.dataset.blankId);
    const blank = blanks.find(b => (b.id !== undefined ? b.id : blanks.indexOf(b)) === id);
    const userAnswer = (input.value || "").trim();
    if (blank && userAnswer && (userAnswer === blank.answer || userAnswer === blank.kana)) {
      input.classList.add("correct");
      input.classList.remove("incorrect");
      correct++;
    } else if (userAnswer) {
      input.classList.add("incorrect");
      input.classList.remove("correct");
    } else {
      input.classList.remove("correct", "incorrect");
    }
  });

  clozeScore.style.display = "block";
  const pct = total > 0 ? correct / total : 0;
  clozeScore.textContent = `得分：${correct} / ${total}`;
  clozeScore.className = `cloze-score ${pct >= 0.7 ? "good" : "needs-work"}`;
  clozeTranslationCard.style.display = "block";
}

function revealClozeAnswers() {
  if (!currentClozeData) return;
  const blanks = currentClozeData.blanks || [];

  clozePassage.querySelectorAll(".cloze-blank-input").forEach((input) => {
    const id = parseInt(input.dataset.blankId);
    const blank = blanks.find(b => (b.id !== undefined ? b.id : blanks.indexOf(b)) === id);
    if (blank) {
      input.value = blank.answer;
      input.classList.add("correct");
      input.classList.remove("incorrect");
    }
  });

  clozeAnswersCard.style.display = "block";
  clozeTranslationCard.style.display = "block";
  clozeScore.style.display = "none";
}

function resetCloze() {
  clozePassage.querySelectorAll(".cloze-blank-input").forEach((input) => {
    input.value = "";
    input.classList.remove("correct", "incorrect");
  });
  clozeUserAnswers = {};
  clozeScore.style.display = "none";
  clozeAnswersCard.style.display = "none";
  clozeTranslationCard.style.display = "none";
}

async function saveClozeResult() {
  if (!currentClozeData) return;
  const config = clozeLastConfig || { topics: [], length: 400, level: "N3" };
  try {
    await api.saveCloze({
      title: currentClozeData.title,
      passage: currentClozeData.passage,
      blanks: currentClozeData.blanks || [],
      chinese_translation: currentClozeData.chinese_translation || "",
      topics: config.topics,
      length: config.length,
      jlpt_level: config.level,
    });
    showToast("完型填空已保存");
    btnClozeSave.style.display = "none";
    if (currentTab === "saved") loadClozeSaved();
  } catch (err) {
    showToast(`保存失败：${err.message}`, "error");
  }
}

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

// ===== 图片词卡功能 =====
const imageTopicList = $("#image-topic-list");
const imageCardGrid = $("#image-card-grid");
const imageToolbarInfo = $("#image-toolbar-info");
const imageEmpty = $("#image-empty");

let imageCardsData = null;
let imageSelectedTopic = null;

async function loadImageCards() {
  try {
    // 首次加载只获取元数据（不含 base64），速度极快
    const data = await api.listImageCards(false);
    imageCardsData = data;

    if (!data.topics || data.topics.length === 0) {
      imageTopicList.innerHTML = "";
      imageCardGrid.innerHTML = "";
      imageEmpty.style.display = "block";
      imageToolbarInfo.textContent = "";
      return;
    }

    imageEmpty.style.display = "none";
    imageToolbarInfo.textContent = `共 ${data.total_images} 张图片词卡`;

    imageTopicList.innerHTML = data.topics
      .map((t) => `
        <div class="wordbank-topic-item ${imageSelectedTopic === t.topic ? "active" : ""}" data-topic="${esc(t.topic)}">
          <span>${esc(t.topic)}</span>
          <span class="wordbank-topic-count">${t.count}</span>
        </div>
      `)
      .join("");

    imageTopicList.querySelectorAll(".wordbank-topic-item").forEach((item) => {
      item.addEventListener("click", () => {
        imageSelectedTopic = imageSelectedTopic === item.dataset.topic ? null : item.dataset.topic;
        imageTopicList.querySelectorAll(".wordbank-topic-item").forEach((el) =>
          el.classList.toggle("active", el.dataset.topic === imageSelectedTopic)
        );
        renderImageCards();
      });
    });

    renderImageCards();
  } catch (err) {
    showToast(`加载图片词卡失败：${err.message}`, "error");
  }
}

function renderImageCards() {
  if (!imageCardsData) return;

  const topics = imageSelectedTopic
    ? imageCardsData.topics.filter((t) => t.topic === imageSelectedTopic)
    : imageCardsData.topics;

  const allWords = [];
  topics.forEach((t) => allWords.push(...t.words));

  if (allWords.length === 0) {
    imageCardGrid.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:40px">该词单暂无图片词卡</p>';
    return;
  }

  imageCardGrid.innerHTML = allWords
    .map((w) => `
      <div class="image-card">
        <div class="image-card-img-wrap" data-word-id="${w.id}">
          ${w.image_base64
            ? `<img src="${esc(w.image_base64)}" alt="${esc(w.japanese)}" />`
            : `<div class="img-placeholder"><span>📷</span><span>加载中...</span></div>`}
        </div>
        <div class="image-card-body">
          <div class="image-card-words">
            <span class="image-card-jp">${esc(w.japanese)}</span>
            <span class="image-card-kana">${esc(w.kana)}</span>
            <button class="image-card-speak-btn" data-speak="${esc(w.japanese)}" data-kana="${esc(w.kana)}" title="朗读">▶</button>
          </div>
          <div class="image-card-meaning">${esc(w.chinese)}</div>
          <div class="image-card-example">${esc(w.example_ja)}<button class="example-speak-btn" data-speak="${esc(w.example_ja)}" title="朗读例句">▶</button></div>
          <div class="image-card-example-cn">${esc(w.example_cn)}</div>
        </div>
      </div>
    `)
    .join("");

  // 懒加载：IntersectionObserver 监听图片容器，可见时加载 base64
  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (!entry.isIntersecting) return;
      var wrap = entry.target;
      var wordId = parseInt(wrap.dataset.wordId);
      if (!wordId || wrap.dataset.loaded === "1") return;
      wrap.dataset.loaded = "1";
      api.getImageCardData(wordId).then(function(data) {
        if (data.image_base64) {
          wrap.innerHTML = '<img src="' + esc(data.image_base64) + '" alt="" />';
          wrap.querySelector("img").addEventListener("click", function() {
            showImageLightbox(data.image_base64);
          });
        }
      }).catch(function() {
        wrap.innerHTML = '<div class="img-placeholder"><span>❌</span></div>';
      });
    });
  }, { rootMargin: "200px" });

  imageCardGrid.querySelectorAll(".image-card-img-wrap").forEach(function(wrap) {
    if (!wrap.querySelector("img")) observer.observe(wrap);
  });

  // 已有图片的点击事件
  imageCardGrid.querySelectorAll("img").forEach((img) => {
    img.addEventListener("click", () => showImageLightbox(img.src));
  });

  imageCardGrid.querySelectorAll(".image-card-speak-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      speakWord(btn.dataset.speak, btn.dataset.kana, btn);
    });
  });

  imageCardGrid.querySelectorAll(".example-speak-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      speakWord(btn.dataset.speak, "", btn);
    });
  });
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
