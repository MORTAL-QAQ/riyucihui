/**
 * 词库独立子页逻辑（阶段二多页架构）
 * 依赖：api.js + common.js（$ / esc / jlptBadge / fmtTime / showToast / handleApiError
 *       / speakWord / initPage / currentUsername / isAdmin）
 */

// ── 词库状态 ──
let currentTopic = "";
let currentSearch = "";
let wordbankPage = 1;
const WORD_PAGE_SIZE = 10;

// ── DOM 引用 ──
const topicList = $("#topic-list");
const searchInput = $("#search-input");
const wordbankCards = $("#wordbank-cards");
const wordbankInfo = $("#wordbank-info");
const emptyState = $("#empty-state");
const wbPagination = $("#wordbank-pagination");
const wbPrev = $("#wb-prev");
const wbNext = $("#wb-next");
const wbPageInfo = $("#wb-page-info");
const wbJumpInput = $("#wb-jump-input");

const addWordForm = $("#add-word-form");
const btnShowAddForm = $("#btn-show-add-form");
const btnAddWord = $("#btn-add-word");
const addWordTopic = $("#add-word-topic");
const addJapanese = $("#add-japanese");
const addKana = $("#add-kana");
const addChinese = $("#add-chinese");
const addExampleJa = $("#add-example-ja");
const addExampleCn = $("#add-example-cn");
const btnMergeDuplicates = $("#btn-merge-duplicates");

// ── PDF 导出对话框 ──
const exportModal = $("#export-modal");
const exportPanelBody = $("#export-panel-options");
const exportGeneratingEl = $("#export-generating");
const exportDoneEl = $("#export-done");
const exportFooter = $("#export-modal-footer");
const exportConfirmBtn = $("#export-modal-confirm");

let _exportWordCount = 0;
let _exportTopic = "";

// ── 列表加载 ──
async function loadWordbank(reset = true) {
  try {
    if (reset) {
      wordbankPage = 1;
    }
    const offset = (wordbankPage - 1) * WORD_PAGE_SIZE;
    const [wordsData, topicsData] = await Promise.all([
      api.listWords({ topic: currentTopic, search: currentSearch, offset, limit: WORD_PAGE_SIZE }),
      api.listTopics(),
    ]);
    renderTopics(topicsData);
    renderWordbankCards(wordsData);
    if (wordsData.words.length > 0) {
      loadStudyStatus(wordsData.words);
    }
  } catch (err) {
    showToast(`加载词库失败：${err.message}`, "error");
  }
}

