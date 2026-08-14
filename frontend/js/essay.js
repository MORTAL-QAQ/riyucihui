/**
 * 短文生成独立子页逻辑（阶段二多页架构）
 * 依赖：api.js + common.js（$ / esc / jlptBadge / showToast / handleApiError
 *       / speakWord / runStreamToPreview / initPage / currentUsername / isAdmin）
 */

// ── 状态 ──
let essaySelectedTopics = [];
let essayLastConfig = null;
let currentEssayData = null;
let essaySelectedWords = new Set();
let essayTopicWords = [];

// ── DOM 引用 ──
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
const essayWordPicker = $("#essay-word-picker");
const essayWordChips = $("#essay-word-chips");
const essayWordHint = $("#essay-word-hint");
const btnEssaySelectAll = $("#btn-essay-select-all-words");
const btnEssayDeselectAll = $("#btn-essay-deselect-all-words");

// ── 词单选择 ──
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

// ── 单词选择 ──
async function refreshEssayWordPicker() {
  if (essaySelectedTopics.length === 0) {
    essayWordPicker.style.display = "none";
    essayTopicWords = [];
    essaySelectedWords.clear();
    return;
  }

  try {
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

// ── 生成 ──
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
  } catch (err) {
    showToast(`保存失败：${err.message}`, "error");
  }
}

// ── 入口：认证 → 选题 ──
initPage().then((ok) => {
  if (ok) loadEssayPick();
});
