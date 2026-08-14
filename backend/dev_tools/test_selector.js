// 模拟测试：runStreamToPreview 的选择器修复（$ 是 querySelector，id 需 # 前缀）
const els = {
  "stream-preview": { style: {}, textContent: "" },
};
global.document = {
  querySelector: (s) => (s === "#stream-preview" ? els["stream-preview"] : null),
  getElementById: (id) => els[id] || null,
};
const $ = (sel) => document.querySelector(sel);

// 修复后写法
const el = $("#" + "stream-preview") || document.getElementById("stream-preview");
console.log("修复后命中:", el === els["stream-preview"]);

// 旧写法（bug）
const el2 = $("stream-preview");
console.log("旧写法命中:", el2 === null ? "null（确认 bug 根因）" : "命中");

// 缺失 id 时防护
const el3 = $("#" + "no-such-id");
console.log("缺失 id 防护:", el3 === null ? "null → 触发防护提示" : "异常");