async function loadStudyStatus(words) {
  const ids = words.map((w) => w.id);
  try {
    const statusList = await api.studyWordsStatus(ids);
    const statusMap = {};
    statusList.forEach((s) => { statusMap[s.word_id] = s; });
    words.forEach((w) => {
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

// ── 图片灯箱 ──
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

// ── PDF 导出 ──
function openExportDialog() {
  exportPanelBody.style.display = "block";
  exportGeneratingEl.style.display = "none";
  exportDoneEl.style.display = "none";
  exportFooter.style.display = "flex";
  exportConfirmBtn.disabled = false;
  exportConfirmBtn.textContent = "📥 导出 PDF";

  $("#export-progress-fill").style.width = "0%";

  const activeEl = document.querySelector(".topic-item.active");
  _exportTopic = activeEl ? activeEl.dataset.topic : "";
  const label = _exportTopic || "全部词单";
  $("#export-topic-label").innerHTML = esc(label) + ' · <span id="export-word-count">--</span> 个单词';

  document.querySelector("input[name='export-layout'][value='table']").checked = true;
  $("#export-include-images").checked = true;
  $("#export-include-examples").checked = true;

  const token = getToken();
  const qs = _exportTopic ? "?topic=" + encodeURIComponent(_exportTopic) + "&limit=1" : "?limit=1";
  fetch(BASE + "/words" + qs, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  }).then((r) => r.json()).then((data) => {
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

var _progressTimer = null;
function startProgress() {
  var w = 0;
  $("#export-progress-fill").style.width = "0%";
  _progressTimer = setInterval(function () {
    w += (100 - w) * 0.08;
    if (w > 95) w = 95;
    $("#export-progress-fill").style.width = w + "%";
  }, 200);
}
function finishProgress() {
  clearInterval(_progressTimer);
  $("#export-progress-fill").style.width = "100%";
}

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

// ── 事件绑定 ──
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

  const exSpeakBtn = e.target.closest(".example-speak-btn");
  if (exSpeakBtn) {
    speakWord(exSpeakBtn.dataset.speak, "", exSpeakBtn);
    return;
  }

  const imgBtn = e.target.closest(".img-gen-btn");
  if (imgBtn) {
    const id = parseInt(imgBtn.dataset.id);
    const card = imgBtn.closest(".wordbank-card");

    if (imgBtn.classList.contains("has-image")) {
      const existingImg = card.querySelector(".wordbank-card-inline-img");
      if (existingImg) {
        existingImg.remove();
        imgBtn.textContent = "展示图片";
        return;
      }
      imgBtn.disabled = true;
      imgBtn.textContent = "加载中...";
      api.getImageCardData(id).then((data) => {
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

    imgBtn.disabled = true;
    imgBtn.textContent = "生成中...";

    var progressWrap = document.createElement("div");
    progressWrap.className = "img-gen-progress";
    progressWrap.innerHTML = '<div class="img-gen-progress-track"><div class="img-gen-progress-bar"></div></div><span class="img-gen-progress-text">0%</span>';
    card.appendChild(progressWrap);

    var bar = progressWrap.querySelector(".img-gen-progress-bar");
    var text = progressWrap.querySelector(".img-gen-progress-text");
    var progress = 0;
    var stalls = [0, 15, 32, 48, 67, 78, 90];
    var stage = 0;
    var timer = null;

    function nextStage() {
      if (stage >= stalls.length - 1) return;
      var from = stalls[stage];
      var to = stalls[stage + 1];
      var steps = 8 + Math.floor(Math.random() * 12);
      var duration = 1000 + Math.random() * 2000;
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
          timer = setTimeout(nextStage, 600 + Math.random() * 1000);
        }
      }
      step();
    }
    nextStage();

    var waitToast = showToast("⏳ 正在生成配图，请勿离开此页面...", "info", 0);

    api.generateWordImage(id).then(function (result) {
      clearTimeout(timer);
      progress = 100; stage = stalls.length;
      bar.style.width = "100%";
      text.textContent = "100%";
      waitToast.remove();
      setTimeout(function () { progressWrap.remove(); showToast("配图生成成功"); }, 400);
      imgBtn.disabled = false;
      imgBtn.textContent = "展示图片";
      imgBtn.classList.add("has-image");
      imgBtn.dataset.img = result.image_base64;
    }).catch(function (err) {
      clearTimeout(timer);
      waitToast.remove();
      bar.style.width = "100%";
      bar.style.background = "#ef4444";
      text.textContent = "失败";
      text.style.color = "#ef4444";
      setTimeout(function () {
        progressWrap.remove();
        imgBtn.disabled = false;
        imgBtn.textContent = "生成图片";
      }, 600);
      showToast("配图生成失败：" + err.message, "error");
    });
    return;
  }

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

btnShowAddForm.addEventListener("click", () => {
  const visible = addWordForm.style.display !== "none";
  addWordForm.style.display = visible ? "none" : "block";
  btnShowAddForm.textContent = visible ? "＋ 添加单词" : "－ 收起";
  if (!visible) populateAddTopicOptions();
});

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

$("#export-modal-close").addEventListener("click", closeExportDialog);
$("#export-modal-cancel").addEventListener("click", closeExportDialog);
exportModal.addEventListener("click", function (e) {
  if (e.target === exportModal) closeExportDialog();
});

exportConfirmBtn.addEventListener("click", function () {
  if (_exportWordCount === 0) return;

  var layout = document.querySelector("input[name='export-layout']:checked");
  layout = layout ? layout.value : "table";
  var includeExamples = $("#export-include-examples").checked;

  exportPanelBody.style.display = "none";
  exportGeneratingEl.style.display = "block";
  exportFooter.style.display = "none";
  var label = _exportTopic || "全部词单";
  $("#export-generating-detail").textContent = "正在导出「" + label + "」的 " + _exportWordCount + " 个单词";
  startProgress();

  var params = {};
  if (_exportTopic) params.topic = _exportTopic;
  params.layout = layout;

  api.exportPdf("/words/export/pdf", params).then(function (result) {
    finishProgress();
    var url = URL.createObjectURL(result.blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = result.filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    exportGeneratingEl.style.display = "none";
    exportDoneEl.style.display = "block";
    exportFooter.style.display = "flex";
    exportConfirmBtn.textContent = "✅ 完成";
    exportConfirmBtn.disabled = true;

    setTimeout(function () {
      if (exportModal.style.display !== "none") closeExportDialog();
    }, 2000);
  }).catch(function (err) {
    clearInterval(_progressTimer);
    exportGeneratingEl.style.display = "none";
    exportPanelBody.style.display = "block";
    exportFooter.style.display = "flex";
    showToast("导出失败：" + err.message, "error");
  });
});

$("#btn-export-pdf").addEventListener("click", openExportDialog);

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

// ── 入口：认证 → 加载词库 ──
initPage().then((ok) => {
  if (ok) loadWordbank();
});
