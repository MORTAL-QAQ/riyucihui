/**
 * 多模态记忆对照实验页逻辑（阶段二多页架构）
 *
 * 流程：生成材料（20 词） → 逐张配图（多模态组 10 张） → 学习 → 测试（4 选 1） → 结果对比
 * 依赖：api.js + common.js（$ / esc / showToast / speakWord / initPage）
 */

// ── DOM 引用 ──
const expConfig = $("#exp-config");
const expLearning = $("#exp-learning");
const expTesting = $("#exp-testing");
const expResult = $("#exp-result");
const expTopicInput = $("#exp-topic");
const expLevelSelect = $("#exp-level");
const expRandomTopicBtn = $("#exp-random-topic");
const btnExpCreate = $("#btn-exp-create");
const expTopicLabel = $("#exp-topic-label");
const expLearnStatus = $("#exp-learn-status");
const expImageProgress = $("#exp-image-progress");
const expImageHint = $("#exp-image-hint");
const expLearnGrid = $("#exp-learn-grid");
const btnExpToTest = $("#btn-exp-to-test");
const expPrepareHint = $("#exp-prepare-hint");
const expTestProgressLabel = $("#exp-test-progress-label");
const expTestAnswered = $("#exp-test-answered");
const expTestProgress = $("#exp-test-progress");
const expTestList = $("#exp-test-list");
const btnExpSubmit = $("#btn-exp-submit");
const expSubmitHint = $("#exp-submit-hint");
const expResultCards = $("#exp-result-cards");
const expVerdict = $("#exp-verdict");
const expDetailTable = $("#exp-detail-table");
const btnExpAgain = $("#btn-exp-again");
const expHistory = $("#exp-history");

// ── 状态 ──
let expSessionId = null;
let expWords = [];        // 学习阶段单词
let expQuiz = [];         // 测试题
const expAnswers = {};    // word_id → choice

const RANDOM_TOPICS = [
  "日常生活", "食物料理", "旅行观光", "学校学习", "工作职场",
  "天气自然", "交通出行", "购物消费", "健康医疗", "兴趣爱好",
];

