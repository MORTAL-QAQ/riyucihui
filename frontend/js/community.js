/**
 * 社区独立子页逻辑（阶段二多页架构）
 * 依赖：api.js（请求层）+ common.js（$ / esc / fmtTime / showToast / handleApiError
 *       / speakWord / initPage / initSidebar / currentUsername / isAdmin）
 */

let communityOffset = 0;
let communityHasMore = true;
let currentCommunityDetail = null;

const communityModalEl = $("#community-modal");

function communityEl(id) {
  return document.getElementById(id);
}

// 头像文字：用户名首字符（大写化），空名兜底
function communityAvatarText(name) {
  const s = (name || "?").trim();
  return esc((s.charAt(0) || "?").toUpperCase());
}

// 头像渐变盘：按 id 稳定取色
function communityGrad(id) {
  return "grad-" + ((id % 6) + 1);
}

function communityCardHtml(p) {
  const isAnnouncement = p.type === "announcement";
  const preview = p.content.length > 160 ? p.content.slice(0, 160) + "…" : p.content;
  return `
    <div class="community-post ${isAnnouncement ? "announcement" : ""}" data-id="${p.id}">
      <div class="community-post-head">
        <span class="community-avatar ${communityGrad(p.id)}">${communityAvatarText(p.username)}</span>
        <div class="community-post-main">
          <div class="community-post-title-line">
            <span class="community-post-title">${esc(p.title)}</span>
            ${isAnnouncement ? '<span class="community-tag">📢 公告</span>' : ""}
            ${p.is_pinned ? '<span class="community-tag pin">📌 置顶</span>' : ""}
          </div>
          <div class="community-post-meta">
            <span>👤 ${esc(p.username)}</span>
            <span class="dot">·</span>
            <span>🕐 ${fmtTime(p.created_at)}</span>
          </div>
        </div>
        <div class="community-post-stats">
          <span class="community-stat">👍 <b>${p.like_count}</b></span>
          <span class="community-stat">💬 <b>${p.comment_count}</b></span>
        </div>
      </div>
      ${p.content.trim()
        ? `<div class="community-post-content">${esc(preview)}</div>`
        : '<div class="community-post-content empty">（暂无内容）</div>'}
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

    // 横幅统计
    communityEl("community-total").textContent = data.total;
    communityEl("community-pinned-count").textContent = pinned.length;
    communityEl("community-announcement-chip").style.display = pinned.length ? "" : "none";

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
  if (!title) {
    showToast("请填写标题", "error");
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
    communityEl("community-char-count").textContent = "0";
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
      <div class="community-detail-head">
        <span class="community-avatar sm ${communityGrad(data.post.id)}">${communityAvatarText(data.post.username)}</span>
        <div class="community-detail-meta">
          <span class="community-detail-user">${esc(data.post.username)}</span>
          <span class="community-detail-time">🕐 ${fmtTime(data.post.created_at)}</span>
          ${data.post.type === "announcement" ? '<span class="community-tag">📢 公告</span>' : ""}
          ${data.post.is_pinned ? '<span class="community-tag pin">📌 置顶</span>' : ""}
        </div>
      </div>
      <div class="community-detail-content${data.post.content.trim() ? "" : " empty"}">${data.post.content.trim()
        ? esc(data.post.content)
        : "（该帖暂无内容）"}</div>
      <div class="community-detail-like-bar">👍 ${data.post.like_count} · 💬 ${data.post.comment_count}</div>
      <div class="community-comments-title">评论（${data.comments.length}）</div>
      <div class="community-comments" id="community-comments">
        ${data.comments.length
          ? data.comments
              .map(
                (c) => `
          <div class="community-comment">
            <span class="community-avatar xs ${communityGrad(c.id)}">${communityAvatarText(c.username)}</span>
            <div class="community-comment-main">
              <div class="community-comment-head">
                <span class="community-comment-user">${esc(c.username)}</span>
                <span class="community-comment-time">${fmtTime(c.created_at)}</span>
                ${c.username === currentUsername || data.is_admin
                  ? `<button class="community-comment-del" data-del="${c.id}">×</button>` : ""}
              </div>
              <div class="community-comment-text">${esc(c.content)}</div>
            </div>
          </div>`
              )
              .join("")
          : '<div class="community-no-comments">还没有评论，快来抢沙发 🛋️</div>'}
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

// ── 事件绑定（列表点击用事件委托） ──
communityEl("btn-community-submit").addEventListener("click", () => submitCommunityPost(false));
communityEl("btn-announcement-submit").addEventListener("click", () => submitCommunityPost(true));
communityEl("community-list").addEventListener("click", (e) => {
  const card = e.target.closest(".community-post");
  if (card) openCommunityDetail(parseInt(card.dataset.id, 10));
});
communityEl("btn-community-more").addEventListener("click", () => loadCommunity(false));

// 发布内容字数统计
communityEl("community-content-input").addEventListener("input", (e) => {
  communityEl("community-char-count").textContent = e.target.value.length;
});

// ── 入口：认证 → 初始化 → 加载列表 ──
initSidebar();
initPage().then((ok) => {
  if (ok) loadCommunity(true);
});
