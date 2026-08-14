/**
 * 完型填空独立子页逻辑（阶段二多页架构）
 * 依赖：api.js + common.js（$ / esc / jlptBadge / showToast / handleApiError
 *       / speakWord / runStreamToPreview / initPage / currentUsername / isAdmin）
 */

// ── 状态 ──
let clozeSelectedTopics = [];
let clozeSelectedWords = new Set();
let clozeTopicWords = [];
let currentClozeData = null;
let clozeLastConfig = null;
let clozeUserAnswers = {};

// ── DOM 引用 ──
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

// ── 事件绑定 ──
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

// ── 词单选择 ──
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

// ── 单词选择 ──
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

// ── 生成 ──
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

// ── 结果渲染 ──
function renderClozeResult(data) {
  currentClozeData = data;
  btnClozeSave.style.display = "";
  clozeTitle.textContent = data.title;
  clozeUserAnswers = {};

  const blanks = (data.blanks || []).map((b, i) => ({ ...b, id: i }));

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

  clozePassage.querySelectorAll(".cloze-blank-input").forEach((input) => {
    input.addEventListener("input", () => {
      clozeUserAnswers[parseInt(input.dataset.blankId)] = input.value.trim();
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const allInputs = [...clozePassage.querySelectorAll(".cloze-blank-input")];
        const idx = allInputs.indexOf(input);
        if (idx < allInputs.length - 1) allInputs[idx + 1].focus();
      }
    });
  });

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
    const blank = blanks.find((b) => (b.id !== undefined ? b.id : blanks.indexOf(b)) === id);
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
    const blank = blanks.find((b) => (b.id !== undefined ? b.id : blanks.indexOf(b)) === id);
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
  } catch (err) {
    showToast(`保存失败：${err.message}`, "error");
  }
}

// ── 入口：认证 → 选题 ──
initPage().then((ok) => {
  if (ok) loadClozePick();
});
