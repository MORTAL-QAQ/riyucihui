/**
 * 背词独立子页逻辑（阶段二多页架构）
 * 依赖：api.js + common.js（$ / $$ / esc / jlptBadge / showToast / handleApiError
 *       / speakWord / showImageLightbox / initPage / currentUsername / isAdmin）
 */

// ── DOM 引用 ──
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
const btnStudyUndo = $("#btn-study-undo");
const studySessionStats = $("#study-session-stats");
const listeningActions = $("#study-listening-actions");
const btnListeningPlay = $("#btn-listening-play");
const btnListeningReveal = $("#btn-listening-reveal");
const flashcardHint = $("#flashcard-hint");

// ── 状态 ──
let studyMode = "kanji2kana";
let studyWords = [];
let studyIndex = 0;
let selectedTopics = [];
let showBack = false;
let studySubTab = "new";
let studyHistory = [];
let studyListeningAudio = false;
let lastReviewResult = null;
let studyReviewing = false;
let touchStartX = 0, touchStartY = 0, touchMoved = false;

// ── 视图切换 ──
function showStudyView(view) {
  studyPick.style.display = view === "pick" ? "block" : "none";
  studySession.style.display = view === "session" ? "block" : "none";
  studyDone.style.display = view === "done" ? "block" : "none";
  if (view !== "session") {
    listeningActions.style.display = "none";
    flashcardHint.style.display = "";
  }
}

// ── 选题 ──
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

// ── 开始学习 ──
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

// ── 闪卡渲染 ──
function renderFlashcard() {
  const w = studyWords[studyIndex];
  flashcard.classList.remove("flipped");
  showBack = false;
  studyReviewing = false;
  studyListeningAudio = false;
  btnStudyUndo.style.display = lastReviewResult ? "" : "none";
  btnStudyUndo.textContent = "↩ 返回上一个单词";

  if (studyMode === "listening") {
    listeningActions.style.display = "";
    flashcardHint.style.display = "none";
    flashcardFront.innerHTML = `<span style="font-size:48px">🔊</span><br><span style="font-size:14px;color:#9ca3af">听听看，想起这个单词了吗？</span>`;
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

  const backMain = $("#flashcard-back-main");
  if (studyMode === "listening") {
    backMain.innerHTML = `<div class="flashcard-answer" style="font-size:28px">${esc(w.japanese)} <span style="font-size:16px;color:#9ca3af">${esc(w.kana)}</span></div><div class="flashcard-meaning">${esc(w.chinese)}</div>`;
  } else if (studyMode === "kanji2kana") {
    backMain.innerHTML = `<div class="flashcard-answer">${esc(w.kana)}</div><div class="flashcard-meaning">${esc(w.chinese)}</div>`;
  } else {
    backMain.innerHTML = `<div class="flashcard-answer">${esc(w.japanese)}</div><div class="flashcard-meaning">${esc(w.chinese)}</div>`;
  }

  const exampleDiv = $("#flashcard-example");
  if (w.example_ja) {
    exampleDiv.style.display = "block";
    exampleDiv.innerHTML = `<div class="flashcard-example-ja">${esc(w.example_ja)}</div><div class="flashcard-example-cn">${esc(w.example_cn)}</div>`;
  } else {
    exampleDiv.style.display = "none";
  }

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

  const infoDiv = $("#flashcard-study-info");
  const s = w.stage ?? 0;
  const dots = Array.from({ length: 7 }, (_, i) =>
    `<span class="study-stage-dot ${s >= 7 ? "mastered" : i < s ? "filled" : ""}"></span>`
  ).join("");
  infoDiv.innerHTML = `<span>阶段 ${s}/7</span><span class="study-stage-bar">${dots}</span><span>复习 ${w.review_count || 0} 次</span>`;

  const speakBtn = $("#flashcard-speak-btn");
  speakBtn.dataset.speak = w.japanese;
  speakBtn.dataset.kana = w.kana;

  studyProgressText.textContent = `${studyIndex + 1} / ${studyWords.length}`;
  studyBarFill.style.width = `${((studyIndex + 1) / studyWords.length) * 100}%`;

  qualityBtns.forEach((b) => (b.disabled = false));
}

// ── 翻牌交互 ──
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
  if (touchMoved) return;
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

flashcard.addEventListener("touchend", (e) => {
  if (!showBack || studyReviewing || !touchMoved) return;
  const dx = e.changedTouches[0].clientX - touchStartX;
  if (Math.abs(dx) < 50) return;
  if (dx > 0) {
    recordReview(5);
  } else {
    recordReview(1);
  }
  touchMoved = false;
});

btnListeningPlay.addEventListener("click", (e) => {
  e.stopPropagation();
  const w = studyWords[studyIndex];
  studyListeningAudio = true;
  speakWord(w.japanese, w.kana, null);
  flashcardFront.innerHTML = `<span style="font-size:48px">🔊</span><br><span style="font-size:14px;color:#6366f1">正在播放… 想起来了吗？</span>`;
});

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

$("#flashcard-speak-btn").addEventListener("click", (e) => {
  e.stopPropagation();
  const btn = e.currentTarget;
  speakWord(btn.dataset.speak, btn.dataset.kana, btn);
});

// ── 评分 ──
qualityBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    if (!showBack || studyReviewing) return;
    recordReview(parseInt(btn.dataset.quality));
  });
});

