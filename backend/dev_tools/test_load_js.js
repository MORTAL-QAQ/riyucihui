// 回归测试 v3：确认登录按钮（btn-auth-submit）click 事件已绑定
const fs = require("fs");
const path = require("path");
const vm = require("vm");

function makeEl(id, log) {
  return {
    id,
    style: {},
    dataset: {},
    listeners: {},
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    addEventListener(ev, fn) { this.listeners[ev] = fn; },
    removeEventListener() {},
    appendChild() {},
    remove() {},
    setAttribute() {},
    getAttribute() { return null; },
    querySelector() { return makeEl("child", log); },
    querySelectorAll() { return []; },
    closest() { return null; },
    focus() {},
    click() { if (this.listeners.click) this.listeners.click({ preventDefault() {} }); },
    value: "",
    textContent: "",
    innerHTML: "",
    disabled: false,
    options: [],
  };
}
const registry = {};
const log = [];
const document = {
  getElementById: (id) => registry[id] || (registry[id] = makeEl(id, log)),
  querySelector: (sel) => {
    const id = String(sel).replace(/^#/, "");
    return registry[id] || (registry[id] = makeEl(id, log));
  },
  querySelectorAll: () => [],
  createElement: () => makeEl("created", log),
  body: { appendChild() {}, style: {} },
  addEventListener() {},
};
const window = {
  API_BASE: "/api",
  addEventListener() {},
  AudioContext: function () { return { state: "running", resume() {}, decodeAudioData() {} }; },
  webkitAudioContext: undefined,
  URL: { createObjectURL: () => "blob:x", revokeObjectURL() {} },
};
const location = { href: "", pathname: "/", search: "" };
const sessionStorage = { getItem: () => null, setItem() {}, removeItem() {} };
const fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve({}), blob: () => Promise.resolve({ arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)) }), arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)) });
const URL = window.URL;
const confirm = () => true;
const prompt = () => null;

const sandbox = { window, document, location, sessionStorage, fetch, URL, confirm, prompt, console };
vm.createContext(sandbox);

const base = path.join(__dirname, "..", "frontend", "js");
const code = ["api.js", "common.js", "app.js"]
  .map((f) => fs.readFileSync(path.join(base, f), "utf8"))
  .join("\n;\n");

try {
  vm.runInContext(code, sandbox, { filename: "bundle.js" });
  const btn = registry["btn-auth-submit"];
  if (!btn) { console.log("❌ 未找到 btn-auth-submit"); process.exit(1); }
  if (btn.listeners.click) {
    console.log("✅ btn-auth-submit 已绑定 click 事件 → 登录按钮点击应有响应");
  } else {
    console.log("❌ btn-auth-submit 未绑定 click 事件");
    process.exit(1);
  }
  // 确认 switchTab / doAuth 存在
  const hasDoAuth = vm.runInContext("typeof doAuth", sandbox) === "function";
  console.log(`${hasDoAuth ? "✅" : "❌"} doAuth 函数可用`);
  process.exit(hasDoAuth ? 0 : 1);
} catch (e) {
  console.log(`❌ 加载抛错: ${e.message}`);
  console.log(e.stack.split("\n").slice(0, 6).join("\n"));
  process.exit(1);
}
