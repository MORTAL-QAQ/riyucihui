/**
 * 系统管理独立子页逻辑（阶段二多页架构，仅管理员可访问）
 * 依赖：api.js + common.js（$ / esc / showToast / initPage / isAdmin）
 */

// ===== 管理员页 =====
const adminCardsGrid = $("#admin-cards-grid");
const adminTabUsers = $("#admin-tab-users");
const adminTabLogins = $("#admin-tab-logins");
const adminPanelUsers = $("#admin-panel-users");
const adminPanelLogins = $("#admin-panel-logins");
const adminLoginReports = $("#admin-login-reports");

let adminUsersCache = [];

adminTabUsers.addEventListener("click", () => switchAdminTab("users"));
adminTabLogins.addEventListener("click", () => switchAdminTab("logins"));

// 管理员创建用户
$("#btn-admin-create-user").addEventListener("click", async () => {
  const uname = prompt("请输入新账号（2-50个字符）：");
  if (!uname) return;
  if (uname.length < 2 || uname.length > 50) { showToast("账号需2-50个字符", "error"); return; }
  const pw1 = prompt("请输入密码（至少6位）：");
  if (!pw1) return;
  if (pw1.length < 6) { showToast("密码至少6位", "error"); return; }
  const pw2 = prompt("请再次输入密码确认：");
  if (pw1 !== pw2) { showToast("两次密码不一致", "error"); return; }
  try {
    const res = await api.adminCreateUser(uname, pw1);
    showToast(res.message);
    loadAdmin();
  } catch (err) {
    showToast(`创建失败：${err.message}`, "error");
  }
});

function switchAdminTab(tab) {
  adminTabUsers.classList.toggle("active", tab === "users");
  adminTabLogins.classList.toggle("active", tab === "logins");
  adminPanelUsers.style.display = tab === "users" ? "block" : "none";
  adminPanelLogins.style.display = tab === "logins" ? "block" : "none";
  if (tab === "users") renderAdminCards();
  if (tab === "logins") loadAdminLogins();
}

