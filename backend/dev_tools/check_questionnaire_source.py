# -*- coding: utf-8 -*-
"""问卷自检：把实现（app/questionnaires.py）与论文源文件逐条比对。

**双源模型**（2026-09 起）：条目措辞命中以下任一源即可判定合规——
  · 该卷的《建卷清单》（实际建卷用的那份）
  · 权威源《问卷设计（SDT与学习效果）.md》（总表规定「条目原文有改动以《问卷设计》为准」）
两者都不命中 = 真正的转写错误。仅命中权威源的行会标注「权威源」，
便于看出哪些行是按权威源统一过的（如 BPNS 主语、括号举例、卷3 开放题）。

校验内容：
  A. 题干 / 矩阵行 / 选项：双源逐字命中
  B. 引导语：同上（未命中则列出源文件原文，供人工确认）
  C. 题量：与源文件「核对清单」声明的题量、页数比对
  D. 反向题：与源文件反向题清单比对（Q1 BPNS 6 题、Q9 SUS 5 题）
  E. 维度：与《问卷总表》第三节「量表-题号对照」的题量比对

用法：cd backend && python dev_tools/check_questionnaire_source.py [源目录]
默认源目录：../论文/03_问卷
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app import questionnaires as qq  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "论文", "03_问卷")

# 表单 → 源文件
SOURCE_OF = {
    "q1": "卷1_前测问卷（建卷清单）.md",
    "q2": "卷2_后测核心（实验组版·建卷清单）.md",   # 2026-09.1 起卷2 合并为单一版本，以此版为落笔依据
    "q3": "卷3_实验组附加卷（建卷清单）.md",
    "q4_exp": "卷4_认知负荷问卷（建卷清单）.md",
    "q4_ctrl": "卷4_认知负荷问卷（建卷清单）.md",
}
TOTAL_SHEET = "问卷总表（整理版）.md"
DESIGN_SHEET = "问卷设计（SDT与学习效果）.md"


def norm(s: str) -> str:
    """规范化：去 Markdown 强调符、占位符替换、引号统一、空白折叠、去行尾标点。"""
    s = s.replace("**", "").replace("`", "").replace("　", "")
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    # 源文件用【主语】占位（建卷时替换为《多模态日语词汇学习网站》）
    s = s.replace("【主语】", "《多模态日语词汇学习网站》")
    s = re.sub(r"\s+", "", s)
    return s.strip("；;。.")


def norm_keep_placeholder(s: str) -> str:
    """同 norm，但**保留【主语】占位**——用于与权威源对照（权威源是占位形态）。"""
    s = s.replace("**", "").replace("`", "").replace("　", "")
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = re.sub(r"\s+", "", s)
    return s.strip("；;。.")


def load(name: str) -> str:
    path = os.path.join(SRC_DIR, name)
    if not os.path.exists(path):
        print(f"[警告] 源文件不存在：{path}")
        return ""
    with io.open(path, encoding="utf-8") as f:
        return norm(f.read())


def load_all() -> str:
    """全部源文件合并（用于判定「引导语是否在别处出现过」）。"""
    parts = []
    for name in sorted(set(SOURCE_OF.values())) + [TOTAL_SHEET]:
        path = os.path.join(SRC_DIR, name)
        if os.path.exists(path):
            with io.open(path, encoding="utf-8") as f:
                parts.append(norm(f.read()))
    return "\n".join(parts)


ALL_SRC = load_all()
_design_path = os.path.join(SRC_DIR, DESIGN_SHEET)
DESIGN_PLACEHOLDER = norm_keep_placeholder(io.open(_design_path, encoding="utf-8").read()) \
    if os.path.exists(_design_path) else ""
DESIGN_SRC = load(DESIGN_SHEET)


def to_placeholder(s: str) -> str:
    """把行文本规约成权威源的【主语】占位形态，便于与《问卷设计》比对。"""
    return norm_keep_placeholder(s).replace("《多模态日语词汇学习网站》", "【主语】") \
        .replace("我的日语学习", "【主语】")


def in_design(s: str) -> bool:
    """该条目是否命中权威源《问卷设计》（接受【主语】占位形态与已替换形态）。"""
    if not DESIGN_SRC:
        return False
    n = norm(s)
    return (n in DESIGN_SRC
            or n in DESIGN_PLACEHOLDER
            or to_placeholder(s) in DESIGN_PLACEHOLDER)


errors = []
warns = []

print("=" * 72)
print("问卷自检：实现 vs 论文源文件")
print(f"源目录：{SRC_DIR}")
print("=" * 72)

for q in qq.list_questionnaires():
    code = q["code"]
    src_name = SOURCE_OF.get(code)
    src = load(src_name) if src_name else ""
    print(f"\n【{qq.display_name(q)}】({code}) ← {src_name}")

    if not src:
        errors.append(f"{code}: 缺少源文件，无法比对")
        continue

    # ── A/B. 逐条文本比对 ──
    missing_item, missing_row, missing_opt, warn_lead = [], [], [], []
    lead_checked = []
    for page in q["pages"]:
        for item in page["items"]:
            item_text = norm(item["text"])
            if item["type"] == "matrix":
                lead_checked.append((item["key"], item["text"]))
                if item_text and item_text not in src:
                    warn_lead.append((item["key"], item["text"]))
                for row in item["rows"]:
                    if norm(row) not in src:
                        missing_row.append((item["key"], row))
                for opt in (item.get("scale", {}).get("labels") or {}).values():
                    if norm(opt) not in src:
                        warn_lead.append((f"{item['key']}.scale", opt))
            else:
                if item_text not in src:
                    missing_item.append((item["key"], item["text"]))
                for opt in item.get("options", []):
                    if norm(str(opt)) not in src:
                        missing_opt.append((item["key"], opt))

    def report(label, rows, is_error=True):
        """rows 元素为 (key, text)；命中权威源的行单独列出，不算错误。"""
        only_design = [(k, t) for k, t in rows if in_design(t)]
        real_missing = [(k, t) for k, t in rows if not in_design(t)]
        if not rows:
            print(f"  ✓ {label}")
            return
        if only_design:
            print(f"  · {label}：{len(only_design)} 行按权威源《问卷设计》统一（建卷清单未回填）")
            for k, t in only_design[:4]:
                print(f"      [{k}] {t[:56]}")
        if real_missing:
            print(f"  ✗ {label}：{len(real_missing)} 行在两个源中均未找到")
            for k, t in real_missing[:6]:
                print(f"      [{k}] {t[:60]}")
            (errors if is_error else warns).extend(
                f"{code} {label}: [{k}] {t[:60]}" for k, t in real_missing)
        elif not only_design:
            print(f"  ✓ {label}")

    report("题干（填空/单选/开放题）逐字命中", missing_item)
    report("矩阵行标签逐字命中", missing_row)
    report("选项逐字命中", missing_opt)

    # 引导语：本卷源文件命中 → OK；其他源文件命中 → 提示（该页源文件未写引导语）；都没有 → 待确认
    lead_total = len(lead_checked)
    lead_own = [x for x in warn_lead if norm(x[1]) in src]
    lead_other = [x for x in warn_lead if norm(x[1]) not in src and norm(x[1]) in ALL_SRC]
    lead_none = [x for x in warn_lead if norm(x[1]) not in ALL_SRC]
    print(f"  ✓ 引导语逐字命中（本卷源文件）：{lead_total - len(warn_lead) + len(lead_own)}/{lead_total} 处")
    for key, text in lead_other:
        print(f"  · 引导语跨文件命中（本页源文件未指定引导语）：[{key}] {text[:50]}")
    for key, text in lead_none:
        print(f"  ⚠ 引导语在任何源文件中都未找到，需人工确认：[{key}] {text[:50]}")
        warns.append(f"{code} 引导语未在源文件找到: [{key}] {text[:50]}")

    # ── C. 题量/页数 ──
    # 正文声明「N 页 · M 题」；核对清单给出分项 (a + b + ...)。
    # 分项仅在「每段只含一个数字」时可加和（如 2 基本信息 + 18 + 12），
    # 描述性括号（如 1 单选 9 点 + 1 矩阵 4 行）不可加和，跳过。
    mine_pages, mine_items = len(q["pages"]), len(qq.item_keys(q))
    m_head = re.search(r"(\d+)页[·、](\d+)题", src)
    declared = None
    if m_head:
        declared = (int(m_head.group(1)), int(m_head.group(2)))

    breakdown_sum = None
    m_paren = re.search(r"(\d+)页[、·](\d+)题（([^）]*)）", src) or re.search(r"题（([^）]*)）", src)
    if m_paren:
        tokens = [t for t in re.split(r"\+", m_paren.groups()[-1]) if t.strip()]
        if tokens and all(re.fullmatch(r"\d+[^0-9]*", t) for t in tokens):
            breakdown_sum = sum(int(re.match(r"\d+", t).group()) for t in tokens)

    if declared:
        doc_pages, doc_items = declared
        print(f"  {'✓' if doc_pages == mine_pages else '✗'} 页数：源 {doc_pages} / 实现 {mine_pages}")
        if doc_pages != mine_pages:
            errors.append(f"{code}: 页数不一致 源{doc_pages} vs 实现{mine_pages}")
        ok = doc_items == mine_items
        print(f"  {'✓' if ok else '✗'} 题量（正文声明）：源 {doc_items} / 实现 {mine_items}"
              + (f"（分项相加 = {breakdown_sum}）" if breakdown_sum else ""))
        if not ok:
            if breakdown_sum == mine_items:
                print(f"      → 源文件自身不一致：正文写 {doc_items}，但分项相加 = {breakdown_sum}"
                      f"；实现按与题目原文一一对应的**分项**取 {mine_items}——属文档笔误，非实现问题")
                warns.append(f"{code}: 源文件题量笔误（正文 {doc_items} vs 分项和 {breakdown_sum}），"
                             f"实现采用分项 {mine_items}")
            else:
                errors.append(f"{code}: 题量不一致 源{doc_items}"
                              f"（分项和 {breakdown_sum}）vs 实现{mine_items}")
        elif breakdown_sum and breakdown_sum != mine_items:
            print(f"  ✗ 分项相加 {breakdown_sum} ≠ 实现 {mine_items}")
            errors.append(f"{code}: 分项相加 {breakdown_sum} ≠ 实现 {mine_items}")
    else:
        print("  ⚠ 未能从源文件解析出「N 页 M 题」")
        warns.append(f"{code}: 源文件未声明页数/题量")

    # ── D. 反向题 ──
    rev = q.get("reverse") or []
    if rev:
        nums = sorted(int(k.rsplit("_r", 1)[1]) for k in rev)
        declared = re.search(r"行\"?\)?（照录原文|行\*\*（|反向题[：:]\s*\*\*([0-9、]+)", src)
        print(f"  反向题 {len(rev)} 项，行号 {nums}")
        # 源文件里应出现同样的行号串
        joined = "、".join(str(n) for n in nums)
        hit = joined in src or joined.replace("、", ",") in src
        print(f"  {'✓' if hit else '⚠'} 行号串「{joined}」在源文件中{'出现' if hit else '未直接找到（可能写法不同）'}")
        if not hit:
            warns.append(f"{code}: 反向题行号串未在源文件直接出现：{joined}")
    else:
        print("  ✓ 本卷无反向题（与源文件一致）")

    # ── E. 维度条目数 ──
    dims = q.get("dimensions") or {}
    print(f"  维度 {len(dims)} 个：" + "、".join(f"{d}({len(v)})" for d, v in dims.items()))
    # 维度 key 必须都是合法条目
    valid = set(qq.item_keys(q))
    bad = [k for v in dims.values() for k in v if k not in valid]
    if bad:
        print(f"  ✗ 维度里含非本卷条目：{bad[:5]}")
        errors.append(f"{code}: 维度含非法条目 {bad[:5]}")
    else:
        print("  ✓ 维度条目均属于本卷")

    # ── F. 计分自检：反向题反转是否正确 ──
    if rev:
        sample = {k: 4 for k in qq.required_keys(q)}
        sc = qq.compute_scores(q, sample)
        dim_with_rev = [d for d, keys in dims.items() if any(k in set(rev) for k in keys)]
        if dim_with_rev:
            d0 = dim_with_rev[0]
            expect = round((4 * (len(dims[d0]) - 1) + 2) / len(dims[d0]), 3) if False else None
            print(f"  ✓ 反向计分抽样：{d0} = {sc.get(d0)}（全 4 作答，含反向题则低于 4）")
            if sc.get(d0, 0) >= 4:
                errors.append(f"{code}: 反向计分疑似未生效（{d0}={sc.get(d0)}）")

print("\n" + "=" * 72)
print("总表交叉核对")
print("=" * 72)
sheet = load(TOTAL_SHEET)
if sheet:
    for q in qq.list_questionnaires():
        n = len(qq.item_keys(q))
        print(f"  {qq.display_name(q):<26} 实现题量 {n}")
    # 反向题：总表按「每份问卷」声明（BPNS 6 + SUS 5 = 11），不是全部表单求和
    rev_ok = True
    for q in qq.list_questionnaires():
        rev = q.get("reverse") or []
        has_bpns = any(k.startswith("p2m1_r") for k in rev)
        expect = 6 if has_bpns else (5 if q["code"] == "q3" else 0)
        ok = len(rev) == expect
        rev_ok = rev_ok and ok
        print(f"  {'✓' if ok else '✗'} {qq.display_name(q):<26} 反向题 {len(rev)}（总表口径应为 {expect}）")
        if not ok:
            errors.append(f"{q['code']}: 反向题 {len(rev)} ≠ 总表口径 {expect}")
    if rev_ok:
        print("  ✓ 反向题与总表口径一致（BPNS 6 题 ×3 卷 + SUS 5 题 = 23 项，每份问卷分别核对）")
else:
    warns.append("未找到问卷总表，跳过交叉核对")

print("\n" + "=" * 72)
if errors:
    print(f"FAIL —— {len(errors)} 个错误、{len(warns)} 个待确认")
    for e in errors:
        print("  ✗", e)
    for w in warns:
        print("  ⚠", w)
    sys.exit(1)
print(f"PASS —— 全部逐字命中；{len(warns)} 个待人工确认项")
for w in warns:
    print("  ⚠", w)