// ── 阶段切换 ──
function showStage(stage) {
  expConfig.style.display = stage === "config" ? "block" : "none";
  expLearning.style.display = stage === "learning" ? "block" : "none";
  expTesting.style.display = stage === "testing" ? "block" : "none";
  expResult.style.display = stage === "result" ? "block" : "none";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ── 阶段一：生成材料 ──
expRandomTopicBtn.addEventListener("click", () => {
  expTopicInput.value = RANDOM_TOPICS[Math.floor(Math.random() * RANDOM_TOPICS.length)];
});

btnExpCreate.addEventListener("click", async () => {
  btnExpCreate.disabled = true;
  const original = btnExpCreate.textContent;
  btnExpCreate.textContent = "生成中（约 10-20 秒）...";
  try {
    const data = await api.experimentCreate(expTopicInput.value.trim(), expLevelSelect.value);
    expSessionId = data.session_id;
    expWords = data.words || [];
    expTopicLabel.textContent = `领域：${data.topic} · 共 ${data.total} 个单词`;
    expLearnStatus.textContent = "";
    renderLearnCards();
    showStage("learning");
    await generateImages(data.words.filter((w) => w.is_multimodal));
    btnExpToTest.disabled = false;
    expPrepareHint.textContent = "材料已就绪，请充分学习后开始测试";
  } catch (err) {
    showToast(`生成失败：${err.message}`, "error");
  } finally {
    btnExpCreate.disabled = false;
    btnExpCreate.textContent = original;
  }
});

function renderLearnCards() {
  expLearnGrid.innerHTML = expWords.map((w) => {
    if (w.is_multimodal) {
      return `
      <div class="exp-card exp-card-mm" data-word="${w.id}">
        <div class="exp-card-head">
          <span class="exp-card-jp">${esc(w.japanese)}</span>
          <button class="exp-speak" data-speak="${esc(w.japanese)}" data-kana="${esc(w.kana)}">🔊</button>
        </div>
        <div class="exp-card-kana">${esc(w.kana)}</div>
        <div class="exp-card-img" id="exp-img-${w.id}"><span class="exp-img-loading">图片生成中...</span></div>
        ${w.example_ja ? `<div class="exp-card-ex">${esc(w.example_ja)}</div>` : ""}
        ${w.example_cn ? `<div class="exp-card-ex-cn">${esc(w.example_cn)}</div>` : ""}
      </div>`;
    }
    return `
    <div class="exp-card exp-card-plain" data-word="${w.id}">
      <div class="exp-card-head">
        <span class="exp-card-jp">${esc(w.japanese)}</span>
      </div>
      <div class="exp-card-kana">${esc(w.kana)}</div>
    </div>`;
  }).join("");

  // 语音播放（多模态组）
  expLearnGrid.querySelectorAll(".exp-speak").forEach((btn) => {
    btn.addEventListener("click", () => speakWord(btn.dataset.speak, btn.dataset.kana, btn));
  });
}

/** 逐张生成多模态配图（避免单请求超时，实时展示进度） */
async function generateImages(mmWords) {
  const total = mmWords.length;
  if (!total) return;
  let done = 0;
  expImageHint.textContent = `正在生成配图 0/${total}（多模态材料准备中）`;
  for (const w of mmWords) {
    try {
      const res = await api.experimentImage(w.id);
      const box = document.getElementById(`exp-img-${w.id}`);
      if (box) {
        box.innerHTML = res.image_base64
          ? `<img src="${res.image_base64}" alt="${esc(w.japanese)}" loading="lazy" />`
          : '<span class="exp-img-loading">配图生成失败</span>';
      }
    } catch (err) {
      const box = document.getElementById(`exp-img-${w.id}`);
      if (box) box.innerHTML = '<span class="exp-img-loading">配图生成失败</span>';
    }
    done += 1;
    expImageProgress.style.width = `${Math.round((done / total) * 100)}%`;
    expImageHint.textContent = `正在生成配图 ${done}/${total}`;
  }
  expImageHint.textContent = `配图已完成（${total} 张）`;
}

// ── 阶段二：进入测试 ──
btnExpToTest.addEventListener("click", async () => {
  btnExpToTest.disabled = true;
  try {
    const data = await api.experimentQuiz(expSessionId);
    expQuiz = data.quiz || [];
    expQuiz.forEach((q) => delete expAnswers[q.word_id]);
    renderQuiz();
    showStage("testing");
    updateTestProgress();
  } catch (err) {
    showToast(`加载测试失败：${err.message}`, "error");
    btnExpToTest.disabled = false;
  }
});

function renderQuiz() {
  expTestList.innerHTML = expQuiz.map((q, idx) => `
    <div class="exp-quiz-item" data-quiz="${q.word_id}">
      <div class="exp-quiz-head">
        <span class="exp-quiz-num">${idx + 1}</span>
        <span class="exp-quiz-jp">${esc(q.japanese)}</span>
        <span class="exp-quiz-kana">${esc(q.kana)}</span>
      </div>
      <div class="exp-quiz-options">
        ${q.options.map((opt) => `
          <label class="exp-option">
            <input type="radio" name="quiz-${q.word_id}" value="${esc(opt)}" data-word="${q.word_id}" />
            <span>${esc(opt)}</span>
          </label>`).join("")}
      </div>
    </div>`).join("");

  expTestList.querySelectorAll("input[type=radio]").forEach((input) => {
    input.addEventListener("change", () => {
      expAnswers[input.dataset.word] = input.value;
      updateTestProgress();
    });
  });
}

function updateTestProgress() {
  const answered = Object.keys(expAnswers).length;
  const total = expQuiz.length;
  expTestProgressLabel.textContent = `进度 ${answered}/${total}`;
  expTestAnswered.textContent = `已作答 ${answered} 题`;
  expTestProgress.style.width = `${total ? Math.round((answered / total) * 100) : 0}%`;
  btnExpSubmit.disabled = answered < total;
  expSubmitHint.textContent = answered < total
    ? `还有 ${total - answered} 题未作答`
    : "已全部作答，可提交";
}

// ── 阶段三：提交并展示结果 ──
btnExpSubmit.addEventListener("click", async () => {
  btnExpSubmit.disabled = true;
  const original = btnExpSubmit.textContent;
  btnExpSubmit.textContent = "提交中...";
  try {
    const answers = Object.entries(expAnswers).map(([wordId, choice]) => ({
      word_id: parseInt(wordId, 10),
      choice,
    }));
    const res = await api.experimentSubmit(expSessionId, answers);
    renderResult(res);
    showStage("result");
    loadHistory();
  } catch (err) {
    showToast(`提交失败：${err.message}`, "error");
    btnExpSubmit.disabled = false;
  } finally {
    btnExpSubmit.textContent = original;
  }
});

function renderResult(res) {
  const mm = res.multimodal || {};
  const pl = res.plain || {};
  expResultCards.innerHTML = `
    <div class="exp-result-card mm">
      <div class="exp-result-label">🎨 多模态组</div>
      <div class="exp-result-rate">${mm.rate}%</div>
      <div class="exp-result-sub">${mm.correct}/${mm.total} 正确</div>
      <div class="exp-result-desc">图片 + 语音 + 例句</div>
    </div>
    <div class="exp-result-card plain">
      <div class="exp-result-label">📄 非多模态组</div>
      <div class="exp-result-rate">${pl.rate}%</div>
      <div class="exp-result-sub">${pl.correct}/${pl.total} 正确</div>
      <div class="exp-result-desc">仅单词 + 假名</div>
    </div>`;

  const diff = res.diff || 0;
  let verdict;
  if (diff > 0) {
    verdict = `多模态组记忆正确率高出 <b>${diff}</b> 个百分点，多模态材料对记忆有正向帮助 📈`;
  } else if (diff < 0) {
    verdict = `本次非多模态组正确率高出 <b>${Math.abs(diff)}</b> 个百分点（单次结果波动属正常）`;
  } else {
    verdict = `两组正确率持平，差异为 0`;
  }
  expVerdict.innerHTML = `${verdict}<br><span class="exp-verdict-note">本次实验共 ${mm.total + pl.total} 题 · 领域：${esc(res.topic)}</span>`;

  const details = res.details || [];
  expDetailTable.innerHTML = `
    <thead>
      <tr><th>单词</th><th>假名</th><th>正确释义</th><th>你的选择</th><th>组别</th><th>结果</th></tr>
    </thead>
    <tbody>
      ${details.map((d) => `
        <tr>
          <td>${esc(d.japanese)}</td>
          <td>${esc(d.kana)}</td>
          <td>${esc(d.chinese)}</td>
          <td>${esc(d.test_choice || "-")}</td>
          <td>${d.is_multimodal ? "🎨 多模态" : "📄 非多模态"}</td>
          <td class="${d.test_correct ? "exp-ok" : "exp-bad"}">${d.test_correct ? "✅" : "❌"}</td>
        </tr>`).join("")}
    </tbody>`;
}

btnExpAgain.addEventListener("click", () => {
  expSessionId = null;
  expWords = [];
  expQuiz = [];
  Object.keys(expAnswers).forEach((k) => delete expAnswers[k]);
  expImageProgress.style.width = "0%";
  btnExpToTest.disabled = true;
  showStage("config");
});

// ── 历史记录 ──
async function loadHistory() {
  try {
    const data = await api.experimentMy();
    const list = data.sessions || [];
    if (!list.length) {
      expHistory.innerHTML = '<div class="exp-history-empty">还没有实验记录，完成一次实验后这里会显示历史成绩</div>';
      return;
    }
    expHistory.innerHTML = list.map((s) => `
      <div class="exp-history-item">
        <div class="exp-history-main">
          <span class="exp-history-topic">${esc(s.topic)}</span>
          <span class="exp-history-time">${fmtTime(s.created_at)}</span>
        </div>
        ${s.status === "done"
          ? `<div class="exp-history-scores">
               <span class="exp-score mm">🎨 ${s.multimodal_correct}/${s.multimodal_total}</span>
               <span class="exp-score plain">📄 ${s.plain_correct}/${s.plain_total}</span>
             </div>`
          : '<span class="exp-history-pending">未完成测试</span>'}
      </div>`).join("");
  } catch (err) {
    expHistory.innerHTML = '<div class="exp-history-empty">历史记录加载失败</div>';
  }
}

// ── 入口 ──
initPage().then((ok) => {
  if (!ok) return;
  loadHistory();
});
