/**
 * 多模态日语词汇学习 — API 客户端模块
 *
 * 提供两个核心请求函数和所有 API 端点的封装方法。
 *
 * 核心函数：
 * - streamRequest(url, body, onEvent): SSE 流式请求（用于 AI 生成：单词/短文/完型填空/语法）
 * - request(url, opts): 普通 JSON 请求（用于 CRUD 操作）
 *
 * 流式请求事件类型：
 * - {chunk: "..."} 增量文本块
 * - {done: true, result: {...}} 生成完成
 * - {error: "..."} 发生错误
 */

const BASE = window.API_BASE || "/api";

// Token 优先从内存读取，否则从 sessionStorage 恢复（#39）
// 外部统一通过 setToken/clearToken/getToken 操作，禁止直接改写内部状态
let authToken = sessionStorage.getItem("token");

function getToken() {
  return authToken || sessionStorage.getItem("token");
}

function setToken(token) {
  authToken = token || null;
  if (token) sessionStorage.setItem("token", token);
  else sessionStorage.removeItem("token");
}

function clearToken() {
  authToken = null;
  sessionStorage.removeItem("token");
}

/** SSE 流式请求 — 通过 Server-Sent Events 逐步接收 AI 生成内容。 */
async function streamRequest(url, body, onEvent) {
  const token = getToken();
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(BASE + url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `请求失败 (${res.status})`);
  }

  // 使用 ReadableStream 逐行解析 SSE 事件
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop(); // 保留不完整的行，等下次拼接
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event = JSON.parse(line.slice(6));
          onEvent(event);
        } catch {}  // 忽略解析失败的行
      }
    }
  }
}

/** 普通 JSON 请求 — 自动附加 Authorization 请求头，自动处理成就解锁弹窗。 */
function request(url, opts = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...opts.headers };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return fetch(BASE + url, { ...opts, headers }).then(async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `请求失败 (${res.status})`);
    }
    // 接口返回 new_achievements 时自动弹出成就解锁提示
    if (data.new_achievements && data.new_achievements.length > 0) {
      data.new_achievements.forEach((a, i) => {
        setTimeout(() => {
          const el = document.createElement("div");
          el.className = "toast achievement";
          el.textContent = `${a.icon} 解锁成就：${a.name}`;
          document.body.appendChild(el);
          setTimeout(() => el.remove(), 3000);
        }, i * 500);  // 多个成就依次弹出（各间隔 500ms）
      });
    }
    return data;
  });
}

