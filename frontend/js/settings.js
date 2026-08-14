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

// ── 入口：认证 → 加载设置 ──
initPage().then((ok) => {
  if (ok) loadSettings();
});
