// 问卷页渲染回归：用真实问卷定义跑一遍渲染逻辑，检查页面按题型正确输出。
// 需要先由 python 生成定义 JSON：
//   python dev_tools/dump_questionnaires.py docs/_qq_defs.json
// 用法：node dev_tools/test_questionnaire_render.js
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const defsPath = path.join(__dirname, "..", "..", "docs", "_qq_defs.json");
if (!fs.existsSync(defsPath)) {
  console.log("缺少定义文件，请先运行：python dev_tools/dump_questionnaires.py");
  process.exit(1);
}
const defs = JSON.parse(fs.readFileSync(defsPath, "utf8"));
const byCode = {};
defs.forEach((q) => { byCode[q.code] = q; });

// ── 最小 DOM mock（记录 innerHTML，便于断言）──
function makeEl(id) {
  const el = {
    id, style: {}, dataset: {}, listeners: {}, children: [],
    value: "", textContent: "", innerHTML: "", disabled: false, rows: [], options: [],
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, on) { if (on === undefined) { this._s.has(c) ? this._s.delete(c) : this._s.add(c); } else if (on) { this._s.add(c); } else { this._s.delete(c); } },
      contains(c) { return this._s.has(c); },
    },
    addEventListener(ev, fn) { this.listeners[ev] = fn; },
    removeEventListener() {},
    appendChild() {}, remove() {}, setAttribute() {}, getAttribute() { return null; },
    querySelector() { return makeEl("child"); },
    querySelectorAll() { return []; },
    closest() { return null; }, focus() {}, click() {},
    scrollIntoView() {},
  };
  return el;
}
const registry = {};
const document = {
  getElementById: (id) => registry[id] || (registry[id] = makeEl(id)),
  querySelector: (sel) => {
    const id = String(sel).replace(/^#/, "");
    return registry[id] || (registry[id] = makeEl(id));
  },
  querySelectorAll: () => [],
  createElement: () => makeEl("created"),
  body: { appendChild() {}, style: {} },
  addEventListener() {},
};
const window = {
  API_BASE: "/api", addEventListener() {}, scrollTo() {}, confirm: () => true,
  AudioContext: function () { return { state: "running", resume() {}, decodeAudioData() {} }; },
  URL: { createObjectURL: () => "blob:x", revokeObjectURL() {} },
};
const sandbox = {
  window, document, console,
  location: { href: "", pathname: "/questionnaire", search: "" },
  sessionStorage: { getItem: () => "faketoken", setItem() {}, removeItem() {} },
  fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
  URL: window.URL,
  confirm: () => true,
  prompt: () => null,
  setTimeout, clearTimeout,
};
vm.createContext(sandbox);

const JS = path.join(__dirname, "..", "..", "frontend", "js");
vm.runInContext(
  ["api.js", "common.js"].map((f) => fs.readFileSync(path.join(JS, f), "utf8")).join("\n;\n"),
  sandbox, { filename: "bundle.js" }
);
// 打桩：直接返回真实定义，避免网络
vm.runInContext(`
  window.__qqDef = ${JSON.stringify(byCode.q1)};
  api.questionnaireGet = async () => ({ questionnaire: window.__qqDef, submitted: false, my_answers: {} });
  api.questionnaireHistory = async () => ({ items: [] });
  api.questionnaires = async () => ({ questionnaires: [], submitted_count: 0, total: 6 });
`, sandbox);
vm.runInContext(fs.readFileSync(path.join(JS, "questionnaire.js"), "utf8"), sandbox,
  { filename: "questionnaire.js" });

const failures = [];
function check(cond, msg) {
  console.log(`  ${cond ? "✓" : "✗"} ${msg}`);
  if (!cond) failures.push(msg);
}

(async () => {
  console.log("== 1. 进入答题视图 ==");
  await vm.runInContext('startFill("q1")', sandbox);
  await new Promise((r) => setTimeout(r, 30));

  const title = registry["qq-form-title"].textContent;
  check(title === "卷1 前测问卷", `标题为「${title}」`);
  check(/约 13 分钟/.test(registry["qq-form-meta"].innerHTML), "显示预计用时");
  check(/匿名编码/.test(registry["qq-intro"].innerHTML), "卷首语渲染（含换行处理）");
  check(registry["qq-progress-text"].textContent.includes("第 1 / 5 页"),
    `进度文本：${registry["qq-progress-text"].textContent}`);

  console.log("== 2. 第 1 页（填空 + 单选）==");
  let html = registry["qq-page-body"].innerHTML;
  check(html.includes("基本信息"), "页标题渲染");
  check(html.includes("你的匿名编码是？"), "填空题干渲染");
  check((html.match(/type="text"/g) || []).length === 3, "3 道填空题（编码/班级/时长）");
  check(html.includes("qq-option") && html.includes("背词App"), "单选选项渲染");
  check(html.includes("qq-req"), "必答标记渲染");
  check(!html.includes("data-qq-input=\"undefined\""), "无 undefined 注入");

  console.log("== 3. 第 2 页（18 行分块矩阵）==");
  vm.runInContext(`
    qqPageIndex = 1;
    renderPage();
  `, sandbox);
  html = registry["qq-page-body"].innerHTML;
  check(html.includes("自主性") && html.includes("胜任感") && html.includes("归属感"), "3 个分块标题");
  check((html.match(/qq-block-row/g) || []).length === 3, "分块行数量 = 3");
  check((html.match(/<tr>/g) || []).length === 19, `表头 + 18 行数据（实际 ${(html.match(/<tr>/g) || []).length}）`);
  check((html.match(/type="radio"/g) || []).length === 18 * 5, "18 行 × 5 选项 = 90 个单选点");
  // 关键交叉校验：渲染出来的作答 key 必须与必答校验用的 key 完全一致
  // （每个选项都带 data-qq-key，按行去重后应为 18 个）
  const renderedKeys = [...new Set([...html.matchAll(/data-qq-key="([^"]+)"/g)].map((m) => m[1]))];
  const expectKeys = Array.from({ length: 18 }, (_, i) => `p2m1_r${i + 1}`);
  check(renderedKeys.length === 18, `渲染出 ${renderedKeys.length} 个行 key（应为 18）`);
  check(expectKeys.every((k) => renderedKeys.includes(k)),
    `行 key 为 r1..r18（首/末：${renderedKeys[0]} / ${renderedKeys[renderedKeys.length - 1]}）`);
  check(html.includes("完全不符合") && html.includes("完全符合"), "量表两端标签");
  check(!/qq_/.test(html), "未泄漏内部前缀");

  console.log("== 4. 必答校验（当前页未作答应拦住）==");
  vm.runInContext("qqAnswers = {};", sandbox);
  const missing = vm.runInContext("missingOnPage().length", sandbox);
  check(missing === 18, `第 2 页检出 ${missing} 个未答（应为 18）`);
  // 模拟用户按渲染出的 key 点选 → 必须能通过校验（若 key 编号错位，这里会失败）
  vm.runInContext(
    `qqAnswers = {}; ${JSON.stringify(renderedKeys)}.forEach(k => { qqAnswers[k] = "3"; });`,
    sandbox
  );
  const stillMissing = vm.runInContext("missingOnPage().length", sandbox);
  check(stillMissing === 0, `按页面实际渲染的 key 作答后通过校验（未答 ${stillMissing}）`);

  console.log("== 5. 最后一页（含 5 点变化量表）==");
  vm.runInContext("qqPageIndex = 4; renderPage();", sandbox);
  html = registry["qq-page-body"].innerHTML;
  check(html.includes("我对学习日语词汇的兴趣程度"), "基线题渲染");
  check(registry["qq-submit"].style.display === "inline-flex", "末页显示提交按钮");
  check(registry["qq-next"].style.display === "none", "末页隐藏下一页按钮");

  console.log("== 6. 卷 3 开放题（选填）==");
  vm.runInContext(`
    window.__qqDef = ${JSON.stringify(byCode.q3)};
    api.questionnaireGet = async () => ({ questionnaire: window.__qqDef, submitted: false, my_answers: {} });
  `, sandbox);
  await vm.runInContext('startFill("q3")', sandbox);
  await new Promise((r) => setTimeout(r, 30));
  vm.runInContext("qqPageIndex = 5; renderPage();", sandbox);
  html = registry["qq-page-body"].innerHTML;
  check(html.includes("<textarea"), "开放题渲染为多行文本");
  check(html.includes("（选填）"), "开放题标注选填");
  check(vm.runInContext("missingOnPage().length", sandbox) === 0, "开放题留空不阻塞提交");

  console.log("== 7. 已提交回顾视图 ==");
  vm.runInContext(`
    api.questionnaireGet = async () => ({
      questionnaire: window.__qqDef, submitted: true,
      submitted_at: "2026-09-19T12:00:00", duration_sec: 480,
      my_answers: { p1m1_r1: 4, p1m1_r2: 5, p6q1: "收获很多" },
    });
  `, sandbox);
  await vm.runInContext('showDone("q3")', sandbox);
  await new Promise((r) => setTimeout(r, 30));
  const doneHtml = registry["qq-done-answers"].innerHTML;
  check(/已提交/.test(registry["qq-done-title"].textContent), "标题显示已提交");
  check(doneHtml.includes("收获很多"), "作答内容回显");
  check(registry["qq-done-view"].style.display === "block", "切到回顾视图");
  check(registry["qq-form-view"].style.display === "none", "答题视图已隐藏");

  console.log();
  if (failures.length) {
    console.log(`FAIL（${failures.length} 项）`);
    failures.forEach((f) => console.log(" -", f));
    process.exit(1);
  }
  console.log("PASS：问卷页渲染逻辑全部通过");
  process.exit(0);
})();