// ── API 方法集合 ──
// 按功能分组：认证 → 单词 → 短文 → 语法 → 学习 → 设置 → 管理 → 成就 → 完型填空
const api = {
  // ── Auth ──
  register(username, password) {
    return request("/register", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  login(username, password) {
    return request("/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  me() {
    return request("/me");
  },

  logout() {
    return request("/logout", { method: "POST" });
  },

  // ── Words ──
  generateQuota() {
    return request("/generate/quota");
  },

  generate(topic, difficulty, extra, count, excludeWords) {
    return request("/generate", {
      method: "POST",
      body: JSON.stringify({
        topic,
        difficulty: difficulty || undefined,
        extra: extra || undefined,
        count: count || 10,
        exclude_words: excludeWords || undefined,
      }),
    });
  },

  generateEssay(topics, words, wordCount, jlptLevel) {
    return request("/essay", {
      method: "POST",
      body: JSON.stringify({
        topics,
        words: words && words.length > 0 ? words : undefined,
        word_count: wordCount,
        jlpt_level: jlptLevel,
      }),
    });
  },

  saveEssay(data) {
    return request("/essays", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  listEssays(offset = 0, limit = 20) {
    return request(`/essays?offset=${offset}&limit=${limit}`);
  },

  deleteEssay(id) {
    return request(`/essays/${id}`, { method: "DELETE" });
  },

  saveWords(topic, words, jlptLevel) {
    return request("/words", {
      method: "POST",
      body: JSON.stringify({ topic, words, jlpt_level: jlptLevel || null }),
    });
  },

  listWords({ topic, search, offset, limit } = {}) {
    const params = new URLSearchParams();
    if (topic) params.set("topic", topic);
    if (search) params.set("search", search);
    if (offset !== undefined) params.set("offset", offset);
    if (limit !== undefined) params.set("limit", limit);
    return request(`/words?${params}`);
  },

  listTopics() {
    return request("/topics");
  },

  deleteTopic(topic) {
    return request(`/topics/${encodeURIComponent(topic)}`, { method: "DELETE" });
  },

  addWord(topic, word) {
    return request(`/topics/${encodeURIComponent(topic)}/words`, {
      method: "POST",
      body: JSON.stringify(word),
    });
  },

  deleteWord(id) {
    return request(`/words/${id}`, { method: "DELETE" });
  },

  generateWordImage(wordId) {
    return request(`/words/${wordId}/image`, { method: "POST" });
  },

  listImageCards(includeData = false) {
    return request(`/image-cards?include_data=${includeData}`);
  },

  getImageCardData(wordId) {
    return request(`/words/${wordId}/image-data`);
  },

  mergeDuplicates() {
    return request("/words/deduplicate", { method: "POST" });
  },

  /** 导出 PDF — 使用 fetch + blob 模式（同 voice），确保 Authorization 头正确传递。 */
  exportPdf(url, params = {}) {
    const token = getToken();
    const headers = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const qs = Object.keys(params).length ? `?${new URLSearchParams(params)}` : "";
    return fetch(BASE + url + qs, { headers }).then(async (res) => {
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `导出失败 (${res.status})`);
      }
      const blob = await res.blob();
      // Extract filename from Content-Disposition header
      const disposition = res.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename\*?=(?:UTF-8'')?(.+?)(?:;|$)/);
      const filename = match ? decodeURIComponent(match[1]) : "export.pdf";
      return { blob, filename };
    });
  },

  async voice(text) {
    const token = getToken();
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(BASE + "/voice", {
      method: "POST",
      headers,
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `语音合成失败 (${res.status})`);
    }
    // 返回 Blob：调用方用 blob.arrayBuffer() 直接解码，
    // 避免再 fetch(blob: URL)（部分浏览器/WebView 不支持导致 "Failed to fetch"）
    return res.blob();
  },

  // ── Study ──
  studyDue() {
    return request("/study/due");
  },

  studyTopics(mode) {
    const params = new URLSearchParams();
    if (mode) params.set("mode", mode);
    const qs = params.toString();
    return request(`/study/topics${qs ? "?" + qs : ""}`);
  },

  studyStats() {
    return request("/study/stats");
  },

  startStudy(topics, count, mode) {
    return request("/study/start", {
      method: "POST",
      body: JSON.stringify({ topics, count, mode }),
    });
  },

  recordStudy(wordId, quality) {
    return request("/study/record", {
      method: "POST",
      body: JSON.stringify({ word_id: wordId, quality }),
    });
  },

  undoStudy() {
    return request("/study/undo", { method: "POST" });
  },

  studyCalendar(days) {
    return request(`/study/calendar?days=${days || 14}`);
  },

  studyWordsStatus(ids) {
    if (!ids.length) return Promise.resolve([]);
    return request(`/study/words-status?ids=${ids.join(",")}`);
  },

  // ── Settings ──
  getSettings() {
    return request("/settings");
  },

  saveSettings(settings) {
    return request("/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    });
  },

  getSpeakers() {
    return request("/speakers");
  },

  changePassword(oldPassword, newPassword) {
    return request("/settings/password", {
      method: "PUT",
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
  },

  updateName(name) {
    return request("/settings/name", {
      method: "PUT",
      body: JSON.stringify({ name }),
    });
  },

  // ── Health ──
  health() {
    return request("/health");
  },

  // ── Admin ──
  adminStats() {
    return request("/admin/stats");
  },

  adminUsers() {
    return request("/admin/users");
  },

  adminLoginHistory() {
    return request("/admin/login-history");
  },

  adminCreateUser(username, password) {
    return request("/admin/create-user", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  toggleAdmin(userId) {
    return request(`/admin/users/${userId}/admin`, { method: "PUT", body: "{}" });
  },

  deleteUser(userId) {
    return request(`/admin/users/${userId}`, { method: "DELETE" });
  },

  setUserLimits(userId, aiLimit, voiceLimit, wordLimit, imageLimit) {
    return request(`/admin/users/${userId}/limits`, {
      method: "PUT",
      body: JSON.stringify({
        daily_ai_limit: aiLimit,
        daily_voice_limit: voiceLimit,
        daily_word_limit: wordLimit,
        daily_image_limit: imageLimit,
      }),
    });
  },

  setUserRemark(userId, remark) {
    return request(`/admin/users/${userId}/remark`, {
      method: "PUT",
      body: JSON.stringify({ remark }),
    });
  },

  resetUserPassword(userId, password) {
    return request(`/admin/users/${userId}/password`, {
      method: "PUT",
      body: JSON.stringify({ password }),
    });
  },

  adminUsage() {
    return request("/admin/usage");
  },

  // ── Grammar ──
  analyzeGrammar(sentence) {
    return request("/grammar/analyze", {
      method: "POST",
      body: JSON.stringify({ sentence }),
    });
  },

  correctGrammar(sentence) {
    return request("/grammar/correct", {
      method: "POST",
      body: JSON.stringify({ sentence }),
    });
  },

  compareGrammar(topic) {
    return request("/grammar/compare", {
      method: "POST",
      body: JSON.stringify({ topic }),
    });
  },

  saveGrammarCompare(topic, result) {
    return request("/grammar/compares", {
      method: "POST",
      body: JSON.stringify({ topic, result }),
    });
  },

  listGrammarCompares(offset = 0, limit = 50) {
    return request(`/grammar/compares?offset=${offset}&limit=${limit}`);
  },

  deleteGrammarCompare(id) {
    return request(`/grammar/compares/${id}`, { method: "DELETE" });
  },

  // ── Cloze ──
  saveCloze(data) {
    return request("/clozes", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  listClozes(offset = 0, limit = 50) {
    return request(`/clozes?offset=${offset}&limit=${limit}`);
  },

  deleteCloze(id) {
    return request(`/clozes/${id}`, { method: "DELETE" });
  },

  // ── Achievement ──
  listAchievements() {
    return request("/achievements");
  },

  awardAchievement(key) {
    return request("/achievements/award/" + key, { method: "POST", body: "{}" });
  },

  // ── Community（社区） ──
  communityPosts(offset = 0, limit = 20) {
    return request(`/community/posts?offset=${offset}&limit=${limit}`);
  },

  createCommunityPost(title, content) {
    return request("/community/posts", {
      method: "POST",
      body: JSON.stringify({ title, content }),
    });
  },

  communityPostDetail(id) {
    return request(`/community/posts/${id}`);
  },

  deleteCommunityPost(id) {
    return request(`/community/posts/${id}`, { method: "DELETE" });
  },

  toggleCommunityLike(id) {
    return request(`/community/posts/${id}/like`, { method: "POST", body: "{}" });
  },

  createCommunityComment(postId, content) {
    return request(`/community/posts/${postId}/comments`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
  },

  deleteCommunityComment(id) {
    return request(`/community/comments/${id}`, { method: "DELETE" });
  },

  createAnnouncement(title, content, pinned = true) {
    return request("/community/announcements", {
      method: "POST",
      body: JSON.stringify({ title, content, pinned }),
    });
  },

  pinCommunityPost(id, pinned) {
    return request(`/community/posts/${id}/pin?pinned=${pinned}`, { method: "PUT" });
  },
};
