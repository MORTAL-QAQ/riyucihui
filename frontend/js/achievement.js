/**
 * 成就独立子页逻辑（阶段二多页架构）
 * 依赖：api.js + common.js（$ / esc / showToast / initPage）
 */

// ── 成就页 ──
async function loadAchievements() {
  try {
    const data = await api.listAchievements();
    const items = data.achievements;
    const categories = data.categories || {};

    const achieved = items.filter((a) => a.achieved).length;
    $("#achievement-stats-row").innerHTML = `
      <div class="achievement-stat">
        <div class="achievement-stat-num">${achieved}</div>
        <div class="achievement-stat-label">已解锁</div>
      </div>
      <div class="achievement-stat">
        <div class="achievement-stat-num">${items.length - achieved}</div>
        <div class="achievement-stat-label">未解锁</div>
      </div>
    `;

    // Group by category
    const grouped = {};
    const catOrder = [];
    for (const a of items) {
      if (!grouped[a.category]) {
        grouped[a.category] = [];
        catOrder.push(a.category);
      }
      grouped[a.category].push(a);
    }

    $("#achievement-grid").innerHTML = catOrder
      .map((cat) => {
        const label = categories[cat] || cat;
        const catAchieved = grouped[cat].filter((a) => a.achieved).length;
        const catTotal = grouped[cat].length;
        const cards = grouped[cat]
          .map((a) => {
            const dateStr = a.achieved_at ? a.achieved_at.slice(0, 10) : "";
            return `
          <div class="achievement-card ${a.achieved ? "" : "locked"}">
            <div class="achievement-icon">${a.icon}</div>
            <div class="achievement-name">${esc(a.name)}</div>
            <div class="achievement-desc">${esc(a.description)}</div>
            ${a.achieved ? `<div class="achievement-date">${dateStr}</div>` : '<div class="achievement-date" style="color:var(--text-muted)">未解锁</div>'}
          </div>`;
          })
          .join("");
        return `
        <div class="achievement-category expanded">
          <div class="achievement-cat-header" data-action="toggle-cat">
            <span class="achievement-cat-header-left">
              <span class="achievement-cat-arrow">▶</span>
              <span>${label}</span>
            </span>
            <span class="achievement-cat-progress">${catAchieved}/${catTotal}</span>
          </div>
          <div class="achievement-cat-cards">${cards}</div>
        </div>`;
      })
      .join("");

    // Click handler for category collapse/expand
    $("#achievement-grid").querySelectorAll('[data-action="toggle-cat"]').forEach((header) => {
      header.addEventListener("click", () => {
        header.parentElement.classList.toggle("expanded");
      });
    });
  } catch (err) {
    showToast(`加载成就失败：${err.message}`, "error");
  }
}

// ── 入口：认证 → 加载成就 ──
initPage().then((ok) => {
  if (ok) loadAchievements();
});
