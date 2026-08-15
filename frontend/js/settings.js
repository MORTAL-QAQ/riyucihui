/**
 * 设置独立子页逻辑（阶段二多页架构）
 * 依赖：api.js + common.js（$ / showToast / speakWord / initPage）
 */

// ── DOM 引用 ──
const settingSpeaker = $("#setting-speaker");
const settingSpeed = $("#setting-speed");
const settingPitch = $("#setting-pitch");
const settingIntonation = $("#setting-intonation");
const settingVolume = $("#setting-volume");
const btnPreview = $("#btn-preview");
const btnSaveSettings = $("#btn-save-settings");
const settingUsername = $("#setting-username");
const settingName = $("#setting-name");
const btnSaveName = $("#btn-save-name");
const pwOld = $("#pw-old");
const pwNew = $("#pw-new");
const pwConfirm = $("#pw-confirm");
const btnChangePassword = $("#btn-change-password");

const valSpeed = $("#val-speed");
const valPitch = $("#val-pitch");
const valIntonation = $("#val-intonation");
const valVolume = $("#val-volume");

const sliders = [
  { el: settingSpeed, val: valSpeed },
  { el: settingPitch, val: valPitch },
  { el: settingIntonation, val: valIntonation },
  { el: settingVolume, val: valVolume },
];

sliders.forEach(({ el, val }) => {
  el.addEventListener("input", () => {
    val.textContent = parseFloat(el.value).toFixed(2);
  });
});

async function loadSettings() {
  try {
    const [settings, speakers] = await Promise.all([
      api.getSettings(),
      api.getSpeakers(),
    ]);

    settingSpeaker.innerHTML = "";
    speakers.forEach((sp) => {
      sp.styles.forEach((st) => {
        const opt = document.createElement("option");
        opt.value = st.id;
        opt.textContent = `${sp.name} — ${st.name || st.id}`;
        if (st.id === settings.speaker) opt.selected = true;
        settingSpeaker.appendChild(opt);
      });
    });

    settingSpeed.value = settings.speed;
    settingPitch.value = settings.pitch;
    settingIntonation.value = settings.intonation;
    settingVolume.value = settings.volume;
    valSpeed.textContent = settings.speed.toFixed(2);
    valPitch.textContent = settings.pitch.toFixed(2);
    valIntonation.textContent = settings.intonation.toFixed(2);
    valVolume.textContent = settings.volume.toFixed(2);
  } catch (err) {
    showToast(`加载设置失败：${err.message}`, "error");
  }
}

btnSaveSettings.addEventListener("click", async () => {
  const data = {
    speaker: parseInt(settingSpeaker.value),
    speed: parseFloat(settingSpeed.value),
    pitch: parseFloat(settingPitch.value),
    intonation: parseFloat(settingIntonation.value),
    volume: parseFloat(settingVolume.value),
  };

  try {
    await api.saveSettings(data);
    showToast("设置已保存");
  } catch (err) {
    showToast(`保存失败：${err.message}`, "error");
  }
});

btnPreview.addEventListener("click", () => {
  btnSaveSettings.click();
  setTimeout(() => speakWord("こんにちは", "", null), 300);
});

// ── 账号信息：用户名 + 昵称 ──
async function loadAccountInfo() {
  try {
    const me = await api.me();
    settingUsername.value = me.username || "";
    settingName.value = me.name || me.username || "";
  } catch (err) {
    showToast(`加载账号信息失败：${err.message}`, "error");
  }
}

btnSaveName.addEventListener("click", async () => {
  const name = settingName.value.trim();
  if (!name) { showToast("昵称不能为空", "error"); return; }
  btnSaveName.disabled = true;
  const original = btnSaveName.textContent;
  btnSaveName.textContent = "保存中...";
  try {
    const res = await api.updateName(name);
    showToast(res.message || "昵称已更新");
    if (typeof currentUsername !== "undefined") {
      // 同步侧边栏/顶栏显示名（独立页无侧边栏，此步仅首页 SPA 生效）
      const el = $("#sidebar-username");
      if (el) el.textContent = name;
    }
  } catch (err) {
    showToast(`昵称保存失败：${err.message}`, "error");
  } finally {
    btnSaveName.disabled = false;
    btnSaveName.textContent = original;
  }
});

// ── 密码显示/隐藏切换 ──
document.querySelectorAll(".setting-pw-toggle").forEach((btn) => {
  btn.addEventListener("click", () => {
    const input = document.getElementById(btn.dataset.for);
    if (!input) return;
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.textContent = show ? "🙈" : "👁";
  });
});

// ── 修改密码 ──
btnChangePassword.addEventListener("click", async () => {
  const oldPw = pwOld.value;
  const newPw = pwNew.value;
  const confirmPw = pwConfirm.value;
  if (!oldPw) { showToast("请输入当前密码", "error"); return; }
  if (newPw.length < 6) { showToast("新密码至少 6 位", "error"); return; }
  if (newPw !== confirmPw) { showToast("两次输入的新密码不一致", "error"); return; }
  btnChangePassword.disabled = true;
  const original = btnChangePassword.textContent;
  btnChangePassword.textContent = "修改中...";
  try {
    const res = await api.changePassword(oldPw, newPw);
    showToast(res.message || "密码已修改");
    pwOld.value = pwNew.value = pwConfirm.value = "";
    // 改密码后旧 Token 已失效，跳回首页重新登录
    setTimeout(() => { clearToken(); location.href = "/"; }, 1200);
  } catch (err) {
    showToast(`修改失败：${err.message}`, "error");
  } finally {
    btnChangePassword.disabled = false;
    btnChangePassword.textContent = original;
  }
});

// ── 入口：认证 → 加载账号与设置 ──
initPage().then((ok) => {
  if (!ok) return;
  loadAccountInfo();
  loadSettings();
});
