/**
 * 语法独立子页逻辑（阶段二多页架构）
 * 依赖：api.js + common.js（$ / esc / escHtml / showToast / handleApiError
 *       / runStreamToPreview / initPage / currentUsername / isAdmin）
 */

// ── 状态 ──
let grammarSubTab = "analyze";
let currentCompareData = null;  // { topic, summary, rows }

// ── DOM 引用 ──
const grammarAnalyzeInput = $("#grammar-analyze-input");
const grammarCorrectInput = $("#grammar-correct-input");
const grammarCompareInput = $("#grammar-compare-input");
const btnGrammarAnalyze = $("#btn-grammar-analyze");
const btnGrammarCorrect = $("#btn-grammar-correct");
const btnGrammarCompare = $("#btn-grammar-compare");

// ── 子标签切换 ──
function switchGrammarTab(tab) {
  grammarSubTab = tab;
  ["analyze", "correct", "compare"].forEach((t) => {
    $(`#grammar-subtab-${t}`).classList.toggle("active", t === tab);
    $(`#grammar-panel-${t}`).style.display = t === tab ? "block" : "none";
  });
}

$("#grammar-subtab-analyze").addEventListener("click", () => switchGrammarTab("analyze"));
$("#grammar-subtab-correct").addEventListener("click", () => switchGrammarTab("correct"));
$("#grammar-subtab-compare").addEventListener("click", () => switchGrammarTab("compare"));

// ── 语法分析 ──
btnGrammarAnalyze.addEventListener("click", async () => {
  const sentence = grammarAnalyzeInput.value.trim();
  if (!sentence) return;

  btnGrammarAnalyze.disabled = true;
  const loadingEl = $("#grammar-analyze-loading");
  loadingEl.style.display = "block";
  $("#grammar-analyze-result").style.display = "none";
  $("#grammar-analyze-error").style.display = "none";

  try {
    await runStreamToPreview("/grammar/analyze", { sentence, stream: true }, "grammar-analyze-stream-preview", {
      onDone: (result) => {
        $("#grammar-points-list").innerHTML = result.points
          .map(
            (p) => `
          <div class="grammar-point-card">
        <div class="gp-header">
          <span class="gp-name">${escHtml(p.grammar)}</span>
          <span class="gp-level">${escHtml(p.level)}</span>
          <span class="gp-meaning">${escHtml(p.meaning)}</span>
        </div>
        <div class="gp-explain">${escHtml(p.explanation)}</div>
        ${p.example ? `<div class="gp-example">📝 ${escHtml(p.example)}<br>💬 ${escHtml(p.example_cn)}</div>` : ""}
      </div>`,
          )
          .join("");
        loadingEl.style.display = "none";
        $("#grammar-analyze-result").style.display = "block";
      },
      onError: (msg) => { throw new Error(msg); },
    });
  } catch (err) {
    loadingEl.style.display = "none";
    $("#grammar-analyze-error").style.display = "block";
    $("#grammar-analyze-error").textContent = `分析失败：${err.message}`;
    showToast("语法分析失败，请重试", "error");
  } finally {
    btnGrammarAnalyze.disabled = false;
  }
});

grammarAnalyzeInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") btnGrammarAnalyze.click();
});

