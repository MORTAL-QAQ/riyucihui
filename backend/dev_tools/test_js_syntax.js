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

// ── 3. 新页面登记检查（顶栏工具应覆盖所有业务页）──
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

console.log();
if (failed) {
  console.log(`FAIL（${failed} 项）`);
  process.exit(1);
}
console.log("PASS：前端静态检查全部通过");
