/**
 * 生成单词独立子页逻辑（阶段二多页架构）
 * 依赖：api.js + common.js（$ / esc / jlptBadge / showToast / handleApiError
 *       / speakWord / runStreamToPreview / initPage / currentUsername / isAdmin）
 */

// ── 状态 ──
let currentTopic = "";
let generatedWords = [];
let selectedSet = new Set();
let savedWordIndices = new Set();
let generatedDifficulty = null;

// ── DOM 引用 ──
const topicInput = $("#topic-input");
const difficultySelect = $("#difficulty-select");
const wordCountSelect = $("#word-count-select");
const extraInput = $("#extra-input");
const btnGenerate = $("#btn-generate");
const loadingEl = $("#loading");
const resultArea = $("#result-area");
const generateError = $("#generate-error");
const generateWelcome = $("#generate-welcome");
const resultTopic = $("#result-topic");
const wordCards = $("#word-cards");
const selectedCount = $("#selected-count");
const btnSave = $("#btn-save");
const btnSelectAll = $("#btn-select-all");
const btnGenerateMore = $("#btn-generate-more");
const quotaText = $("#quota-text");
const quotaProgressFill = $("#quota-progress-fill");

// ── 事件绑定 ──
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

// ── 配额 ──
async function loadGenerateQuota() {
  try {
    const q = await api.generateQuota();

    const remaining = q.remaining;
    const limit = q.daily_limit;
    const used = q.today_generated;

    if (q.is_admin || limit === null) {
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
    // API 不可用时保留默认显示
  }
}

// ── 生成 ──
async function doGenerate() {
  const topic = topicInput.value.trim();
  if (!topic) {
    topicInput.focus();
    return;
  }
  currentTopic = topic;
  savedWordIndices = new Set();

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
        if (generatedDifficulty) {
          generatedWords.forEach((w) => { if (!w.jlpt_level) w.jlpt_level = generatedDifficulty; });
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
          <button class="star-btn ${saved ? "saved" : ""}" data-index="${i}" title="${saved ? "已收藏" : "收藏到词库"}">${saved ? "★" : "☆"}</button>
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
  const sortedIndices = [...selectedSet].sort((a, b) => b - a);
  const words = sortedIndices.slice().reverse().map((i) => generatedWords[i]);

  btnSave.disabled = true;
  try {
    await api.saveWords(topic, words, generatedDifficulty);
    showToast(`成功保存 ${words.length} 个单词到词库`);
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
          result.forEach((w) => { if (!w.jlpt_level) w.jlpt_level = generatedDifficulty; });
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

// ── 入口：认证 → 配额 ──
initPage().then((ok) => {
  if (ok) loadGenerateQuota();
});
