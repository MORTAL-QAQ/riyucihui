// 前端静态回归：
//   1) 全部 js 文件语法检查（防 SyntaxError 导致整页脚本失效）
//   2) 页面 JS 里 $("#id") 引用的 DOM id 是否存在于对应 HTML（防空引用 TypeError）
//      —— 曾因引用已删除的元素（#export-include-images）导致导出无响应
//
// 用法：node dev_tools/test_js_syntax.js
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const FE = path.join(__dirname, "..", "..", "frontend");
const JS_DIR = path.join(FE, "js");
const HTML_DIR = FE;

// JS 中出现但由 JS 动态生成 / 由其他页面共用的 id，不算缺失
const DYNAMIC_OK = new Set([
  "app", "main-app", "btn-logout", "sidebar", "mobile-nav", "toast", "toast-box",
]);

let failed = 0;

// ── 1. 语法检查 ──
const jsFiles = fs.readdirSync(JS_DIR).filter((f) => f.endsWith(".js")).sort();
console.log(`== 1. 语法检查（${jsFiles.length} 个文件）==`);
for (const f of jsFiles) {
  const src = fs.readFileSync(path.join(JS_DIR, f), "utf8");
  try {
    new vm.Script(src, { filename: f });
    console.log(`  ✓ ${f}`);
  } catch (e) {
    console.log(`  ✗ ${f}: ${e.message}`);
    failed += 1;
  }
}

// ── 2. DOM id 一致性 ──
console.log("\n== 2. DOM id 检查 ==");
const htmlIds = {};
for (const f of fs.readdirSync(HTML_DIR).filter((f) => f.endsWith(".html"))) {
  const text = fs.readFileSync(path.join(HTML_DIR, f), "utf8");
  const ids = new Set();
  for (const m of text.matchAll(/\bid="([A-Za-z0-9_-]+)"/g)) ids.add(m[1]);
  htmlIds[f] = ids;
}
const allIds = new Set();
Object.values(htmlIds).forEach((s) => s.forEach((i) => allIds.add(i)));

for (const f of jsFiles) {
  const htmlFile = f.replace(/\.js$/, ".html");
  const src = fs.readFileSync(path.join(JS_DIR, f), "utf8");
  const refs = new Set();
  for (const m of src.matchAll(/\$\("#([A-Za-z0-9_-]+)"\)/g)) refs.add(m[1]);
  for (const m of src.matchAll(/getElementById\("([A-Za-z0-9_-]+)"\)/g)) refs.add(m[1]);
  // JS 自己用 innerHTML 生成的元素（id="x"）也算存在
  const selfMade = new Set();
  for (const m of src.matchAll(/id="([A-Za-z0-9_-]+)"/g)) selfMade.add(m[1]);
  for (const m of src.matchAll(/id=\\"([A-Za-z0-9_-]+)\\"/g)) selfMade.add(m[1]);
  const missing = [...refs].filter(
    (id) => !allIds.has(id) && !selfMade.has(id) && !DYNAMIC_OK.has(id)
  );
  if (!missing.length) {
    console.log(`  ✓ ${f}（引用 ${refs.size} 个 id，全部存在）`);
  } else {
    console.log(`  ⚠ ${f} 引用了不存在的 id: ${missing.join(", ")}`);
  }
  // index.html 是 SPA，其 js（app.js）引用大量动态 id，只做提示不算失败
  if (missing.length && htmlFile !== "index.html" && f !== "app.js") {
    failed += 1;
  }
}

