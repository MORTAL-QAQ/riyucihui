/**
 * 多模态日语词汇学习 — 共享层（多页架构阶段二）
 *
 * 被 index.html（SPA）与独立子页（community/wordbank/study 等）共同引用。
 * 内容：
 * - DOM 工具：$ / $$
 * - 安全与展示：esc / escHtml / jlptBadge / fmtTime
 * - 提示：showToast / handleApiError
 * - 发音：speakWord（Web Audio 绕过 autoplay 策略）
 * - 会话：currentUsername / isAdmin / requireAuth / initPage / bindLogout
 */

// ===== DOM 查询简写 =====
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ===== HTML 转义（防 XSS） =====
function esc(s) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  return String(s).replace(/[&<>"']/g, (c) => map[c]);
}

function escHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function jlptBadge(level) {
  if (!level) return "";
  return `<span class="jlpt-badge ${esc(level)}">${esc(level)}</span>`;
}

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

// ===== Toast =====
function showToast(msg, type = "success", duration = 2500) {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  if (duration > 0) {
    setTimeout(() => el.remove(), duration);
  }
  return el;
}

/**
 * 统一 API/运行时错误处理：错误 toast + console 记录。
 * 返回可展示的消息文本。
 */
function handleApiError(err, fallbackMsg = "操作失败，请稍后重试") {
  const msg = (err && err.message) || fallbackMsg;
  console.error("[app]", err);
  showToast(msg, "error", 3500);
  return msg;
}

// ===== 发音（Web Audio，绕过浏览器 autoplay 策略） =====
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
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  api
    .voice(text)
    .then((blob) => blob.arrayBuffer())
    .then((buf) => {
      if (!audioCtx) {
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

// ===== 会话（独立子页使用） =====
let currentUsername = "";
let isAdmin = false;

function requireAuth() {
  if (!getToken()) {
    location.href = "/";
    return false;
  }
  return true;
}

async function loadCurrentUser() {
  const me = await api.me();
  currentUsername = me.username;
  isAdmin = !!me.is_admin;
  const displayName = me.name || me.username;
  const el = $("#sidebar-username");
  if (el) el.textContent = displayName;
  const navAdmin = $("#nav-admin");
  if (navAdmin) navAdmin.style.display = isAdmin ? "" : "none";
  injectAdminNav();
  return me;
}

// ── 顶栏「管理」按钮：仅管理员可见（动态注入，普通用户顶栏不出现） ──
const ADMIN_NAV_STYLE =
  "display:inline-flex; align-items:center; gap:4px; color:#d5d8e6; text-decoration:none; font-size:13px; padding:7px 12px; border-radius:999px; background:rgba(255,255,255,0.04); border:1px solid transparent;";
const ADMIN_NAV_ACTIVE_STYLE =
  "display:inline-flex; align-items:center; gap:4px; color:#fff; text-decoration:none; font-size:13px; padding:7px 12px; border-radius:999px; background:rgba(99,102,241,0.35); border:1px solid rgba(129,140,248,0.4);";

function injectAdminNav() {
  if (!isAdmin) return;
  // 独立子页顶栏导航容器（SPA 首页无此结构，自动跳过）
  const navWrap = document.querySelector('.subpage-header div[style*="flex-wrap:wrap"]');
  if (!navWrap) return;
  if (navWrap.querySelector('a[href="/admin"]')) return; // 防重复注入
  const a = document.createElement("a");
  a.href = "/admin";
  a.textContent = "🛡 管理";
  const current = location.pathname.replace(/^\/+|\/+$/g, "");
  a.style.cssText = current === "admin" ? ADMIN_NAV_ACTIVE_STYLE : ADMIN_NAV_STYLE;
  navWrap.appendChild(a);
}

function bindLogout() {
  // 同时绑定顶栏退出按钮（#btn-logout）与移动端抽屉退出按钮（#drawer-logout）
  document.querySelectorAll("#btn-logout, #drawer-logout").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try { await api.logout(); } catch (_) {}
      clearToken();
      location.href = "/";
    });
  });
}

/**
 * 独立子页初始化入口：
 * 校验登录 → 绑定退出 → 加载当前用户信息。
 * 未登录或 token 失效时跳回首页登录页。返回是否就绪。
 */
async function initPage() {
  if (!requireAuth()) return false;
  initSidebar();
  bindLogout();
  try {
    await loadCurrentUser();
    return true;
  } catch (_) {
    return false;
  }
}

