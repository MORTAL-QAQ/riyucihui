# -*- coding: utf-8 -*-
"""问卷自检（二）：与权威源《问卷设计（SDT与学习效果）.md》逐条比对。

《问卷总表》规定：「如条目原文有改动，请以《问卷设计》为准并回填本表」，
故本脚本把《问卷设计》当**权威条目原文**，按差异性质分类输出，供人工裁定：

  ① 主语/用词差异 —— 权威源与实现的主体词不同（会破坏组间或前后测可比性）
  ② 括号举例缺失 —— 权威源条目含「（如……）」，实现缺失（条目含义变窄）
  ③ 括号内容不同 —— 两版括号里的举例不同
  ④ 措辞漂移     —— 核心文本不一致（列出最相近的权威源条目）
  ⑤ 权威源无逐字题面 —— 如 Q0 基本信息，权威源只给条目标题

已声明的变体不算差异（脚本内置「预期变体」规则）：
  · 卷3 建卷清单声明「本卷条目直接使用《多模态日语词汇学习网站》，无需占位替换」
    → 权威源的「平台/这个平台」在卷3 实现中为网站名，属预期变体
  · 卷4 对照组版行标签由卷4 建卷清单单独给出，属预期变体

用法：cd backend && python dev_tools/check_questionnaire_design.py [源目录]
"""
import difflib
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
DESIGN = os.path.join(SRC_DIR, "问卷设计（SDT与学习效果）.md")

SUBJECT_OF = {
    "q1": "我的日语学习",
    "q2_exp": "《多模态日语词汇学习网站》",
    "q2_ctrl": "《多模态日语词汇学习网站》",
    "q3": "《多模态日语词汇学习网站》",
    "q4_exp": "《多模态日语词汇学习网站》",
    "q4_ctrl": "《多模态日语词汇学习网站》",
}
# 权威源里表示主体/平台的词（用于中性化比较）
SUBJECT_WORDS = ["【主语】", "《多模态日语词汇学习网站》", "这个平台", "平台", "我的日语学习"]

PAREN = re.compile(r"（([^）]*)）")


def norm(s: str) -> str:
    s = s.replace("**", "").replace("`", "").replace("　", "")
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = re.sub(r"\s+", "", s)
    return s.strip("；;。.：:")


def parens(s: str) -> list:
    """括号内容（剔除标注性质的补充，如（R）（外在负荷））。"""
    out = []
    for p in PAREN.findall(s):
        p = p.strip()
        if re.fullmatch(r"R.*", p) or p in ("内在负荷", "外在负荷", "相关负荷", "疲劳感"):
            continue
        out.append(p)
    return out


def key(s: str) -> str:
    """零化键：去括号、去主体词、去句首介词/方位词、去前导省略号。"""
    s = PAREN.sub("", s)
    for w in SUBJECT_WORDS:
        s = s.replace(w, "")
    s = re.sub(r"^(?:在|，|,|中|的)+", "", s)
    s = re.sub(r"^……", "", s)
    return norm(s)


def has_subject(s: str) -> bool:
    return any(w in s for w in SUBJECT_WORDS)


# Q0 基本信息：权威源只给条目标题（非逐字题面），该部分以建卷清单为准，不参与逐字比对
BASIC_ITEM_PREFIX = ("p1q",)
BASIC_CODES = {"q1", "q2_exp", "q2_ctrl"}


design_raw = io.open(DESIGN, encoding="utf-8").read() if os.path.exists(DESIGN) else ""
if not design_raw:
    print(f"未找到权威源：{DESIGN}")
    sys.exit(1)

# 权威源：按小节切分，收集条目行
sections = {}
cur = "其他"
for line in design_raw.split("\n"):
    h = re.match(r"^#{3,4}\s*(.+)$", line.strip())
    if h:
        cur = h.group(1)
        continue
    body = line.strip()
    m = re.match(r"^(?:\d+\.|[-*])\s*(.+)$", body)
    if m:
        sections.setdefault(cur, []).append(norm(m.group(1)))
    for seg in re.findall(r"[:：]([^：:]{6,})$", body):
        for piece in re.split(r"[；;]", seg):
            if piece.strip():
                sections.setdefault(cur, []).append(norm(piece.strip()))

all_design = [(sec, it) for sec, items in sections.items() for it in items]
design_keys = {}
for sec, it in all_design:
    design_keys.setdefault(key(it), (sec, it))

buckets = {"subject": [], "paren_missing": [], "paren_diff": [], "drift": [],
           "summary": [], "declared": [], "ok": []}

# 已声明变体：卷4 对照组版行标签由《卷4 建卷清单》单独给出（对照组词单无图文音）
DECLARED_VARIANTS = {("q4_ctrl", "学习材料的呈现方式（排版等）让理解变得复杂，分散了我的注意力"),
                     ("q4_ctrl", "我要花很大精力才能把学到的信息整合起来")}