async function loadAdminLogins() {
  try {
    const reports = await api.adminLoginHistory();
    if (!reports || reports.length === 0) {
      adminLoginReports.innerHTML =
        '<div class="empty-state"><div class="empty-icon">📭</div><p>暂无登录记录</p></div>';
      return;
    }

    let html = "";
    reports.forEach((r) => {
      html += `
      <div class="login-report-card">
        <div class="login-report-header" data-user="${r.user_id}">
          <div class="login-report-user">
            <span class="login-report-avatar">👤</span>
            <div>
              <div class="login-report-username">${esc(r.name || r.username)}</div>
              <div class="login-report-meta">
                账号 ${esc(r.username)} ·
                共 <strong>${r.login_count}</strong> 次登录 ·
                首次 ${formatDate(r.first_login)} ·
                最近 ${formatDate(r.last_login)}
              </div>
            </div>
          </div>
          <span class="login-report-toggle">▶</span>
        </div>
        <div class="login-report-body" style="display:none">
          <table class="admin-table login-table">
            <thead>
              <tr><th>#</th><th>登录时间</th><th>IP 地址</th></tr>
            </thead>
            <tbody>
              ${r.logins.map((l, i) => `
                <tr>
                  <td>${i + 1}</td>
                  <td>${formatDateTime(l.login_at)}</td>
                  <td>${esc(l.ip_address || "N/A")}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </div>`;
    });

    adminLoginReports.innerHTML = html;

    // 点击展开/折叠
    adminLoginReports.querySelectorAll(".login-report-header").forEach((hdr) => {
      hdr.addEventListener("click", () => {
        const body = hdr.nextElementSibling;
        const toggle = hdr.querySelector(".login-report-toggle");
        const visible = body.style.display !== "none";
        body.style.display = visible ? "none" : "block";
        toggle.textContent = visible ? "▶" : "▼";
      });
    });
  } catch (err) {
    adminLoginReports.innerHTML =
      `<div class="error-msg">加载失败：${esc(err.message)}</div>`;
  }
}

function formatDateTime(isoStr) {
  if (!isoStr) return "N/A";
  const d = new Date(isoStr);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function formatDate(isoStr) {
  if (!isoStr) return "N/A";
  const d = new Date(isoStr);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
}

async function loadAdmin() {
  try {
    const stats = await api.adminStats();
    $("#stat-users").textContent = stats.total_users;
    $("#stat-words").textContent = stats.total_words;
    $("#stat-ai").textContent = stats.total_ai_calls;
    $("#stat-tokens").textContent = formatTokens(stats.total_tokens);

    const users = await api.adminUsers();
    adminUsersCache = users;
    renderAdminCards();
  } catch (err) {
    showToast(`加载管理页失败：${err.message}`, "error");
  }
}

function formatTokens(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
  if (n >= 1000) return (n / 1000).toFixed(1) + "K";
  return String(n);
}

function effectiveLimit(dbValue, defaultValue) {
  if (dbValue !== null && dbValue !== undefined) return dbValue;
  return defaultValue;
}

function formatLimit(v, effectiveDefault) {
  const eff = effectiveLimit(v, effectiveDefault);
  if (eff === null || eff === undefined) return "不限";
  return String(eff) + "/天";
}

function limitUsageClass(used, limit) {
  if (limit === null || limit === undefined || limit <= 0) return "";
  if (used >= limit) return "full";
  if (used / limit >= 0.8) return "warn";
  return "";
}

function limitBarPct(used, limit) {
  if (!limit) return 0;
  return Math.min(100, (used / limit) * 100);
}

function renderLimitRow(opts) {
  const { icon, label, used, total, limit, effectiveDefault, kind, selectOptions } = opts;
  const eff = effectiveLimit(limit, effectiveDefault);
  const pct = limitBarPct(used, eff);
  const barClass = limitUsageClass(used, eff);
  const usedClass = limitUsageClass(used, eff);

  const usedDisplay = eff != null ? `${used}<span class="dim"> / ${eff}</span>` : `${used}<span class="dim"> / 不限</span>`;
  const countLabel = total != null ? `<span class="dim">总${total}</span>` : "";

  return `
    <div class="admin-limit-row">
      <span class="admin-limit-icon">${icon}</span>
      <span class="admin-limit-label">${label}</span>
      <div class="admin-limit-bar-wrap">
        <div class="admin-limit-bar-fill ${barClass}" style="width:${pct}%"></div>
      </div>
      <span class="admin-limit-usage">
        <span class="${usedClass}">${usedDisplay}</span>
        ${countLabel}
      </span>
      <select class="admin-limit-select" data-kind="${kind}" data-userid="${opts.userId}" data-username="${opts.username}">
        <option value="">设置</option>
        ${selectOptions.map(o => `<option value="${o.val}">${o.label}</option>`).join("")}
      </select>
    </div>`;
}

function renderAdminCards() {
  const grid = adminCardsGrid;
  const users = adminUsersCache;

  // Limit preset options
  const aiOptions = [
    { val: "0", label: "AI: 0次" },
    { val: "10", label: "AI: 10次" },
    { val: "25", label: "AI: 25次" },
    { val: "50", label: "AI: 50次" },
    { val: "100", label: "AI: 100次" },
    { val: "-1", label: "AI: 不限" },
  ];
  const voiceOptions = [
    { val: "0", label: "语音: 0次" },
    { val: "20", label: "语音: 20次" },
    { val: "50", label: "语音: 50次" },
    { val: "100", label: "语音: 100次" },
    { val: "-1", label: "语音: 不限" },
  ];
  const wordOptions = [
    { val: "0", label: "单词: 0个" },
    { val: "50", label: "单词: 50个" },
    { val: "100", label: "单词: 100个" },
    { val: "200", label: "单词: 200个" },
    { val: "500", label: "单词: 500个" },
    { val: "-1", label: "单词: 不限" },
  ];
  const imageOptions = [
    { val: "0", label: "图片: 0张" },
    { val: "3", label: "图片: 3张" },
    { val: "10", label: "图片: 10张" },
    { val: "30", label: "图片: 30张" },
    { val: "-1", label: "图片: 不限" },
  ];

  grid.innerHTML = users.map((u) => {
    const usage = u.usage || {};
    const aid = u.id;
    const unm = esc(u.name || u.username);   // 主显示：昵称
    const acc = esc(u.username);             // 次要：账号

    return `
    <div class="admin-user-card">
      <div class="admin-card-header">
        <div class="admin-card-user">
          <span class="admin-card-avatar">${u.is_admin ? "🛡" : "👤"}</span>
          <span class="admin-card-username">${unm}</span>
          <span class="admin-card-role ${u.is_admin ? "admin" : "user"}">${u.is_admin ? "管理员" : "用户"}</span>
        </div>
        <div class="admin-card-meta">
          <span>ID:${aid}</span>
          <span>@${acc}</span>
          <span>单词:${u.word_count}</span>
          <span>学习:${u.study_count}</span>
        </div>
      </div>
      <div class="admin-card-remark" data-userid="${aid}">
        <span class="admin-card-remark-text">${u.remark ? esc(u.remark) : '<span class="dim">无备注</span>'}</span>
        <button class="admin-card-remark-edit" data-action="edit-remark" data-id="${aid}" data-username="${acc}" data-remark="${u.remark ? esc(u.remark) : ''}">✎</button>
      </div>
      <div class="admin-card-group">
        <span class="admin-card-group-label">实验分组</span>
        <select class="admin-group-select" data-action="set-group" data-id="${aid}" data-username="${acc}">
          <option value="">未分组</option>
          <option value="experiment" ${u.experiment_group === "experiment" ? "selected" : ""}>实验组</option>
          <option value="control" ${u.experiment_group === "control" ? "selected" : ""}>对照组</option>
        </select>
      </div>
      <div class="admin-card-body">
        ${renderLimitRow({
          icon: "🤖", label: "AI调用", kind: "ai",
          used: usage.today_ai || 0, total: usage.total_ai || 0,
          limit: u.daily_ai_limit, effectiveDefault: u.is_admin ? null : 25,
          userId: aid, username: unm, selectOptions: aiOptions,
        })}
        ${renderLimitRow({
          icon: "🎤", label: "语音", kind: "voice",
          used: usage.today_voice || 0, total: usage.total_voice || 0,
          limit: u.daily_voice_limit, effectiveDefault: null,
          userId: aid, username: unm, selectOptions: voiceOptions,
        })}
        ${renderLimitRow({
          icon: "📝", label: "单词", kind: "word",
          used: usage.today_word || 0, total: usage.total_word || 0,
          limit: u.daily_word_limit, effectiveDefault: u.is_admin ? null : 100,
          userId: aid, username: unm, selectOptions: wordOptions,
        })}
        ${renderLimitRow({
          icon: "🖼", label: "图片", kind: "image",
          used: usage.today_image || 0, total: usage.total_image || 0,
          limit: u.daily_image_limit, effectiveDefault: u.is_admin ? null : 3,
          userId: aid, username: unm, selectOptions: imageOptions,
        })}
      </div>
      <div class="admin-card-actions">
        <button class="btn btn-outline btn-sm" data-action="toggle-admin" data-id="${aid}" data-username="${acc}" data-current="${u.is_admin}">
          ${u.is_admin ? "取消管理" : "设为管理"}
        </button>
        <button class="btn btn-outline btn-sm" data-action="reset-password" data-id="${aid}" data-username="${acc}">重置密码</button>
        <button class="btn-sm-danger" data-action="delete-user" data-id="${aid}" data-username="${acc}">删除</button>
      </div>
    </div>`;
  }).join("");

  // Toggle admin
  grid.querySelectorAll('[data-action="toggle-admin"]').forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = parseInt(btn.dataset.id);
      const username = btn.dataset.username;
      if (!confirm(`确定修改 ${username} 的管理员状态吗？`)) return;
      try {
        const res = await api.toggleAdmin(id);
        showToast(res.message);
        loadAdmin();
      } catch (err) {
        showToast(`操作失败：${err.message}`, "error");
      }
    });
  });

  // Reset password
  grid.querySelectorAll('[data-action="reset-password"]').forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = parseInt(btn.dataset.id);
      const username = btn.dataset.username;
      const pw1 = prompt(`请输入「${username}」的新密码（至少6位）：`);
      if (!pw1) return;
      if (pw1.length < 6) { showToast("密码至少需要6位", "error"); return; }
      const pw2 = prompt("请再次输入新密码确认：");
      if (!pw2) return;
      if (pw1 !== pw2) { showToast("两次输入的密码不一致", "error"); return; }
      try {
        const res = await api.resetUserPassword(id, pw1);
        showToast(res.message);
      } catch (err) {
        showToast(`重置失败：${err.message}`, "error");
      }
    });
  });

  // Delete user
  grid.querySelectorAll('[data-action="delete-user"]').forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = parseInt(btn.dataset.id);
      const username = btn.dataset.username;
      if (!confirm(`确定删除用户「${username}」及其所有数据吗？此操作不可恢复！`)) return;
      try {
        const res = await api.deleteUser(id);
        showToast(res.message);
        loadAdmin();
      } catch (err) {
        showToast(`删除失败：${err.message}`, "error");
      }
    });
  });

  // Edit remark
  grid.querySelectorAll('[data-action="edit-remark"]').forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = parseInt(btn.dataset.id);
      const username = btn.dataset.username;
      const current = btn.dataset.remark || "";
      const remark = prompt(`「${username}」的备注（最多200字）：`, current);
      if (remark === null) return; // cancelled
      if (remark.length > 200) { showToast("备注不能超过200字", "error"); return; }
      try {
        await api.setUserRemark(id, remark || null);
        showToast("备注已更新");
        loadAdmin();
      } catch (err) {
        showToast(`备注保存失败：${err.message}`, "error");
      }
    });
  });

  // Set experiment group — per-card select
  grid.querySelectorAll('[data-action="set-group"]').forEach((sel) => {
    sel.addEventListener("change", async () => {
      const id = parseInt(sel.dataset.id);
      const username = sel.dataset.username;
      const group = sel.value; // "" / "experiment" / "control"
      try {
        const res = await api.setUserGroup(id, group);
        showToast(res.message);
        loadAdmin();  // 刷新以同步徽标与选中态
      } catch (err) {
        showToast(`分组设置失败：${err.message}`, "error");
        sel.value = sel.dataset.prev || "";
      }
    });
    sel.addEventListener("focus", () => { sel.dataset.prev = sel.value; });
  });

  // Set limits — per-row select
  grid.querySelectorAll('.admin-limit-select').forEach((sel) => {
    sel.addEventListener("change", async () => {
      const val = sel.value;
      if (!val) return;
      const kind = sel.dataset.kind;
      const limitVal = val === "-1" ? null : parseInt(val);
      const userId = parseInt(sel.dataset.userid);
      const username = sel.dataset.username;

      const user = adminUsersCache.find((u) => u.id === userId);
      if (!user) return;

      const aiLimit = kind === "ai" ? limitVal : user.daily_ai_limit;
      const voiceLimit = kind === "voice" ? limitVal : user.daily_voice_limit;
      const wordLimit = kind === "word" ? limitVal : user.daily_word_limit;
      const imageLimit = kind === "image" ? limitVal : user.daily_image_limit;

      try {
        // Use extended setUserLimits with image support
        await request("/admin/users/" + userId + "/limits", {
          method: "PUT",
          body: JSON.stringify({
            daily_ai_limit: aiLimit,
            daily_voice_limit: voiceLimit,
            daily_word_limit: wordLimit,
            daily_image_limit: imageLimit,
          }),
        });
        showToast(`已更新 ${username} 的限额`);
        sel.value = "";
        loadAdmin();
      } catch (err) {
        showToast(`设置失败：${err.message}`, "error");
        sel.value = "";
      }
    });
  });
}

// ── 入口：认证 + 管理员校验 → 加载管理数据 ──
initPage().then((ok) => {
  if (!ok) return;
  if (!isAdmin) {
    showToast("无权限访问管理页", "error");
    location.href = "/";
    return;
  }
  loadAdmin();
});