async function recordReview(quality) {
  if (studyReviewing) return;
  studyReviewing = true;
  qualityBtns.forEach((b) => (b.disabled = true));
  btnStudyUndo.style.display = "none";

  const w = studyWords[studyIndex];
  const prevStage = w.stage ?? 0;
  let result;
  try {
    result = await api.recordStudy(w.id, quality);
  } catch (err) {
    studyReviewing = false;
    qualityBtns.forEach((b) => (b.disabled = false));
    if (lastReviewResult) btnStudyUndo.style.display = "";
    showToast(`记录失败：${err.message}`, "error");
    return;
  }

  lastReviewResult = {
    wordId: w.id,
    japanese: w.japanese,
    kana: w.kana,
    quality: quality,
  };

  studyHistory.push({
    japanese: w.japanese,
    kana: w.kana,
    quality: quality,
    prevStage: prevStage,
    newStage: result.stage,
  });
  w.stage = result.stage;
  w.review_count = (w.review_count || 0) + 1;

  if (result.new_achievements) {
    result.new_achievements.forEach((a) => showToast(`🏆 ${a.name}`, "achievement"));
  }

  studyIndex++;
  if (studyIndex >= studyWords.length) {
    renderSessionStats();
    showStudyView("done");
  } else {
    renderFlashcard();
  }
}

// ── 会话统计 ──
function renderSessionStats() {
  const total = studyHistory.length;
  if (total === 0) {
    studySessionStats.innerHTML = "";
    studyDoneMsg.textContent = "本轮完成！";
    return;
  }

  const correct = studyHistory.filter((h) => h.quality >= 3).length;
  const accuracy = Math.round((correct / total) * 100);
  const newlyGraduated = studyHistory.filter((h) => h.prevStage <= 0 && h.newStage >= 1).length;
  const mastered = studyHistory.filter((h) => h.newStage >= 7).length;

  const distLabels = ["完全忘了", "不太记得", "有点印象", "勉强正确", "比较顺畅", "完全掌握"];
  const distColors = ["#6b7280", "#b91c1c", "#c2410c", "#a16207", "#15803d", "#14532d"];
  const dist = [0, 0, 0, 0, 0, 0];
  studyHistory.forEach((h) => dist[h.quality]++);

  let emoji, comment;
  if (accuracy >= 90) { emoji = "🌟"; comment = "太厉害了！"; }
  else if (accuracy >= 70) { emoji = "👍"; comment = "表现不错！"; }
  else if (accuracy >= 50) { emoji = "💪"; comment = "继续加油！"; }
  else { emoji = "📚"; comment = "多复习就会进步的！"; }

  studyDoneMsg.innerHTML = `${emoji} ${comment}<br><span style="font-size:14px;font-weight:400;color:#9ca3af">正确率 ${accuracy}% (${correct}/${total})</span>`;

  let statsHtml = '<div class="session-stats-grid">';

  statsHtml += `
    <div class="session-stat-card">
      <div class="session-ring-wrap">
        <svg width="80" height="80" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r="34" fill="none" stroke="#e5e7eb" stroke-width="8"/>
          <circle cx="40" cy="40" r="34" fill="none" stroke="url(#grad)" stroke-width="8"
            stroke-dasharray="${(accuracy / 100) * 213.6} 213.6" stroke-linecap="round"
            transform="rotate(-90 40 40)" style="transition: stroke-dasharray 0.8s ease"/>
          <defs><linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#6366f1"/><stop offset="100%" stop-color="#8b5cf6"/>
          </linearGradient></defs>
          <text x="40" y="36" text-anchor="middle" font-size="18" font-weight="800" fill="#1f2937">${accuracy}%</text>
          <text x="40" y="52" text-anchor="middle" font-size="9" fill="#9ca3af">正确率</text>
        </svg>
      </div>
    </div>`;

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

// ── 撤销 ──
btnStudyUndo.addEventListener("click", () => undoReview());

async function undoReview() {
  if (studyReviewing || !lastReviewResult) return;
  studyReviewing = true;
  btnStudyUndo.style.display = "none";
  try {
    await api.undoStudy();
    studyHistory.pop();
    studyIndex--;
    lastReviewResult = null;
    showToast("已撤销上一次评分", "info");
    renderFlashcard();
  } catch (err) {
    studyReviewing = false;
    if (lastReviewResult) btnStudyUndo.style.display = "";
    showToast(`撤销失败：${err.message}`, "error");
  }
}

// ── 键盘快捷键 ──
document.addEventListener("keydown", (e) => {
  if (studySession.style.display === "none") return;
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;

  if (e.code === "Space") {
    e.preventDefault();
    if (!showBack) {
      flashcard.click();
    }
  } else if (e.key >= "1" && e.key <= "6") {
    e.preventDefault();
    const quality = parseInt(e.key) - 1;
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

// ── 子页签 ──
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
  studyTopicGrid.querySelectorAll(".study-topic-card").forEach((c) => c.classList.remove("selected"));
  loadStudyPick();
});

studySubtabReview.addEventListener("click", () => {
  if (studySubTab === "review") return;
  studySubTab = "review";
  studySubtabReview.classList.add("active");
  studySubtabNew.classList.remove("active");
  selectedTopics = [];
  btnStartStudy.textContent = "开始背诵";
  studyTopicGrid.querySelectorAll(".study-topic-card").forEach((c) => c.classList.remove("selected"));
  loadStudyPick();
});

btnStudyToggleTopics.addEventListener("click", () => {
  const visible = studyTopicWrap.style.display !== "none";
  studyTopicWrap.style.display = visible ? "none" : "block";
  btnStudyToggleTopics.classList.toggle("expanded", !visible);
});

// ── 入口：认证 → 选题 ──
initPage().then((ok) => {
  if (ok) loadStudyPick();
});