// ===== 移动端侧边栏抽屉（所有页面共用；子页自动注入与首页一致的抽屉导航） =====
let _mobileSidebarInjected = false;
let _mobileSidebarBound = false;

const MOBILE_NAV_ITEMS = [
  ["home", "/", "🏠", "首页"],
  ["wordbank", "/wordbank", "📖", "我的词库"],
  ["study", "/study", "📝", "背词"],
  ["generate", "/generate", "✦", "生成单词"],
  ["essay", "/essay", "📄", "短文"],
  ["cloze", "/cloze", "📝", "完型填空"],
  ["grammar", "/grammar", "📐", "语法"],
  ["image", "/image", "📷", "图片词卡"],
  ["community", "/community", "💬", "社区"],
  ["achievement", "/achievement", "🏆", "成就"],
  ["saved", "/saved", "💾", "我的保存"],
  ["settings", "/settings", "⚙", "设置"],
];

function injectMobileDrawer() {
  if (_mobileSidebarInjected) return null;
  _mobileSidebarInjected = true;
  const current = location.pathname.replace(/^\/+|\/+$/g, "") || "home";
  const navHtml = MOBILE_NAV_ITEMS.map(
    ([key, href, icon, label]) =>
      `<a class="nav-btn ${current === key ? "active" : ""}" href="${href}">` +
      `<span class="nav-icon">${icon}</span> ${label}</a>`
  ).join("");
  const wrap = document.createElement("div");
  wrap.className = "mobile-only";
  wrap.innerHTML = `
    <button class="hamburger" id="hamburger-btn" aria-label="菜单">☰</button>
    <div class="sidebar-overlay" id="sidebar-overlay"></div>
    <aside class="sidebar mobile-only-sidebar">
      <div class="logo">
        <span class="logo-icon">あ</span>
        <span class="logo-text">多模态日语词汇学习</span>
      </div>
      <div class="sidebar-greeting">
        <span class="sidebar-greeting-emoji">👋</span>
        <span>日本語の世界へようこそ！</span>
        <span class="sidebar-greeting-kao">Hi~ o(*￣▽￣*)ブ</span>
      </div>
      <nav class="nav">
        ${navHtml}
        <a class="nav-btn" id="nav-admin" href="/admin" style="display:none">
          <span class="nav-icon">🛡</span> 管理
        </a>
      </nav>
      <div class="sidebar-footer">
        <div class="user-info">
          <span class="user-icon">👤</span>
          <span class="user-name" id="sidebar-username"></span>
        </div>
        <button class="btn btn-link btn-logout" id="drawer-logout">退出登录</button>
      </div>
    </aside>`;
  document.body.appendChild(wrap);
  return wrap.querySelector(".sidebar");
}

function initSidebar() {
  if (_mobileSidebarBound) return;
  let sidebar = document.querySelector(".sidebar");
  // 子页无侧边栏时注入（桌面端 >768px 由 .mobile-only 隐藏，不注入）
  if (
    !sidebar &&
    window.matchMedia &&
    !window.matchMedia("(min-width: 769px)").matches
  ) {
    sidebar = injectMobileDrawer();
  }
  const overlay = document.getElementById("sidebar-overlay");
  const hamburger = document.getElementById("hamburger-btn");
  if (!sidebar || !hamburger) return;
  _mobileSidebarBound = true;
  const close = () => {
    sidebar.classList.remove("open");
    if (overlay) overlay.classList.remove("show");
  };
  hamburger.addEventListener("click", () => {
    sidebar.classList.contains("open") ? close() : (sidebar.classList.add("open"), overlay && overlay.classList.add("show"));
  });
  if (overlay) overlay.addEventListener("click", close);
  sidebar.querySelectorAll(".nav-btn").forEach((b) => b.addEventListener("click", close));
}

// ===== 图片灯箱（词库/背词共用） =====
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

// ===== SSE 流式统一处理（AI 生成页面共用） =====
async function runStreamToPreview(url, body, previewId, handlers = {}) {
  // 注意：$ 是 querySelector（选择器语义），previewId 是纯 id，需补 # 前缀
  const previewEl = $("#" + previewId) || document.getElementById(previewId);
  if (!previewEl) {
    // 页面结构缺失/版本错配时给出明确提示，避免 null.style 崩溃
    const { onError } = handlers;
    if (onError) onError("页面组件未加载，请刷新页面后重试");
    else showToast("页面组件未加载，请刷新页面后重试", "error");
    return;
  }
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