// ── 3. 页面与脚本登记检查（顶栏工具应覆盖所有业务页）──
console.log("\n== 3. 页面与脚本登记 ==");
const topbar = fs.readFileSync(
  path.join(__dirname, "unify_topbar.py"), "utf8"
);
const pages = [...topbar.matchAll(/\("(\/[a-z]+)", "/g)].map((m) => m[1]);
for (const p of pages.filter((p) => p !== "/")) {
  const file = path.join(HTML_DIR, `${p.slice(1)}.html`);
  const ok = fs.existsSync(file);
  console.log(`  ${ok ? "✓" : "✗"} ${p} → ${p.slice(1)}.html`);
  if (!ok) failed += 1;
}
console.log(`  导航项：${pages.join(" ")}`);

// ── 4. 导航一致性：桌面顶栏 / 移动抽屉 / 首页侧边栏 三方比对 ──
// 曾出现「桌面加了入口、手机抽屉没加」的问题（实验页、问卷页各漏过一次）
console.log("\n== 4. 导航一致性（桌面 / 移动抽屉 / 首页侧边栏）==");
const commonJs = fs.readFileSync(path.join(JS_DIR, "common.js"), "utf8");
const indexHtml = fs.readFileSync(path.join(HTML_DIR, "index.html"), "utf8");

const desktopNav = new Set(pages); // unify_topbar.py 的 NAV_ITEMS
const drawerBlock = commonJs.match(/MOBILE_NAV_ITEMS\s*=\s*\[([\s\S]*?)\];/);
const drawerNav = new Set(
  drawerBlock
    ? [...drawerBlock[1].matchAll(/"(\/[a-z]*)"/g)].map((m) => m[1])
    : []
);
const sidebarNav = new Set(
  [...indexHtml.matchAll(/data-tab="([a-z]+)"/g)].map((m) => "/" + m[1])
);
sidebarNav.add("/"); // 首页自身

const report = (label, set) =>
  console.log(`  ${label}：${[...set].sort().join(" ") || "（空）"}`);

report("桌面顶栏", desktopNav);
report("移动抽屉", drawerNav);
report("首页侧边栏", sidebarNav);

const inDrawerNotDesktop = [...drawerNav].filter((p) => !desktopNav.has(p));
const inDesktopNotDrawer = [...desktopNav].filter((p) => !drawerNav.has(p));
const inSidebarNotDesktop = [...sidebarNav].filter((p) => !desktopNav.has(p));
const inDesktopNotSidebar = [...desktopNav].filter((p) => !sidebarNav.has(p));

if (inDrawerNotDesktop.length) {
  console.log(`  ⚠ 移动抽屉多出：${inDrawerNotDesktop.join(" ")}`);
}
if (inSidebarNotDesktop.length) {
  console.log(`  ⚠ 首页侧边栏多出：${inSidebarNotDesktop.join(" ")}`);
}
if (inDesktopNotDrawer.length) {
  console.log(`  ✗ 移动抽屉缺少入口（手机端会看不到）：${inDesktopNotDrawer.join(" ")}`);
  failed += 1;
}
if (inDesktopNotSidebar.length) {
  console.log(`  ✗ 首页侧边栏缺少入口：${inDesktopNotSidebar.join(" ")}`);
  failed += 1;
}
if (!inDesktopNotDrawer.length && !inDesktopNotSidebar.length) {
  console.log("  ✓ 三处导航一致（桌面 / 移动抽屉 / 首页侧边栏）");
}

// ── 5. SPA 路由覆盖：首页侧边栏每个 tab 都要有 switchTab 分支 ──
console.log("\n== 5. 首页侧边栏 tab 的 switchTab 覆盖 ==");
const missingTab = [];
for (const tab of [...indexHtml.matchAll(/data-tab="([a-z]+)"/g)].map((m) => m[1])) {
  if (tab === "more") continue;
  if (!new RegExp(`tab === "${tab}"`).test(commonJs) &&
      !new RegExp(`tab === "${tab}"`).test(fs.readFileSync(path.join(JS_DIR, "app.js"), "utf8"))) {
    missingTab.push(tab);
  }
}
if (missingTab.length) {
  console.log(`  ✗ 以下 tab 无 switchTab 分支（点击无反应）：${missingTab.join(" ")}`);
  failed += 1;
} else {
  console.log("  ✓ 侧边栏全部 tab 均有 switchTab 分支");
}

console.log();
if (failed) {
  console.log(`FAIL（${failed} 项）`);
  process.exit(1);
}
console.log("PASS：前端静态检查全部通过");