// ── 语法纠错 ──
btnGrammarCorrect.addEventListener("click", async () => {
  const sentence = grammarCorrectInput.value.trim();
  if (!sentence) return;

  btnGrammarCorrect.disabled = true;
  const loadingEl = $("#grammar-correct-loading");
  loadingEl.style.display = "block";
  $("#grammar-correct-result").style.display = "none";
  $("#grammar-correct-error").style.display = "none";

  try {
    await runStreamToPreview("/grammar/correct", { sentence, stream: true }, "grammar-correct-stream-preview", {
      onDone: (result) => {
        const data = result;
        let errorsHtml = "";
        if (data.errors.length === 0) {
          errorsHtml = '<div class="no-errors-badge">✓ 句子完全正确，没有语法错误</div>';
        } else {
          errorsHtml =
            '<h3 style="margin-bottom:8px">发现 ' +
            data.errors.length +
            " 处问题：</h3>" +
            data.errors
              .map(
                (e) => `
          <div class="grammar-error-item">
            <span class="ge-type">${escHtml(e.type)}</span>
            <strong>${escHtml(e.fragment)}</strong> — ${escHtml(e.description)}
            <br><em>→ ${escHtml(e.suggestion)}</em>
          </div>`,
              )
              .join("");
        }

        $("#grammar-correct-card").innerHTML = `
          <div class="gc-original">
            <strong>原文：</strong>${escHtml(data.original)}
          </div>
          <div class="gc-corrected">
            <strong>改正：</strong><span class="gc-text">${escHtml(data.corrected)}</span>
          </div>
          ${errorsHtml}
        `;
        loadingEl.style.display = "none";
        $("#grammar-correct-result").style.display = "block";
      },
      onError: (msg) => { throw new Error(msg); },
    });
  } catch (err) {
    loadingEl.style.display = "none";
    $("#grammar-correct-error").style.display = "block";
    $("#grammar-correct-error").textContent = `纠错失败：${err.message}`;
    showToast("语法纠错失败，请重试", "error");
  } finally {
    btnGrammarCorrect.disabled = false;
  }
});

grammarCorrectInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") btnGrammarCorrect.click();
});

// ── 语法辨析 ──
btnGrammarCompare.addEventListener("click", async () => {
  const topic = grammarCompareInput.value.trim();
  if (!topic) return;

  btnGrammarCompare.disabled = true;
  const loadingEl = $("#grammar-compare-loading");
  loadingEl.style.display = "block";
  $("#grammar-compare-result").style.display = "none";
  $("#grammar-compare-error").style.display = "none";

  try {
    await runStreamToPreview("/grammar/compare", { topic, stream: true }, "grammar-compare-stream-preview", {
      onDone: (result) => {
        const data = result;
        currentCompareData = { topic: data.topic, summary: data.summary, rows: data.rows };
        const saveBtn = $("#btn-grammar-save-compare");
        saveBtn.disabled = false;
        saveBtn.textContent = "保存结果";
        $("#grammar-compare-topic-label").textContent = `「${data.topic}」辨析`;
        $("#grammar-compare-summary").innerHTML = `<strong>📋 总结：</strong>${escHtml(data.summary)}`;
        $("#grammar-compare-table").innerHTML = `
          <thead>
            <tr>
              <th>语法</th>
              <th>接续</th>
              <th>含义</th>
              <th>例句</th>
            </tr>
          </thead>
          <tbody>
            ${data.rows
              .map(
                (r) => `
          <tr>
            <td><strong>${escHtml(r.grammar)}</strong></td>
            <td class="gct-pattern">${escHtml(r.pattern)}</td>
            <td>${escHtml(r.meaning)}</td>
            <td>${escHtml(r.example)}<br><small>${escHtml(r.example_cn)}</small></td>
          </tr>`,
              )
              .join("")}
          </tbody>
        `;
        loadingEl.style.display = "none";
        $("#grammar-compare-result").style.display = "block";
      },
      onError: (msg) => { throw new Error(msg); },
    });
  } catch (err) {
    loadingEl.style.display = "none";
    $("#grammar-compare-error").style.display = "block";
    $("#grammar-compare-error").textContent = `辨析失败：${err.message}`;
    showToast("语法辨析失败，请重试", "error");
  } finally {
    btnGrammarCompare.disabled = false;
  }
});

grammarCompareInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") btnGrammarCompare.click();
});

// ── 保存语法辨析 ──
$("#btn-grammar-save-compare").addEventListener("click", async () => {
  if (!currentCompareData) return;
  const btn = $("#btn-grammar-save-compare");
  btn.disabled = true;
  btn.textContent = "保存中...";
  try {
    await api.saveGrammarCompare(
      currentCompareData.topic,
      JSON.stringify({ summary: currentCompareData.summary, rows: currentCompareData.rows }),
    );
    btn.textContent = "已保存";
    showToast("保存完毕，可在「我的保存」查看");
  } catch (err) {
    btn.disabled = false;
    btn.textContent = "保存结果";
    showToast(`保存失败：${err.message}`, "error");
  }
});

// ── 入口：认证（无初始加载，子标签切换即可用） ──
initPage();
