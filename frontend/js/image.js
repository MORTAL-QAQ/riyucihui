/**
 * 图片词卡独立子页逻辑（阶段二多页架构）
 * 依赖：api.js + common.js（$ / esc / showToast / speakWord / showImageLightbox / initPage）
 */

// ── DOM 引用 ──
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
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var wrap = entry.target;
      var wordId = parseInt(wrap.dataset.wordId);
      if (!wordId || wrap.dataset.loaded === "1") return;
      wrap.dataset.loaded = "1";
      api.getImageCardData(wordId).then(function (data) {
        if (data.image_base64) {
          wrap.innerHTML = '<img src="' + esc(data.image_base64) + '" alt="" />';
          wrap.querySelector("img").addEventListener("click", function () {
            showImageLightbox(data.image_base64);
          });
        }
      }).catch(function () {
        wrap.innerHTML = '<div class="img-placeholder"><span>❌</span></div>';
      });
    });
  }, { rootMargin: "200px" });

  imageCardGrid.querySelectorAll(".image-card-img-wrap").forEach(function (wrap) {
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

// ── 入口：认证 → 加载词卡 ──
initPage().then((ok) => {
  if (ok) loadImageCards();
});