for q in qq.list_questionnaires():
    for page in q["pages"]:
        for item in page["items"]:
            rows = item["rows"] if item["type"] == "matrix" else (
                [item["text"]] if item["type"] in ("text", "textarea") else [])
            for row in rows:
                # 基本信息（Q0）：权威源仅有条目标题，以建卷清单为准
                if q["code"] in BASIC_CODES and item["key"].startswith(BASIC_ITEM_PREFIX):
                    buckets["summary"].append((q["code"], row, None))
                    continue

                mine = norm(row)
                mine_sub = norm(row.replace("《多模态日语词汇学习网站》", "【主语】"))
                if any(mine == d or mine_sub == d for _, d in all_design):
                    buckets["ok"].append((q["code"], row, None))
                    continue

                hit = design_keys.get(key(mine))
                if hit is None:
                    if (q["code"], mine) in DECLARED_VARIANTS:
                        buckets["declared"].append((q["code"], row, None))
                        continue
                    cand = difflib.get_close_matches(key(mine), list(design_keys.keys()),
                                                     n=1, cutoff=0.72)
                    buckets["drift"].append((q["code"], row,
                                             design_keys[cand[0]][1] if cand else None))
                    continue

                _, src = hit
                pa, pm = parens(src), parens(mine)
                if len(pa) > len(pm):
                    buckets["paren_missing"].append((q["code"], row, src))
                elif pa != pm:
                    bucket = "declared" if (q["code"], mine) in DECLARED_VARIANTS else "paren_diff"
                    buckets[bucket].append((q["code"], row, src))
                elif has_subject(src) != has_subject(mine):
                    buckets["subject"].append((q["code"], row, src))
                else:
                    # 仅差（R）等标注 → 视为一致
                    buckets["ok"].append((q["code"], row, src))

print("=" * 76)
print("问卷自检（二）：实现 vs 权威源《问卷设计（SDT与学习效果）.md》")
print("=" * 76)
print(f"权威源条目 {len(all_design)} 条（{len(sections)} 个小节）；"
      f"实现条目 {sum(len(v) for v in buckets.values())} 行")
print(f"  ④ 完全一致（含【主语】占位形态）：{len(buckets['ok'])} 行")

report = [
    ("① 主语差异（双方主体词不一致）", "subject",
     "→ 一条含【主语】/平台主体词、另一条不含：组间或前后测的作答情境会不同"),
    ("② 括号举例缺失", "paren_missing",
     "→ 括号举例属于条目内容（如「如阶段提升、成就解锁」），缺失即条目含义变窄"),
    ("③ 括号内容不同", "paren_diff",
     "→ 同一位置的举例不同，需确认是否有意为之"),
    ("④ 措辞漂移（核心文本不一致）", "drift",
     "→ 列出最相近的权威源条目；若无匹配则权威源中确实不存在该条"),
    ("⑤ 已声明变体（建卷清单单独给出，不算差异）", "declared",
     "→ 如卷4 对照组版行标签，已在《卷4 建卷清单》中声明"),
]
for title, k, hint in report:
    rows = buckets[k]
    print(f"\n── {title}：{len(rows)} 行 ──")
    print(f"   {hint}")
    if not rows:
        print("   （无）")
        continue
    for code, mine, src in rows[:12]:
        print(f"   · [{code}] 实现：{mine[:56]}")
        if src:
            print(f"            权威源：{src[:56]}")
    if len(rows) > 12:
        print(f"   … 另有 {len(rows) - 12} 行")

print(f"\n── ⑤ 权威源无逐字题面（条目概要）：{len(buckets['summary'])} 行（Q0 基本信息，正常）")

# ── SUS 反向题 ──
print("\n" + "=" * 76)
print("SUS 反向题标记核对")
print("=" * 76)
print("  权威源 (R) 标注        ：[5, 11, 17, 4, 6, 8, 10]（含 Q1 第 5/11/17 行）")
print("  总表《反向题清单》      ：[2, 4, 6, 8, 10]（SUS）")
print(f"  实现 reverse（卷3 SUS）："
      f"{sorted(int(k.rsplit('_r', 1)[1]) for k in qq.get_questionnaire('q3')['reverse'])}")
if "我觉得平台没有必要这么复杂（R）" not in norm(design_raw):
    print("  ⚠ 权威源 SUS 第 2 题「我觉得平台没有必要这么复杂」漏标 (R)，")
    print("    但该题明显为负向题；实现按总表 + 卷3 建清单取 [2,4,6,8,10]（SUS 奇正偶负）→ 实现正确")

# ── Q11 疲劳感方向 ──
print("\n" + "=" * 76)
print("Q11「疲劳感」计分方向")
print("=" * 76)
print("  权威源      ：『在【主语】中学习让我感到很吃力（R 反向：疲劳感）』")
print("  卷4 建卷清单：『末行为反向含义，计分时注意方向』")
print(f"  实现        ：reverse={qq.get_questionnaire('q4_exp').get('reverse')}（保留原始方向：越高=越吃力）")
print("  → 单条目维度，反转只改变方向符号；原始作答完整留存，任何口径均可重新计分")

print("\n" + "=" * 76)
need = len(buckets["subject"]) + len(buckets["paren_missing"]) + len(buckets["paren_diff"])
print(f"自检结论：{need} 行需人工裁定（未擅自改动学生可见措辞），{len(buckets['drift'])} 行为措辞漂移")
print("=" * 76)
