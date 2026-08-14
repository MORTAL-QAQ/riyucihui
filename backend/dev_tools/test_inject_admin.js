// 专项测试：injectAdminNav 按 isAdmin 动态注入/不注入顶栏管理按钮
const fs = require("fs");
const path = require("path");
const vm = require("vm");

function makeEl(id) {
  return {
    id,
    style: { cssText: "" },
    dataset: {},
    listeners: {},
    children: [],
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    addEventListener(ev, fn) { this.listeners[ev] = fn; },
    removeEventListener() {},
    appendChild(c) { this.children.push(c); return c; },
    remove() {},
    setAttribute() {},
    getAttribute() { return null; },
    querySelector(sel) {
      if (sel === 'a[href="/admin"]') {
        return this.children.find((c) => c.href === "/admin") || null;
      }
      return null;
    },
    querySelectorAll() { return []; },
    closest() { return null; },
    focus() {},
    value: "",
    textContent: "",
    innerHTML: "",
    disabled: false,
  };
}
const registry = {};
const navWrap = makeEl("navwrap"); // 模拟顶栏导航容器
registry["navwrap"] = navWrap;
const document = {
  getElementById: (id) => registry[id] || (registry[id] = makeEl(id)),
  querySelector: (sel) => {
    if (sel === '.subpage-header div[style*="flex-wrap:wrap"]') return navWrap;
    return registry[sel.replace(/^#/, "")] || null;
  },
  querySelectorAll: () => [],
  createElement: () => makeEl("created"),
  body: { appendChild() {}, style: {} },
  addEventListener() {},
};
const window = { API_BASE: "/api", addEventListener() {} };
const location = { href: "", pathname: "/study" };
const sessionStorage = { getItem: () => null, setItem() {}, removeItem() {} };
const fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
const sandbox = { window, document, location, sessionStorage, fetch, URL: {}, confirm: () => true, prompt: () => null, console, navWrap };
vm.createContext(sandbox);

const base = path.join(__dirname, "..", "..", "frontend", "js");
const code = fs.readFileSync(path.join(base, "common.js"), "utf8");
vm.runInContext(code, sandbox);

// 1) 普通用户：isAdmin=false → 不注入
vm.runInContext("isAdmin = false; injectAdminNav();", sandbox);
let injected = vm.runInContext('navWrap.querySelector(\'a[href="/admin"]\')', sandbox);
console.log(`普通用户: 注入=${injected !== null} ${injected === null ? "✅" : "❌"}`);

// 2) 管理员：isAdmin=true → 注入
vm.runInContext("isAdmin = true; injectAdminNav();", sandbox);
injected = vm.runInContext('navWrap.querySelector(\'a[href="/admin"]\')', sandbox);
console.log(`管理员: 注入=${injected !== null} href=${injected && injected.href} 文本=${injected && injected.textContent} ${injected ? "✅" : "❌"}`);

// 3) 防重复：再调一次不重复注入
vm.runInContext("injectAdminNav();", sandbox);
const count = vm.runInContext('navWrap.children.filter(c => c.href === "/admin").length', sandbox);
console.log(`防重复: 管理按钮数=${count} ${count === 1 ? "✅" : "❌"}`);

// 4) admin 页高亮
vm.runInContext("location.pathname = '/admin'; navWrap.children = []; isAdmin = true; injectAdminNav();", sandbox);
const onAdmin = vm.runInContext('navWrap.children.find(c => c.href === "/admin")', sandbox);
console.log(`admin页高亮: ${(onAdmin && onAdmin.style.cssText.includes("rgba(99,102,241,0.35)")) ? "✅" : "❌"}`);

process.exit(0);
