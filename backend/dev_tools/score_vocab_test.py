#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""词汇测试卷「4 子分计分 + 统计」脚本（纯 Python 标准库实现）。

================================================================================
一、这个脚本做什么
================================================================================
把「词汇测试卷」的原始作答（宽表 CSV）按【呈现模式 × 知识维度】交叉拆成 4 个子分，
再算完整套被试内假设检验（H1 / H2 / 保持率 / H3 / H6），输出 `scores.csv` 与 `stats.txt`。

================================================================================
二、研究口径（严格按《论文/02_实验设计/论文设计与实验方案.md》与《测试卷出题模板.md》）
================================================================================
1. 被试内设计：每个主题词单 20 词中，10 词以「图文音」呈现
   （假名/汉字 + 中文释义 + 例句 + AI 配图 + TTS 发音），10 词以「纯文字」呈现
   （同释义同例句，无配图无发音）。**呈现模式绑在「词」上**，同一词对所有被试一致。
2. 词汇测试：40 题覆盖主题1、主题2 各 20 个测试词（一词一题），满分 50 分。
   时点：即时后测（A 卷）/ 延迟后测（B 卷）。
3. 知识维度与题型分值（固定）：
     - 接受性 共 30 分：认读 10 题 + 选义 10 题 + 听辨 10 题，每小题 1 分
     - 产出性 共 20 分：写假名 5 题 + 语境填空 5 题，每小题 2 分
4. 4 个交叉子分：题目按其对应词的模态分成两组（各 20 题 / 25 分），
   每组再分接受性 / 产出性。因为两类词各 20 题，于是：
     - 图文音组：接受性 15 题 = 15 分；产出性 5 题 = 10 分  → 模态组满分 25
     - 纯文字组：接受性 15 题 = 15 分；产出性 5 题 = 10 分  → 模态组满分 25
   故每名被试每个时点得到 4 个子分：
     图文音_接受性(15) / 图文音_产出性(10) / 纯文字_接受性(15) / 纯文字_产出性(10)

   ⚠ 注意：写假名 5 题 + 填空 5 题共 10 道产出性题要分给两个模态组（每组 5 道），
     所以「写假名/填空」在两组间只能是 3+2 或 2+3 之类的分配，**不可能两组各 2.5 道**。
     本脚本因此只强制校验「每组接受性 15 分 / 产出性 10 分」与「全卷 50 分」，
     不强制每种题型在两组间的具体道数（题型点值合计 10/10/10/10/10 只做告警）。

5. 假设检验：
     - H1（即时）/ H2（延迟）：图文音词 vs 纯文字词 → 配对样本 t 检验
       （总分、接受性、产出性分列），效应量报告 Cohen's d_z = 差值均数 / 差值标准差
     - 保持率：延迟 − 即时，两类词分别算，再做配对比较（另附「延迟/即时」比值作描述）
     - H3：2×2 重复测量 ANOVA（呈现模式 2 水平 × 知识维度 2 水平，均为被试内），
       报告 F、df、p、偏 η²，重点看交互效应；并给「两维度模态增益差值」的
       Bootstrap 95% 置信区间（被试重抽样，默认 5000 次，随机种子可设）
     - H6（第二轮）：2×2 混合设计 ANOVA（呈现模式＝被试内 × 水平＝被试间「专业生/二外生」），
       报告交互效应
     - 辅助：描述统计（均值 / 标准差 / 样本量）

================================================================================
三、输入文件（UTF-8，带 BOM 可接受）
================================================================================
1) bindings.csv  词-模态绑定表
     列： 主题,序号,单词,呈现模式          （呈现模式 ∈ {图文音, 纯文字}）
2) items.csv     题目表
     列： 题号,单词,题型,维度,分值
     题型 ∈ {认读,选义,听辨,写假名,填空}；维度 ∈ {接受性,产出性}
3) responses.csv 作答表（宽表）
     列： 匿名编码,轮次,时点,[水平,]题号1,题号2,...
     例： 0521LX,第一轮,即时,专业生,A01,A02,...
     - 题号列名必须与 items.csv 的「题号」一致（脚本按列名匹配，不依赖列顺序）
     - 单元格 = 该题得分（0 或满分；允许在 [0, 满分] 内的部分给分）
     - 空白 / NA / - / — / ? 视为缺失
     - 「水平」列为可选附加列（专业生 / 二外生），缺失则留空
     - 同一被试同一时点可以有多行（例如 A/B 卷分次录入），脚本按
       (匿名编码, 轮次, 时点) 聚合：每个题号取第一个非缺失值

================================================================================
四、输出
================================================================================
- scores.csv：每名被试每时点一行
    匿名编码,轮次,水平,时点,图文音_接受性,图文音_产出性,纯文字_接受性,纯文字_产出性,
    图文音_总分,纯文字_总分,模态增益
- stats.txt ：可读的统计报告（含样本量、缺失处理说明、全部检验结果、方法假设）

================================================================================
五、用法
================================================================================
  # 计分 + 统计（默认在当前目录找三份 CSV，输出也写到当前目录）
  python score_vocab_test.py

  # 指定路径
  python score_vocab_test.py --bindings bindings.csv --items items.csv \
                             --responses responses.csv --out ./out --seed 12345 --n-boot 5000

  # 生成三份 CSV 模板（含表头与示例行），方便教师录入
  python score_vocab_test.py --template ./模板
  python score_vocab_test.py template ./模板          # 等价写法

  # 自测：用固定随机种子的合成数据跑通全流程并断言结果，结尾输出 PASS
  python score_vocab_test.py --selftest
  python score_vocab_test.py selftest
      （自测产物写入系统临时目录；若该目录不可写（如受限沙箱），
        则回退到当前目录下的 _score_vocab_selftest/，运行时会把实际路径打印出来）

================================================================================
六、依赖
================================================================================
仅 Python 标准库（math / statistics / csv / argparse / random / tempfile / unicodedata）。
t 分布、F 分布的分位与 p 值用 math.lgamma 实现正则化不完全 Beta 函数（Numerical Recipes
的连分式法），精度优于 1e-12。
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import math
import os
import random
import statistics
import sys
import tempfile
import unicodedata
from collections import OrderedDict

# ==============================================================================
# 1. 常量：口径固定值
# ==============================================================================

MODE_MM = "图文音"          # 多模态组（图文音）
MODE_TX = "纯文字"          # 非多模态组（纯文字）
MODES = (MODE_MM, MODE_TX)

DIM_REC = "接受性"
DIM_PRO = "产出性"
DIMS = (DIM_REC, DIM_PRO)

ITEM_TYPES = ("认读", "选义", "听辨", "写假名", "填空")
TYPE_TO_DIM = {
    "认读": DIM_REC,
    "选义": DIM_REC,
    "听辨": DIM_REC,
    "写假名": DIM_PRO,
    "填空": DIM_PRO,
}
TYPE_ORDER = {t: i for i, t in enumerate(ITEM_TYPES)}

FULL_SCORE = 50.0
# 每个模态组、每个知识维度的应有分值（口径固定）
EXPECTED_MODE_DIM_POINTS = {
    (MODE_MM, DIM_REC): 15.0,
    (MODE_MM, DIM_PRO): 10.0,
    (MODE_TX, DIM_REC): 15.0,
    (MODE_TX, DIM_PRO): 10.0,
}
# 每种题型的应有分值合计（口径固定，仅告警）
EXPECTED_TYPE_POINTS = {t: 10.0 for t in ITEM_TYPES}

TIME_IMMEDIATE = "即时"
TIME_DELAYED = "延迟"
TIME_ORDER = {TIME_IMMEDIATE: 0, TIME_DELAYED: 1}

# 内部字段名（与 scores.csv 列名一致）
K_CODE = "匿名编码"
K_ROUND = "轮次"
K_LEVEL = "水平"
K_TIME = "时点"
K_MA = "图文音_接受性"
K_MP = "图文音_产出性"
K_TA = "纯文字_接受性"
K_TP = "纯文字_产出性"
K_MT = "图文音_总分"
K_TT = "纯文字_总分"
K_GAIN = "模态增益"

SCORE_HEADER = [K_CODE, K_ROUND, K_LEVEL, K_TIME,
                K_MA, K_MP, K_TA, K_TP, K_MT, K_TT, K_GAIN]

# responses.csv 中允许作为「缺失」的记号
MISSING_TOKENS = {"", "-", "--", "—", "–", "na", "n/a", "nan", "null", "none", "?", "/", "无"}

BINDINGS_HEADER = ["主题", "序号", "单词", "呈现模式"]
ITEMS_HEADER = ["题号", "单词", "题型", "维度", "分值"]


class DataError(Exception):
    """输入数据不符合口径时抛出；由 main 捕获后打印中文错误并以非零码退出。"""


# ==============================================================================
# 2. 分布的数值实现（纯标准库；t / F 的 CDF、分位）
# ==============================================================================

def _betacf(a, b, x, itmax=500, eps=3.0e-16):
    """正则化不完全 Beta 函数的连分式（Lentz 算法，Numerical Recipes 6.4）。"""
    tiny = 1.0e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betainc(a, b, x):
    """正则化不完全 Beta 函数 I_x(a, b)。"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                  + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_two_sided_p(t, df):
    """Student t 分布的双侧 p 值：p = I_{df/(df+t^2)}(df/2, 1/2)。"""
    if df <= 0:
        return float("nan")
    if not math.isfinite(t):
        return 1.0
    x = df / (df + t * t)
    return min(1.0, max(0.0, betainc(df / 2.0, 0.5, x)))


def t_crit(alpha, df):
    """t 分布的双侧临界值 t_{1-alpha/2, df}（对 CDF 二分求根，精度 1e-12）。"""
    if df <= 0:
        return float("nan")
    if alpha <= 0.0:
        return float("inf")
    if alpha >= 1.0:
        return 0.0
    lo, hi = 0.0, 1.0e6
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if t_two_sided_p(mid, df) > alpha:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1.0e-12:
            break
    return 0.5 * (lo + hi)


def f_sf(F, df1, df2):
    """F 分布的右尾 p 值：p = P(F_{df1,df2} > F)。"""
    if df1 <= 0 or df2 <= 0:
        return float("nan")
    if F <= 0.0:
        return 1.0
    if not math.isfinite(F):
        return 0.0
    x = df2 / (df2 + df1 * F)
    return min(1.0, max(0.0, betainc(df2 / 2.0, df1 / 2.0, x)))


# ==============================================================================
# 3. 小工具
# ==============================================================================

def _mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def _sd(xs):
    """样本标准差（ddof=1）。"""
    return statistics.stdev(xs) if len(xs) > 1 else float("nan")


def _var(xs):
    return statistics.variance(xs) if len(xs) > 1 else float("nan")


def _dw(s):
    """字符串显示宽度（CJK 全角算 2 列），用于让报告表格对齐。"""
    w = 0
    for ch in s:
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def _pad(s, width, align="left"):
    s = str(s)
    gap = max(1, width - _dw(s))
    return s + " " * gap if align == "left" else " " * gap + s


def _fmt_num(v, nd=4):
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return "nan" if math.isnan(v) else ("inf" if v > 0 else "-inf")
    return f"{v:.{nd}f}"


def _fmt_p(p):
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "nan"
    if p < 1e-6:
        return f"{p:.3e}"
    return f"{p:.6f}"


def _fmt_cell(v):
    """写 CSV 用：整数去掉小数点，浮点保留必要精度。"""
    if v is None:
        return ""
    if isinstance(v, float) and float(v).is_integer():
        return str(int(v))
    return repr(v) if isinstance(v, float) else str(v)


def _to_float(tok):
    """把单元格解析为 float；缺失记号返回 None。解析失败抛 DataError 由上层带上下文重抛。"""
    s = (tok or "").strip()
    if s.lower() in MISSING_TOKENS:
        return None
    s = s.replace("％", "%").replace("，", ",")
    return float(s)  # 可能抛 ValueError


def _table(headers, rows, aligns=None):
    """生成对齐的文本表格（CJK 宽度感知）。"""
    rows = [[("" if c is None else str(c)) for c in r] for r in rows]
    widths = [_dw(h) for h in headers]
    for r in rows:
        for i, c in enumerate(r):
            if i < len(widths):
                widths[i] = max(widths[i], _dw(c))
    aligns = aligns or ["left"] * len(headers)
    out = ["  ".join(_pad(h, widths[i]) for i, h in enumerate(headers)).rstrip()]
    out.append("-" * (_dw(out[0]) + 2))
    for r in rows:
        out.append("  ".join(_pad(c, widths[i]) for i, c in enumerate(r)).rstrip())
    return out


def _pct_rank(sorted_vals, q):
    """线性插值分位数（等价 numpy.percentile 的线性法）。q ∈ [0,100]。"""
    n = len(sorted_vals)
    if n == 0:
        return float("nan")
    if n == 1:
        return sorted_vals[0]
    pos = (q / 100.0) * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


# ==============================================================================
# 4. 输入读取与校验
# ==============================================================================

def _read_csv(path, kind, required):
    """读取一份 CSV 并返回 (fieldnames, list[dict])，统一处理 BOM / 空白 / 表头缺失。"""
    if not os.path.exists(path):
        raise DataError(f"找不到文件：{path}（{kind}）")
    if os.path.isdir(path):
        raise DataError(f"路径是一个目录而不是文件：{path}（{kind}）")
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh)
            try:
                raw_header = next(reader)
            except StopIteration:
                raise DataError(f"文件为空（没有任何行）：{path}（{kind}）")
            header = [(h or "").strip().lstrip("\ufeff") for h in raw_header]
            header = [h for h in header if h != ""]
            if not header:
                raise DataError(f"表头为空：{path}（{kind}）")
            dup = [h for h in set(header) if header.count(h) > 1]
            if dup:
                raise DataError(f"{kind} 表头存在重复列名：{'、'.join(sorted(dup))}（{path}）")
            missing = [c for c in required if c not in header]
            if missing:
                raise DataError(
                    f"{kind} 缺少必需的列：{'、'.join(missing)}（文件：{path}）\n"
                    f"        实际表头为：{','.join(header)}\n"
                    f"        请用 `--template` 生成标准模板后对照修改。"
                )
            rows = []
            for lineno, rec in enumerate(reader, start=2):
                if not rec or all((c or "").strip() == "" for c in rec):
                    continue
                padded = list(rec) + [""] * (len(header) - len(rec))
                d = {}
                for i, col in enumerate(header):
                    d[col] = (padded[i] or "").strip()
                d["__lineno__"] = lineno
                rows.append(d)
    except UnicodeDecodeError as exc:
        raise DataError(f"文件不是 UTF-8 编码，无法读取：{path}（{kind}）—— {exc}\n"
                        f"        请另存为「CSV UTF-8」后重试。")
    if not rows:
        raise DataError(f"{kind} 只有表头、没有任何数据行：{path}")
    return header, rows


def read_bindings(path):
    """读取词-模态绑定表：返回 (word -> {'主题','序号','呈现模式'}, 告警列表, 行列表)。"""
    warns = []
    _, rows = _read_csv(path, "词-模态绑定表 bindings.csv", ["主题", "序号", "单词", "呈现模式"])
    table = OrderedDict()
    for r in rows:
        word = r["单词"]
        mode = r["呈现模式"]
        if not word:
            raise DataError(f"bindings.csv 第 {r['__lineno__']} 行的「单词」为空。")
        if mode not in MODES:
            raise DataError(
                f"bindings.csv 第 {r['__lineno__']} 行的「呈现模式」= 「{mode}」不合法。\n"
                f"        只允许：{'、'.join(MODES)}"
            )
        if word in table:
            prev = table[word]
            raise DataError(
                f"bindings.csv 中单词「{word}」出现多次"
                f"（第 {prev['__lineno__']} 行与第 {r['__lineno__']} 行）。\n"
                f"        同一词必须只有一条模态绑定记录；若不同主题下确有同形词，"
                f"请在「单词」列加主题前缀区分。"
            )
        table[word] = {"主题": r["主题"], "序号": r["序号"], "呈现模式": mode,
                       "__lineno__": r["__lineno__"]}
    # 结构提示：每个测试主题内 10 图文音 + 10 纯文字
    per_theme = OrderedDict()
    for w, info in table.items():
        per_theme.setdefault(info["主题"], {MODE_MM: 0, MODE_TX: 0})
        per_theme[info["主题"]][info["呈现模式"]] += 1
    for theme, cnt in per_theme.items():
        if cnt[MODE_MM] != cnt[MODE_TX]:
            warns.append(f"绑定表主题「{theme}」的图文音词 {cnt[MODE_MM]} 个、"
                         f"纯文字词 {cnt[MODE_TX]} 个，两者不相等（设计口径为 10/10）。")
    return table, warns, rows


def read_items(path):
    """读取题目表；返回 (items, 告警列表)。"""
    warns = []
    _, rows = _read_csv(path, "题目表 items.csv", ["题号", "单词", "题型", "维度", "分值"])
    items = []
    seen_code = {}
    for r in rows:
        code = r["题号"]
        word = r["单词"]
        itype = r["题型"]
        dim = r["维度"]
        if not code:
            raise DataError(f"items.csv 第 {r['__lineno__']} 行的「题号」为空。")
        if code in seen_code:
            raise DataError(f"items.csv 中题号「{code}」重复出现"
                            f"（第 {seen_code[code]} 行与第 {r['__lineno__']} 行）。")
        seen_code[code] = r["__lineno__"]
        if not word:
            raise DataError(f"items.csv 第 {r['__lineno__']} 行（题号 {code}）的「单词」为空。")
        if itype not in ITEM_TYPES:
            raise DataError(
                f"items.csv 第 {r['__lineno__']} 行（题号 {code}）的「题型」= 「{itype}」不合法。\n"
                f"        只允许：{'、'.join(ITEM_TYPES)}"
            )
        if dim not in DIMS:
            raise DataError(
                f"items.csv 第 {r['__lineno__']} 行（题号 {code}）的「维度」= 「{dim}」不合法。\n"
                f"        只允许：{'、'.join(DIMS)}"
            )
        if TYPE_TO_DIM[itype] != dim:
            raise DataError(
                f"items.csv 第 {r['__lineno__']} 行（题号 {code}）：题型「{itype}」属于"
                f"「{TYPE_TO_DIM[itype]}」，但「维度」列写的是「{dim}」，两者矛盾。"
            )
        try:
            full = _to_float(r["分值"])
        except ValueError:
            raise DataError(f"items.csv 第 {r['__lineno__']} 行（题号 {code}）的「分值」"
                            f"= 「{r['分值']}」不是数字。")
        if full is None or full <= 0:
            raise DataError(f"items.csv 第 {r['__lineno__']} 行（题号 {code}）的「分值」"
                            f"必须为正数，当前为「{r['分值']}」。")
        items.append({"题号": code, "单词": word, "题型": itype, "维度": dim, "分值": full,
                      "__lineno__": r["__lineno__"]})
    return items, warns


def validate_items(items, bindings):
    """校验分值口径。返回 (info_lines, warn_lines)；口径不符直接抛 DataError。"""
    info, warns = [], []

    # --- 4.1 每道题的模态来自「词-模态绑定表」 ---
    unknown = [it for it in items if it["单词"] not in bindings]
    if unknown:
        lines = "\n".join(
            f"        题号 {it['题号']}（第 {it['__lineno__']} 行）的单词「{it['单词']}」"
            f"未出现在 bindings.csv 中" for it in unknown[:20])
        more = f"\n        ……另有 {len(unknown) - 20} 行同样问题" if len(unknown) > 20 else ""
        raise DataError(
            "以下题目的单词在词-模态绑定表中找不到，无法判定其呈现模式：\n" + lines + more + "\n"
            "        请在 bindings.csv 中补齐这些词的「呈现模式」。"
        )
    for it in items:
        it["呈现模式"] = bindings[it["单词"]]["呈现模式"]

    # --- 4.2 一词一题 ---
    words = [it["单词"] for it in items]
    dup = sorted({w for w in words if words.count(w) > 1})
    if dup:
        warns.append("以下单词对应了多道题（设计口径为「一词一题」）：" + "、".join(dup[:20]))

    # --- 4.3 分值合计 ---
    total = sum(it["分值"] for it in items)
    if abs(total - FULL_SCORE) > 1e-9:
        raise DataError(
            f"题目分值合计 = {_fmt_cell(total)} 分，与口径要求的 {_fmt_cell(FULL_SCORE)} 分不符。\n"
            f"        口径：接受性 30 分（认读 10 + 选义 10 + 听辨 10，每题 1 分）"
            f" + 产出性 20 分（写假名 5 + 填空 5，每题 2 分）= 50 分。\n"
            f"        题量：{len(items)} 题。请核对 items.csv 的「分值」列。"
        )

    # --- 4.4 每个模态组内的接受性 / 产出性分值 ---
    grid = {}
    for it in items:
        grid[(it["呈现模式"], it["维度"])] = grid.get((it["呈现模式"], it["维度"]), 0.0) + it["分值"]
    for mode in MODES:
        g_rec = grid.get((mode, DIM_REC), 0.0)
        g_pro = grid.get((mode, DIM_PRO), 0.0)
        exp_rec = EXPECTED_MODE_DIM_POINTS[(mode, DIM_REC)]
        exp_pro = EXPECTED_MODE_DIM_POINTS[(mode, DIM_PRO)]
        if abs(g_rec - exp_rec) > 1e-9 or abs(g_pro - exp_pro) > 1e-9:
            n_rec = sum(1 for it in items if it["呈现模式"] == mode and it["维度"] == DIM_REC)
            n_pro = sum(1 for it in items if it["呈现模式"] == mode and it["维度"] == DIM_PRO)
            raise DataError(
                f"「{mode}」组的子分分值不符口径：接受性 {_fmt_cell(g_rec)} 分（应为 "
                f"{_fmt_cell(exp_rec)} 分，现 {n_rec} 题）、产出性 {_fmt_cell(g_pro)} 分"
                f"（应为 {_fmt_cell(exp_pro)} 分，现 {n_pro} 题）。\n"
                f"        口径：每类词各 20 题（测试词 40 个 = 20 图文音 + 20 纯文字），\n"
                f"              组内接受性 15 题 × 1 分 = 15 分；产出性 5 题 × 2 分 = 10 分。\n"
                f"        请检查 bindings.csv 的模态分配与 items.csv 的题型/分值是否配套。"
            )

    # --- 4.5 题型构成（仅告警） ---
    for t in ITEM_TYPES:
        pts = sum(it["分值"] for it in items if it["题型"] == t)
        cnt = sum(1 for it in items if it["题型"] == t)
        if abs(pts - EXPECTED_TYPE_POINTS[t]) > 1e-9:
            warns.append(f"题型「{t}」共 {cnt} 题 / {_fmt_cell(pts)} 分，"
                         f"与口径的 10 分不一致（请确认是否有意调整）。")
    # --- 4.6 每模态题量（仅告警） ---
    for mode in MODES:
        cnt = sum(1 for it in items if it["呈现模式"] == mode)
        if cnt != 20:
            warns.append(f"「{mode}」组共 {cnt} 题，与口径的 20 题不一致。")

    info.append(f"题目总数：{len(items)} 题，分值合计 {_fmt_cell(total)} 分")
    for mode in MODES:
        for dim in DIMS:
            cnt = sum(1 for it in items if it["呈现模式"] == mode and it["维度"] == dim)
            pts = grid.get((mode, dim), 0.0)
            info.append(f"  {mode} × {dim}：{cnt} 题 / {_fmt_cell(pts)} 分")
    for t in ITEM_TYPES:
        cnt = sum(1 for it in items if it["题型"] == t)
        pts = sum(it["分值"] for it in items if it["题型"] == t)
        info.append(f"  题型「{t}」：{cnt} 题 / {_fmt_cell(pts)} 分（{TYPE_TO_DIM[t]}）")
    unused = [w for w in bindings if w not in set(words)]
    if unused:
        info.append(f"绑定表中未被任何题目引用的词 {len(unused)} 个"
                    f"（多为主题3/4 扩展词，不进入测试）：{'、'.join(unused[:12])}"
                    + ("……" if len(unused) > 12 else ""))
    return info, warns


def read_responses(path, item_codes, item_max):
    """读取作答宽表并聚合。

    返回 dict：
      agg          : OrderedDict[(编码, 轮次, 时点)] -> {'水平', 'vals':{题号:float|None}, 'rows':n}
      warns        : 告警列表
      item_cols    : 表头中命中的题号（保持表头顺序）
      extra_cols   : 被忽略的未知列
    """
    if not os.path.exists(path):
        raise DataError(f"找不到文件：{path}（作答表 responses.csv）")
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh)
            try:
                raw_header = next(reader)
            except StopIteration:
                raise DataError(f"文件为空（没有任何行）：{path}（作答表 responses.csv）")
            header = [(h or "").strip().lstrip("\ufeff") for h in raw_header]
            if not header:
                raise DataError(f"表头为空：{path}（作答表 responses.csv）")
            missing_keys = [c for c in (K_CODE, K_ROUND, K_TIME) if c not in header]
            if missing_keys:
                raise DataError(
                    f"作答表 responses.csv 缺少必需的列：{'、'.join(missing_keys)}\n"
                    f"        实际表头前几列：{','.join(header[:8])}\n"
                    f"        要求：匿名编码,轮次,时点,[水平,]题号1,题号2,..."
                )
            code_set = set(item_codes)
            item_cols = [h for h in header if h in code_set]
            absent = [c for c in item_codes if c not in set(header)]
            if absent:
                raise DataError(
                    f"作答表 responses.csv 表头中缺少以下题号列：{'、'.join(absent[:20])}"
                    + ("……" if len(absent) > 20 else "") + "\n"
                    f"        宽表必须包含 items.csv 中全部题号的列（列名与「题号」完全一致）。\n"
                    f"        若 A/B 卷分文件录入，请先合并为一张宽表再计分。"
                )
            extra_cols = [h for h in header
                          if h not in code_set and h not in (K_CODE, K_ROUND, K_TIME, K_LEVEL)]
            has_level = K_LEVEL in header

            warns = []
            if extra_cols:
                warns.append("作答表中有被忽略的未知列（不参与计分）："
                             + "、".join(extra_cols[:20]) + ("……" if len(extra_cols) > 20 else ""))

            agg = OrderedDict()
            conflict = 0
            level_conflict = 0
            out_of_range = []
            bad_cells = []
            for lineno, rec in enumerate(reader, start=2):
                if not rec or all((c or "").strip() == "" for c in rec):
                    continue
                padded = list(rec) + [""] * (len(header) - len(rec))
                row = {header[i]: (padded[i] or "").strip() for i in range(len(header))}
                code = row[K_CODE]
                rnd = row[K_ROUND]
                tpoint = row[K_TIME]
                if not code:
                    raise DataError(f"responses.csv 第 {lineno} 行的「{K_CODE}」为空。")
                if not tpoint:
                    raise DataError(f"responses.csv 第 {lineno} 行（{code}）的「{K_TIME}」为空。")
                key = (code, rnd, tpoint)
                slot = agg.get(key)
                if slot is None:
                    slot = {"水平": row.get(K_LEVEL, "") if has_level else "",
                            "vals": {c: None for c in item_codes}, "rows": 0}
                    agg[key] = slot
                elif has_level and row.get(K_LEVEL, ""):
                    if not slot["水平"]:
                        slot["水平"] = row[K_LEVEL]
                    elif slot["水平"] != row[K_LEVEL]:
                        level_conflict += 1
                slot["rows"] += 1
                for c in item_cols:
                    tok = row.get(c, "")
                    try:
                        v = _to_float(tok)
                    except ValueError:
                        bad_cells.append(f"{code}/{rnd}/{tpoint}/{c}=「{tok}」(第 {lineno} 行)")
                        continue
                    if v is None:
                        continue
                    if v < -1e-9 or v > item_max[c] + 1e-9:
                        out_of_range.append(
                            f"{code}/{rnd}/{tpoint}/{c}={_fmt_cell(v)}"
                            f"（该题满分 {_fmt_cell(item_max[c])}）")
                    if slot["vals"][c] is None:
                        slot["vals"][c] = v
                    elif abs(slot["vals"][c] - v) > 1e-9:
                        conflict += 1
                        slot["vals"][c] = slot["vals"][c]  # 保留首个非缺失值
            if conflict:
                warns.append(f"同一被试同时点存在 {conflict} 处「同一题号出现两个不同得分」的冲突，"
                             f"已按「保留首个非缺失值」处理；建议核对 A/B 卷录入。")
            if level_conflict:
                warns.append(f"同一被试同时点出现 {level_conflict} 处「水平」取值不一致，"
                             f"已保留首次出现的取值。")
            if bad_cells:
                warns.append(f"以下 {len(bad_cells)} 个单元格不是数字，已按缺失处理："
                             + "、".join(bad_cells[:10]) + ("……" if len(bad_cells) > 10 else ""))
            if out_of_range:
                warns.append(f"以下 {len(out_of_range)} 个得分超出 [0, 该题满分] 范围（已原样保留，"
                             f"请核对录入）：" + "、".join(out_of_range[:10])
                             + ("……" if len(out_of_range) > 10 else ""))
    except UnicodeDecodeError as exc:
        raise DataError(f"作答表不是 UTF-8 编码，无法读取：{path} —— {exc}\n"
                        f"        请另存为「CSV UTF-8」后重试。")
    return {"agg": agg, "warns": warns, "item_cols": item_cols,
            "extra_cols": extra_cols, "has_level": has_level}


def build_scores(items, responses):
    """按 4 个子分计分；缺失按「整行剔除」处理。

    返回 (rows, excluded, stats_info)：
      rows     : 完整行（list[dict]，键见 K_* 常量）
      excluded : [(编码, 轮次, 时点, 缺失题数, 缺失题号前几个)]
      stats_info: dict(n_raw, n_complete, n_excluded, ...)
    """
    agg = responses["agg"]
    item_codes = [it["题号"] for it in items]

    # 预计算：题号 -> (模态, 维度, 分值)
    meta = {it["题号"]: (it["呈现模式"], it["维度"], it["分值"]) for it in items}

    rows, excluded = [], []
    for (code, rnd, tpoint), slot in agg.items():
        miss = [c for c in item_codes if slot["vals"][c] is None]
        if miss:
            excluded.append((code, rnd, tpoint, len(miss), miss[:5]))
            continue
        sub = {(m, d): 0.0 for m in MODES for d in DIMS}
        for c in item_codes:
            m, d, _ = meta[c]
            sub[(m, d)] += slot["vals"][c]
        rec = {
            K_CODE: code, K_ROUND: rnd, K_LEVEL: slot["水平"], K_TIME: tpoint,
            K_MA: sub[(MODE_MM, DIM_REC)], K_MP: sub[(MODE_MM, DIM_PRO)],
            K_TA: sub[(MODE_TX, DIM_REC)], K_TP: sub[(MODE_TX, DIM_PRO)],
        }
        rec[K_MT] = rec[K_MA] + rec[K_MP]
        rec[K_TT] = rec[K_TA] + rec[K_TP]
        rec[K_GAIN] = rec[K_MT] - rec[K_TT]
        rows.append(rec)

    def sort_key(r):
        return (r[K_CODE], r[K_ROUND], TIME_ORDER.get(r[K_TIME], 99), r[K_TIME])

    rows.sort(key=sort_key)
    excluded.sort(key=lambda t: (t[0], t[1], TIME_ORDER.get(t[2], 99)))

    info = {
        "n_raw_obs": len(agg),
        "n_complete": len(rows),
        "n_excluded": len(excluded),
        "n_multi_row": sum(1 for s in agg.values() if s["rows"] > 1),
        "codes_excluded": sorted({e[0] for e in excluded}),
    }
    return rows, excluded, info


# ==============================================================================
# 5. 统计检验
# ==============================================================================

def paired_t_test(xs, ys, label_x="图文音", label_y="纯文字"):
    """配对样本 t 检验 + Cohen's d_z + 差值均数的 95% CI。

    t = mean(d) / (sd(d)/sqrt(n))，df = n - 1，d = x - y（ddof=1 的样本标准差）。
    Cohen's d_z = mean(d) / sd(d)（差值均数 ÷ 差值标准差）。
    """
    n = len(xs)
    if n != len(ys):
        raise DataError("内部错误：配对检验的两个变量长度不一致。")
    if n < 2:
        return {"n": n, "ok": False, "reason": f"有效配对 n = {n} < 2，无法做配对 t 检验。"}
    d = [x - y for x, y in zip(xs, ys)]
    md = _mean(d)
    sd_d = _sd(d)
    se = sd_d / math.sqrt(n) if sd_d > 0 else 0.0
    if se > 0:
        t = md / se
        df = n - 1
        p = t_two_sided_p(t, df)
        tc = t_crit(0.05, df)
        ci = (md - tc * se, md + tc * se)
        dz = md / sd_d
    else:
        t, df, p, dz = float("inf") if md != 0 else 0.0, n - 1, 0.0 if md != 0 else 1.0, float("inf") if md != 0 else 0.0
        ci = (md, md)
    return {
        "n": n, "ok": True,
        "label_x": label_x, "label_y": label_y,
        "mean_x": _mean(xs), "sd_x": _sd(xs),
        "mean_y": _mean(ys), "sd_y": _sd(ys),
        "mean_d": md, "sd_d": sd_d, "se": se,
        "t": t, "df": df, "p": p, "dz": dz,
        "ci_lo": ci[0], "ci_hi": ci[1],
    }


def rm_anova_2x2(mat):
    """2×2 全被试内重复测量 ANOVA（呈现模式 A × 知识维度 B）。

    mat[i] = (y_图接, y_图产, y_纯接, y_纯产)，顺序固定。

    ---- SS 分解（正交归一化对照法，等价于经典「单元格均值」分解）----
    记 4 个单元格的对照编码（+1 表示该效应的正极）：
        A  (呈现模式) : (+1, +1, -1, -1)   Σc² = 4
        B  (知识维度) : (+1, -1, +1, -1)   Σc² = 4
        A×B           : (+1, -1, -1, +1)   Σc² = 4
    对第 i 名被试取对照分 L_i = Σ_l c_l · y_il，则
        SS_effect = n · mean(L)² / Σc²
        SS_error  = Σ_i (L_i - mean(L))² / Σc²          （即「效应 × 被试」交互项）
    三条对照方向两两正交，故有恒等式
        SS_A + SS_B + SS_AB + SS_errA + SS_errB + SS_errAB = SS_被试内
    其中 SS_被试内 = Σ_i Σ_l (y_il - mean_i)²（df = 3n）。
    a=b=2 时三个对照的 df 均为 1，故每个误差项的 df = n-1（即 (n-1)(a-1)、
    (n-1)(b-1)、(n-1)(a-1)(b-1) 在 2×2 下同为 n-1）。

    ⚠ 三个误差项**数值上一般并不相等**（只是自由度相同），因此本函数按
      「每个效应使用自己的匹配误差项」（sphericity assumed，SPSS 默认行为）报告主结果，
      同时额外给出把三者合并的「合并误差」口径供对照。
    """
    n = len(mat)
    if n < 3:
        return {"ok": False, "reason": f"有效被试 n = {n} < 3，无法做重复测量 ANOVA。"}

    codes = {
        "A": (1.0, 1.0, -1.0, -1.0),
        "B": (1.0, -1.0, 1.0, -1.0),
        "AB": (1.0, -1.0, -1.0, 1.0),
    }
    res = {"ok": True, "n": n, "effects": {}}
    ss_err_pooled = 0.0
    for key, c in codes.items():
        ss_c = sum(ci * ci for ci in c)
        L = [sum(ci * yi for ci, yi in zip(c, row)) for row in mat]
        Lbar = _mean(L)
        ss_eff = n * Lbar * Lbar / ss_c
        ss_err = sum((l - Lbar) ** 2 for l in L) / ss_c
        df_eff, df_err = 1, n - 1
        ms_eff = ss_eff / df_eff
        ms_err = ss_err / df_err
        if ms_err > 0:
            F = ms_eff / ms_err
            p = f_sf(F, df_eff, df_err)
        else:
            F = float("inf") if ss_eff > 0 else 0.0
            p = 0.0 if ss_eff > 0 else 1.0
        eta2p = ss_eff / (ss_eff + ss_err) if (ss_eff + ss_err) > 0 else float("nan")
        res["effects"][key] = {
            "SS": ss_eff, "df": df_eff, "MS": ms_eff,
            "SS_error": ss_err, "df_error": df_err, "MS_error": ms_err,
            "F": F, "p": p, "eta2p": eta2p,
        }
        ss_err_pooled += ss_err

    df_pool = 3 * (n - 1)
    ms_err_pooled = ss_err_pooled / df_pool if df_pool > 0 else float("nan")
    res["SS_error_pooled"] = ss_err_pooled
    res["df_error_pooled"] = df_pool
    res["MS_error_pooled"] = ms_err_pooled
    for key in codes:
        e = res["effects"][key]
        if ms_err_pooled and ms_err_pooled > 0:
            e["F_pooled"] = e["MS"] / ms_err_pooled
            e["p_pooled"] = f_sf(e["F_pooled"], 1, df_pool)
        else:
            e["F_pooled"] = float("nan")
            e["p_pooled"] = float("nan")

    # 恒等式核对：被试内分解应恰好等于 Σ_i Σ_l (y_il - mean_i)²
    gm = _mean([v for row in mat for v in row])
    ss_within = sum((v - _mean(row)) ** 2 for row in mat for v in row)
    ss_between = 4.0 * sum((_mean(row) - gm) ** 2 for row in mat)
    ss_total = sum((v - gm) ** 2 for row in mat for v in row)
    lhs = sum(res["effects"][k]["SS"] + res["effects"][k]["SS_error"] for k in codes)
    res["ss_within_subjects"] = ss_within
    res["ss_between_subjects"] = ss_between
    res["ss_total"] = ss_total
    res["identity_within"] = abs(lhs - ss_within) / max(1.0, abs(ss_within))
    res["identity_total"] = abs((ss_within + ss_between) - ss_total) / max(1.0, abs(ss_total))

    # 供报告用的便捷量：两维度上的模态增益（配对差值）
    ga = [row[0] - row[2] for row in mat]   # 接受性：图文音 - 纯文字
    gp = [row[1] - row[3] for row in mat]   # 产出性：图文音 - 纯文字
    res["gain_receptive"] = ga
    res["gain_productive"] = gp
    res["gain_diff"] = [a - p for a, p in zip(ga, gp)]
    return res


def one_way_anova_between(groups):
    """一水平被试间单因素 ANOVA（仅用于混合设计的自检与辅助报告）。"""
    allv = [v for g in groups for v in g]
    N = len(allv)
    k = len(groups)
    if N - k <= 0:
        return {"ok": False}
    gm = _mean(allv)
    ss_b = sum(len(g) * (_mean(g) - gm) ** 2 for g in groups if g)
    ss_w = sum(sum((v - _mean(g)) ** 2 for v in g) for g in groups if g)
    df_b, df_w = k - 1, N - k
    ms_b = ss_b / df_b if df_b else float("nan")
    ms_w = ss_w / df_w if df_w else float("nan")
    F = ms_b / ms_w if ms_w and ms_w > 0 else float("nan")
    return {"ok": True, "SS_between": ss_b, "df_between": df_b, "MS_between": ms_b,
            "SS_within": ss_w, "df_within": df_w, "MS_within": ms_w,
            "F": F, "p": f_sf(F, df_b, df_w) if math.isfinite(F) else float("nan")}


def mixed_anova_2x2(within_pairs, groups):
    """2×2 混合设计 ANOVA：A = 呈现模式（被试内，2 水平）× B = 水平（被试间，2 组）。

    within_pairs[i] = (y_图文音, y_纯文字)，groups[i] = 组标签（恰好 2 组）。

    ---- SS 分解（经典分解；n_g 为各组人数，N = Σn_g，a = 2）----
    记第 i 名被试的差值 Δ_i = y_i1 - y_i2，组均值 Δ_g，加权总均值 Δ = Σn_gΔ_g/N。
    令 M_i = 被试均值（两个模态的平均），M_g = 组均值，GM = 全体总均值。

    析出被试间部分：
        SS_B      = a · Σ_g n_g (M_g - GM)²                    df = b-1 = 1
        SS_误差(B) = a · Σ_g Σ_i (M_i - M_g)²                    df = N-b   （被试(组内)效应）
    析出被试内部分（等价于对差值 Δ 做单因素被试间 ANOVA，再乘以 1/2）：
        SS_A      = N · Δ² / 2                                  df = a-1 = 1
        SS_A×B    = Σ_g n_g (Δ_g - Δ)² / 2                       df = (a-1)(b-1) = 1
        SS_误差(A) = Σ_g Σ_i (Δ_i - Δ_g)² / 2                    df = (a-1)(N-b) = N-b
        （A×B 与 A 共用同一误差项「A×被试(组内)」，故 df 同为 N-b）

    恒等式：SS_B + SS_误差(B) + SS_A + SS_A×B + SS_误差(A) = SS_总。
    在 a = 2 时，上述 1/2 因子来自「Σ_k (y_k - M_i)² = Δ_i²/2」。

    ⚠ 不等组（n_1 ≠ n_2）时 SS_A / SS_A×B 与 SS_B 不再正交，本函数采用
      「加权均值」口径（等价于 SPSS 的 Type III 在被试内部分的处理）；
      若各组人数相差较大，建议研究者用 SPSS/Pingouin 的 Type III 平方和复核。
    """
    N = len(within_pairs)
    labels = list(OrderedDict.fromkeys(groups))
    if len(labels) != 2:
        return {"ok": False,
                "reason": f"被试间因素的组数 = {len(labels)}（{'、'.join(labels) or '无'}），"
                          f"2×2 混合设计需要恰好 2 组。"}
    if N - 2 <= 0:
        return {"ok": False, "reason": f"总被试数 N = {N}，不足以估计误差项（需 N > 2）。"}

    idx = {lab: [] for lab in labels}
    for i, g in enumerate(groups):
        idx[g].append(i)
    ns = {lab: len(idx[lab]) for lab in labels}
    a = 2

    allv = [v for pair in within_pairs for v in pair]
    GM = _mean(allv)
    M_subj = [_mean(p) for p in within_pairs]
    M_g = {lab: _mean([v for i in idx[lab] for v in within_pairs[i]]) for lab in labels}
    D = [p[0] - p[1] for p in within_pairs]
    D_g = {lab: _mean([D[i] for i in idx[lab]]) for lab in labels}
    D_bar = sum(ns[lab] * D_g[lab] for lab in labels) / N

    ss_B = a * sum(ns[lab] * (M_g[lab] - GM) ** 2 for lab in labels)
    ss_errB = a * sum((M_subj[i] - M_g[lab]) ** 2 for lab in labels for i in idx[lab])
    ss_A = N * D_bar * D_bar / 2.0
    ss_AB = sum(ns[lab] * (D_g[lab] - D_bar) ** 2 for lab in labels) / 2.0
    ss_errA = sum((D[i] - D_g[lab]) ** 2 for lab in labels for i in idx[lab]) / 2.0

    ss_total = sum((v - GM) ** 2 for v in allv)
    df_B, df_errB = len(labels) - 1, N - len(labels)
    df_A, df_AB, df_errA = a - 1, (a - 1) * (len(labels) - 1), (a - 1) * (N - len(labels))

    def _fx(ss, df, ss_err, df_err):
        ms = ss / df if df else float("nan")
        mse = ss_err / df_err if df_err else float("nan")
        if mse and mse > 0:
            F = ms / mse
            p = f_sf(F, df, df_err)
        else:
            F = float("inf") if ss > 0 else 0.0
            p = 0.0 if ss > 0 else 1.0
        eta = ss / (ss + ss_err) if (ss + ss_err) > 0 else float("nan")
        return {"SS": ss, "df": df, "MS": ms, "SS_error": ss_err, "df_error": df_err,
                "MS_error": mse, "F": F, "p": p, "eta2p": eta}

    res = {
        "ok": True, "n_total": N, "groups": labels, "group_n": ns,
        "group_labels_cn": list(labels),
        "GM": GM,
        "A": _fx(ss_A, df_A, ss_errA, df_errA),        # 模态主效应（被试内）
        "B": _fx(ss_B, df_B, ss_errB, df_errB),        # 水平主效应（被试间）
        "AB": _fx(ss_AB, df_AB, ss_errA, df_errA),     # 模态 × 水平交互（共用误差 A）
        "ss_total": ss_total,
        "ss_errA": ss_errA, "df_errA": df_errA,
        "ss_errB": ss_errB, "df_errB": df_errB,
        "M_g": M_g, "D_g": D_g, "D_bar": D_bar,
        "M_subj": M_subj, "D": D,
        "idx": idx,
    }
    lhs = ss_B + ss_errB + ss_A + ss_AB + ss_errA
    res["identity_total"] = abs(lhs - ss_total) / max(1.0, abs(ss_total))
    # 平衡性检查（= a=2 且各组人数相同）
    res["balanced"] = len(set(ns.values())) == 1
    # 简单效应：各组内部「图文音 vs 纯文字」配对 t
    res["simple_effects"] = {}
    for lab in labels:
        xs = [within_pairs[i][0] for i in idx[lab]]
        ys = [within_pairs[i][1] for i in idx[lab]]
        res["simple_effects"][lab] = paired_t_test(xs, ys)
    return res


def bootstrap_mean_ci(values, n_boot=5000, seed=12345, alpha=0.05):
    """被试重抽样的 Bootstrap 百分位法置信区间（对均数）。"""
    n = len(values)
    if n < 2:
        return {"n": n, "n_boot": n_boot, "mean": _mean(values),
                "lo": float("nan"), "hi": float("nan"), "seed": seed}
    rng = random.Random(seed)
    means = [0.0] * n_boot
    for b in range(n_boot):
        s = 0.0
        for _ in range(n):
            s += values[rng.randrange(n)]
        means[b] = s / n
    means.sort()
    return {
        "n": n, "n_boot": n_boot, "seed": seed,
        "mean": _mean(values),
        "sd": _sd(values),
        "lo": _pct_rank(means, 100.0 * alpha / 2.0),
        "hi": _pct_rank(means, 100.0 * (1.0 - alpha / 2.0)),
        "median": _pct_rank(means, 50.0),
        "se_boot": _sd(means),
    }


# ==============================================================================
# 6. 报告生成
# ==============================================================================

class Report:
    def __init__(self):
        self.lines = []

    def w(self, s=""):
        self.lines.append(s)

    def h1(self, title):
        self.w()
        self.w("=" * 78)
        self.w(title)
        self.w("=" * 78)

    def h2(self, title):
        self.w()
        self.w("-" * 78)
        self.w(title)
        self.w("-" * 78)

    def h3(self, title):
        self.w()
        self.w(f"◆ {title}")

    def table(self, headers, rows, aligns=None, indent="  "):
        for ln in _table(headers, rows, aligns):
            self.w(indent + ln)

    def text(self):
        return "\n".join(self.lines) + "\n"


def _subject_key(row):
    return (row[K_ROUND], row[K_CODE])


def _by_time(rows, tpoint):
    return [r for r in rows if r[K_TIME] == tpoint]


def _paired_arrays(rows, tpoint, kx, ky):
    """按「轮次 + 编码」把两个子分凑成配对；返回 (keys, xs, ys)。"""
    sel = [r for r in rows if r[K_TIME] == tpoint]
    keys = [_subject_key(r) for r in sel]
    return keys, [r[kx] for r in sel], [r[ky] for r in sel]


def emit_paired_block(rep, title, xs, ys, lx, ly):
    rep.h3(title)
    r = paired_t_test(xs, ys, lx, ly)
    if not r["ok"]:
        rep.w(f"  跳过：{r['reason']}")
        return r
    rep.table(
        ["变量对", "n", "M(图文音)", "SD", "M(纯文字)", "SD", "M(差值)", "SD(差值)", "Cohen's d_z"],
        [[f"{lx} vs {ly}", r["n"], _fmt_num(r["mean_x"], 3), _fmt_num(r["sd_x"], 3),
          _fmt_num(r["mean_y"], 3), _fmt_num(r["sd_y"], 3), _fmt_num(r["mean_d"], 3),
          _fmt_num(r["sd_d"], 3), _fmt_num(r["dz"], 3)]])
    rep.table(
        ["t", "df", "p", "差值均数 95% CI", "结论(α=.05)"],
        [[_fmt_num(r["t"], 4), r["df"], _fmt_p(r["p"]),
          f"[{_fmt_num(r['ci_lo'], 3)}, {_fmt_num(r['ci_hi'], 3)}]",
          "显著" if r["p"] < 0.05 else "不显著"]],
        aligns=["left"] * 5)
    rep.w(f"  注：d_z = 差值均数 / 差值标准差（差值为「图文音 − 纯文字」，正值表示图文音词更优）。")
    return r


def emit_descriptives(rep, rows, tpoint):
    rep.h3(f"描述统计：{tpoint}（满分：图文音/纯文字各组 25 = 接受性 15 + 产出性 10）")
    sel = _by_time(rows, tpoint)
    if not sel:
        rep.w(f"  无 {tpoint} 数据。")
        return
    specs = [(K_MA, 15.0), (K_MP, 10.0), (K_TA, 15.0), (K_TP, 10.0),
             (K_MT, 25.0), (K_TT, 25.0), (K_GAIN, None)]
    trows = []
    for k, full in specs:
        vals = [r[k] for r in sel]
        trows.append([k, len(vals), _fmt_num(_mean(vals), 3), _fmt_num(_sd(vals), 3),
                      _fmt_num(min(vals), 2), _fmt_num(max(vals), 2),
                      (_fmt_cell(full) if full else "—")])
    rep.table(["子分", "n", "M", "SD", "Min", "Max", "满分"], trows)
    if len(sel) > 1:
        rep.w(f"  注：SD 为样本标准差（ddof=1）。模态增益 = 图文音_总分 − 纯文字_总分，"
              f"取值范围 −25 ~ +25。")


def emit_h3_anova(rep, rows, tpoint, n_boot, seed):
    sel = _by_time(rows, tpoint)
    mat = [(r[K_MA], r[K_MP], r[K_TA], r[K_TP]) for r in sel]
    rep.h3(f"H3：2×2 重复测量 ANOVA（呈现模式 × 知识维度，均为被试内）—— {tpoint}")
    res = rm_anova_2x2(mat)
    if not res["ok"]:
        rep.w(f"  跳过：{res['reason']}")
        return None
    names = {"A": "呈现模式(A)", "B": "知识维度(B)", "AB": "呈现模式×知识维度(A×B)"}
    trows = []
    for k in ("A", "B", "AB"):
        e = res["effects"][k]
        trows.append([names[k], _fmt_num(e["SS"], 4), e["df"], _fmt_num(e["MS"], 4),
                      _fmt_num(e["F"], 4), _fmt_p(e["p"]), _fmt_num(e["eta2p"], 4)])
    for k in ("A", "B", "AB"):
        e = res["effects"][k]
        trows.append([f"误差({names[k]})", _fmt_num(e["SS_error"], 4), e["df_error"],
                      _fmt_num(e["MS_error"], 4), "", "", ""])
    trows.append(["合并误差(三误差之和)", _fmt_num(res["SS_error_pooled"], 4),
                  res["df_error_pooled"], _fmt_num(res["MS_error_pooled"], 4), "", "", ""])
    rep.table(["效应", "SS", "df", "MS", "F", "p", "偏 η²"], trows)
    rep.w("  另以「合并误差」为分母的对照结果（仅作参考）：")
    rep.table(["效应", "F(合并误差)", "p(合并误差)"],
              [[names[k], _fmt_num(res["effects"][k]["F_pooled"], 4),
                _fmt_p(res["effects"][k]["p_pooled"])] for k in ("A", "B", "AB")])
    rep.w(f"  恒等式核对：Σ(效应 SS + 各效应误差 SS) 与 SS_被试内 的相对偏差 = "
          f"{res['identity_within']:.3e}（应为 0，用于验证分解正确）")
    ab = res["effects"]["AB"]
    ga, gp = res["gain_receptive"], res["gain_productive"]
    rep.w(f"  两维度上的模态增益：接受性 M = {_fmt_num(_mean(ga), 3)}（SD = {_fmt_num(_sd(ga), 3)}），"
          f"产出性 M = {_fmt_num(_mean(gp), 3)}（SD = {_fmt_num(_sd(gp), 3)}）；"
          f"差值（接受性 − 产出性）M = {_fmt_num(_mean(res['gain_diff']), 3)}。")
    rep.w(f"  ⚠ 交互效应解释：A×B 的单自由度对照等价于「接受性增益 − 产出性增益」的配对 t 检验，"
          f"即 F_AB = t²（t = {_fmt_num(math.sqrt(abs(ab['F'])) if math.isfinite(ab['F']) else float('nan'), 4)}）。"
          + (f"交互显著（p = {_fmt_p(ab['p'])}）表示模态收益在两个知识维度上不均衡（支持 H3）。"
             if ab["p"] < 0.05 else
             f"交互不显著（p = {_fmt_p(ab['p'])}）→ 未见「模态收益在维度间不均衡」的证据（H3 未获支持）。"))
    rep.w("  ⚠ 本设计 3 个效应的 df 均为 1，球形性假设自动满足，无需 Greenhouse-Geisser 校正。")
    rep.w(f"  ⚠ 「知识维度」主效应比较的是 15 分制（接受性）与 10 分制（产出性）的原始分，"
          f"数值本身不具实质解释力，仅用于拆出交互效应（交互项不受量纲影响）。")

    # Bootstrap：两维度模态增益差值的 95% CI（被试重抽样）
    bs = bootstrap_mean_ci(res["gain_diff"], n_boot=n_boot, seed=seed)
    rep.h3(f"两维度「模态增益差值」（接受性增益 − 产出性增益）的 Bootstrap 95% CI —— {tpoint}")
    rep.table(["点估计 M", "SD", "95% CI 下限", "95% CI 上限", "n", "重抽样次数", "随机种子"],
              [[_fmt_num(bs["mean"], 3), _fmt_num(bs["sd"], 3), _fmt_num(bs["lo"], 3),
                _fmt_num(bs["hi"], 3), bs["n"], bs["n_boot"], bs["seed"]]])
    rep.w("  方法：以被试为单位有放回重抽样（百分位法），每次重算一次均数差；"
          "CI 不包含 0 支持「模态收益在维度间不均衡」。")
    return {"anova": res, "boot": bs}


def emit_retention(rep, rows):
    sel = [r for r in rows if r[K_TIME] in (TIME_IMMEDIATE, TIME_DELAYED)]
    byk = {}
    for r in sel:
        byk.setdefault(_subject_key(r), {})[r[K_TIME]] = r
    keys = sorted(k for k, v in byk.items() if TIME_IMMEDIATE in v and TIME_DELAYED in v)
    rep.h3("保持率（延迟 − 即时）")
    if not keys:
        rep.w("  跳过：没有任何被试同时具备即时与延迟两个时点的完整数据。")
        return None
    diff_mm = [byk[k][TIME_DELAYED][K_MT] - byk[k][TIME_IMMEDIATE][K_MT] for k in keys]
    diff_tx = [byk[k][TIME_DELAYED][K_TT] - byk[k][TIME_IMMEDIATE][K_TT] for k in keys]
    ratio_mm, ratio_tx = [], []
    for k in keys:
        im, it = byk[k][TIME_IMMEDIATE], byk[k][TIME_DELAYED]
        if im[K_MT] > 0:
            ratio_mm.append(it[K_MT] / im[K_MT])
        if im[K_TT] > 0:
            ratio_tx.append(it[K_TT] / im[K_TT])
    rep.table(["指标", "n", "M(图文音)", "SD", "M(纯文字)", "SD", "M(图文音 − 纯文字)"],
              [["保持差值 = 延迟分 − 即时分", len(keys),
                _fmt_num(_mean(diff_mm), 3), _fmt_num(_sd(diff_mm), 3),
                _fmt_num(_mean(diff_tx), 3), _fmt_num(_sd(diff_tx), 3),
                _fmt_num(_mean(diff_mm) - _mean(diff_tx), 3)],
               ["保持比值 = 延迟分 / 即时分", len(ratio_mm),
                _fmt_num(_mean(ratio_mm), 3), _fmt_num(_sd(ratio_mm), 3),
                _fmt_num(_mean(ratio_tx), 3), _fmt_num(_sd(ratio_tx), 3),
                _fmt_num(_mean(ratio_mm) - _mean(ratio_tx), 3)]])
    rep.w("  注：研究口径把「保持率」定义为「延迟 − 即时」（即保持量/衰减量）；"
          "比值口径（延迟/即时）一并列出以便描述，注意其未控制即时分的天花板效应。")
    r = emit_paired_block(rep, "两类词「保持差值」的配对比较（图文音 vs 纯文字）",
                          diff_mm, diff_tx, "图文音保持差值", "纯文字保持差值")
    return {"diff": r, "ratio_mm": _mean(ratio_mm), "ratio_tx": _mean(ratio_tx)}


def emit_battery(rep, rows, title, n_boot, seed):
    """对给定的数据子集跑完整套检验。"""
    rep.h1(title)
    sel_now = _by_time(rows, TIME_IMMEDIATE)
    sel_del = _by_time(rows, TIME_DELAYED)
    rep.w(f"即时 n = {len(sel_now)}；延迟 n = {len(sel_del)}；"
          f"轮次 = {'、'.join(sorted({r[K_ROUND] for r in rows})) or '—'}")

    emit_descriptives(rep, rows, TIME_IMMEDIATE)
    emit_descriptives(rep, rows, TIME_DELAYED)

    # H1 / H2
    for tpoint, tag in ((TIME_IMMEDIATE, "H1（即时后测）"), (TIME_DELAYED, "H2（延迟后测）")):
        rep.h2(f"{tag}：图文音词 vs 纯文字词 → 配对样本 t 检验")
        if not _by_time(rows, tpoint):
            rep.w(f"  跳过：无 {tpoint} 数据。")
            continue
        k, xs, ys = _paired_arrays(rows, tpoint, K_MT, K_TT)
        emit_paired_block(rep, f"{tag} · 总分（满分各 25）", xs, ys, "图文音_总分", "纯文字_总分")
        k, xs, ys = _paired_arrays(rows, tpoint, K_MA, K_TA)
        emit_paired_block(rep, f"{tag} · 接受性（满分各 15）", xs, ys, "图文音_接受性", "纯文字_接受性")
        k, xs, ys = _paired_arrays(rows, tpoint, K_MP, K_TP)
        emit_paired_block(rep, f"{tag} · 产出性（满分各 10）", xs, ys, "图文音_产出性", "纯文字_产出性")

    rep.h2("保持率：延迟 − 即时")
    emit_retention(rep, rows)

    rep.h2("H3：2×2 重复测量 ANOVA（呈现模式 × 知识维度）")
    for tpoint in (TIME_IMMEDIATE, TIME_DELAYED):
        if _by_time(rows, tpoint):
            emit_h3_anova(rep, rows, tpoint, n_boot, seed)
        else:
            rep.h3(f"H3 —— {tpoint}")
            rep.w(f"  跳过：无 {tpoint} 数据。")


def emit_h6(rep, rows):
    rep.h1("【5】H6：2×2 混合设计 ANOVA（呈现模式＝被试内 × 水平＝被试间）")
    rep.w("因变量：该时点的「模态总分」（图文音_总分 / 纯文字_总分，满分各 25）。")

    # 选择被试间因素：优先「水平」列；若缺失则退回「轮次」
    levels = OrderedDict()
    for r in rows:
        lv = (r.get(K_LEVEL) or "").strip()
        if lv:
            levels.setdefault(lv, 0)
            levels[lv] += 1
    factor_name = None
    if len(levels) >= 2:
        factor_name = K_LEVEL
        # 被试键 = (轮次, 匿名编码)，避免依赖对象身份
        factor_vals = {_subject_key(r): (r.get(K_LEVEL) or "").strip() for r in rows}
    else:
        rounds = OrderedDict()
        for r in rows:
            rounds.setdefault(r[K_ROUND], 0)
            rounds[r[K_ROUND]] += 1
        if len(rounds) >= 2:
            factor_name = K_ROUND
            factor_vals = {_subject_key(r): r[K_ROUND] for r in rows}
            rep.w("⚠ 未检测到 ≥2 个「水平」取值（responses.csv 的「水平」列缺失或全为空），"
                  "已退回使用「轮次」作为被试间因素（第一轮=专业生 / 第二轮=二外生）。")
            rep.w("  若需按真实「水平」分组，请在 responses.csv 中补齐「水平」列。")
        else:
            rep.w("跳过：数据中只有一个「水平」/「轮次」取值，无法做被试间比较。")
            rep.w("  2×2 混合设计 ANOVA 需要同时包含两轮（或两个水平组）的数据：")
            rep.w("    方案一：把两轮被试合并到同一张 responses.csv（轮次列区分），"
                  "并在「水平」列标注 专业生 / 二外生；")
            rep.w("    方案二：分别对两轮各跑一次本脚本（此时只报告被试内检验，即 H1/H2/H3）。")
            return None

    for tpoint in (TIME_IMMEDIATE, TIME_DELAYED):
        rep.h2(f"—— 时点：{tpoint} ——")
        sel = [r for r in rows if r[K_TIME] == tpoint]
        if not sel:
            rep.w(f"  跳过：无 {tpoint} 数据。")
            continue
        pairs = [(r[K_MT], r[K_TT]) for r in sel]
        groups = [factor_vals[_subject_key(r)] for r in sel]
        res = mixed_anova_2x2(pairs, groups)
        if not res["ok"]:
            rep.w(f"  跳过：{res['reason']}")
            continue
        rep.w(f"被试间因素：{factor_name}；各组人数：" +
              "、".join(f"{lab} n={n}" for lab, n in res["group_n"].items()) +
              f"；总 N = {res['n_total']}")
        if not res["balanced"]:
            rep.w("  ⚠ 各组人数不相等：本脚本采用加权均值口径（被试内部分等价于 SPSS Type III），"
                  "建议研究者用 Type III 平方和复核。")
        names = {"A": "呈现模式(A, 被试内)", "B": f"{factor_name}(B, 被试间)",
                 "AB": f"呈现模式 × {factor_name}(A×B)"}
        trows = []
        for k in ("A", "B", "AB"):
            e = res[k]
            trows.append([names[k], _fmt_num(e["SS"], 4), e["df"], _fmt_num(e["MS"], 4),
                          _fmt_num(e["F"], 4), _fmt_p(e["p"]), _fmt_num(e["eta2p"], 4)])
        trows.append(["误差(A×被试/组内)", _fmt_num(res["ss_errA"], 4), res["df_errA"],
                      _fmt_num(res["ss_errA"] / res["df_errA"], 4), "", "", ""])
        trows.append(["误差(被试/组内)", _fmt_num(res["ss_errB"], 4), res["df_errB"],
                      _fmt_num(res["ss_errB"] / res["df_errB"], 4), "", "", ""])
        rep.table(["效应", "SS", "df", "MS", "F", "p", "偏 η²"], trows)
        rep.w(f"  恒等式核对：SS_B + 误差(被试/组内) + SS_A + SS_A×B + 误差(A) 与 SS_总 的相对偏差 = "
              f"{res['identity_total']:.3e}（应为 0）")
        rep.w(f"  各水平组的模态增益（图文音 − 纯文字，满分差 −25~+25）：" +
              "、".join(f"{lab} M = {_fmt_num(res['D_g'][lab], 3)}（n = {res['group_n'][lab]}）"
                        for lab in res["groups"]) +
              f"；总 M = {_fmt_num(res['D_bar'], 3)}")
        rep.w("  各组内部的简单效应（图文音 vs 纯文字，配对 t）：")
        simple = []
        for lab in res["groups"]:
            r = res["simple_effects"][lab]
            if r["ok"]:
                simple.append([lab, r["n"], _fmt_num(r["mean_d"], 3), _fmt_num(r["dz"], 3),
                               _fmt_num(r["t"], 4), r["df"], _fmt_p(r["p"])])
            else:
                simple.append([lab, r["n"], "", "", "", "", r["reason"]])
        rep.table(["水平组", "n", "M(差值)", "d_z", "t", "df", "p"], simple)
        ab = res["AB"]
        rep.w(f"  交互效应解读：A×B 的 F = {_fmt_num(ab['F'], 4)}，p = {_fmt_p(ab['p'])}，"
              f"偏 η² = {_fmt_num(ab['eta2p'], 4)}。"
              + ("交互显著 → 模态效应随学习者水平变化（支持 H6 的边界条件假设）。"
                 if ab["p"] < 0.05 else
                 "交互不显著 → 未见「模态效应随水平变化」的证据。"))
        rep.w("  ⚠ 注意：把两轮被试放入同一个被试间因素，等价于把「专业生 vs 二外生」"
              "当作一个水平变量；两轮在词单版本（N3/N4）、施测时间与干预长度上亦不同，"
              "因此该交互的解释需谨慎（水平与轮次并非完全等同）。")
    return True


# ==============================================================================
# 7. 模板生成
# ==============================================================================

# 示例词表（取自《论文/02_实验设计/实验词单80词示例_N4版.md》的主题1/主题2 测试词单），
# 模态分配沿用该文件的「模态分配方案」草案：序号 1,4,6,7,9,12,14,16,17,20 为图文音。
_MM_INDEX = {1, 4, 6, 7, 9, 12, 14, 16, 17, 20}
EXAMPLE_WORDS = {
    "主题1": ["会話", "作文", "漢字", "質問", "練習", "留学生", "入学", "図書館", "習う", "覚える",
              "忘れる", "間違う", "答える", "通う", "難しい", "易しい", "眠い", "忙しい",
              "もうすぐ", "たいてい"],
    "主题2": ["玄関", "台所", "冷蔵庫", "洗濯", "掃除", "荷物", "財布", "鍵", "片付ける", "手伝う",
              "洗う", "届ける", "遅れる", "休む", "広い", "狭い", "明るい", "暗い",
              "だいたい", "ゆっくり"],
}


def example_bindings():
    rows = []
    for theme, words in EXAMPLE_WORDS.items():
        for idx, word in enumerate(words, start=1):
            mode = MODE_MM if idx in _MM_INDEX else MODE_TX
            rows.append([theme, idx, word, mode])
    return rows


def example_items(bindings_rows):
    """按口径生成 40 题骨架。

    每组（20 词）内部：k=0..4 认读、k=5..9 选义、k=10..14 听辨（各 1 分）；
    图文音组 k=15..17 写假名、k=18..19 填空；纯文字组 k=15..16 写假名、k=17..19 填空（各 2 分）。
    于是全卷：认读 10 / 选义 10 / 听辨 10 / 写假名 5 / 填空 5 = 40 题 50 分；
    每组接受性 15 分、产出性 10 分。
    """
    mm = [r for r in bindings_rows if r[3] == MODE_MM]
    tx = [r for r in bindings_rows if r[3] == MODE_TX]
    out = []
    no = 0
    for k in range(20):
        for grp, word in ((mm, mm[k][2]), (tx, tx[k][2])):
            no += 1
            code = f"A{no:02d}"
            if k < 5:
                itype = "认读"
            elif k < 10:
                itype = "选义"
            elif k < 15:
                itype = "听辨"
            elif grp is mm:
                itype = "写假名" if k < 18 else "填空"
            else:
                itype = "写假名" if k < 17 else "填空"
            dim = TYPE_TO_DIM[itype]
            pts = 1 if dim == DIM_REC else 2
            out.append([code, word, itype, dim, pts])
    return out


def write_templates(outdir):
    """生成三份 CSV 模板（含表头与示例行）。返回写出的文件路径列表。"""
    os.makedirs(outdir, exist_ok=True)
    b_rows = example_bindings()
    i_rows = example_items(b_rows)
    paths = []

    p = os.path.join(outdir, "bindings.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(BINDINGS_HEADER)
        w.writerows(b_rows)
    paths.append(p)

    p = os.path.join(outdir, "items.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(ITEMS_HEADER)
        w.writerows(i_rows)
    paths.append(p)

    codes = [r[0] for r in i_rows]
    ex_rows = []
    for ri, (code, rnd, tpoint, level) in enumerate(
            (("0521LX", "第一轮", TIME_IMMEDIATE, "专业生"),
             ("0521LX", "第一轮", TIME_DELAYED, "专业生"),
             ("0522WY", "第一轮", TIME_IMMEDIATE, "专业生"))):
        vals = []
        for j, c in enumerate(codes):
            pts = i_rows[j][4]
            # 示例作答：交替对/错（纯占位，务必替换为真实数据）
            vals.append(pts if (j + ri * 7) % 3 != 0 else 0)
        ex_rows.append([code, rnd, tpoint, level] + vals)
    p = os.path.join(outdir, "responses.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([K_CODE, K_ROUND, K_TIME, K_LEVEL] + codes)
        w.writerows(ex_rows)
    paths.append(p)
    return paths


# ==============================================================================
# 8. 主流程
# ==============================================================================

def load_and_validate(bindings_path, items_path):
    bindings, b_warns, _ = read_bindings(bindings_path)
    items, i_warns = read_items(items_path)
    info, v_warns = validate_items(items, bindings)
    return bindings, items, b_warns + i_warns + v_warns, info


def compute_scores(items, responses_path):
    item_codes = [it["题号"] for it in items]
    item_max = {it["题号"]: it["分值"] for it in items}
    responses = read_responses(responses_path, item_codes, item_max)
    rows, excluded, sinfo = build_scores(items, responses)
    return rows, excluded, sinfo, responses


def write_scores_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(SCORE_HEADER)
        for r in rows:
            w.writerow([_fmt_cell(r.get(c)) for c in SCORE_HEADER])


def write_stats_report(path, ctx):
    """写 stats.txt。ctx 由 build_report 组装。"""
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(ctx)


def build_report(rows, excluded, sinfo, responses, info_lines, warns, opts,
                 bindings_path, items_path, responses_path):
    rep = Report()
    rep.h1("词汇测试卷「4 子分计分 + 统计」报告")
    rep.w(f"生成时间   ：{_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    rep.w(f"bindings   ：{os.path.abspath(bindings_path)}")
    rep.w(f"items      ：{os.path.abspath(items_path)}")
    rep.w(f"responses  ：{os.path.abspath(responses_path)}")
    rep.w(f"Bootstrap  ：{opts.n_boot} 次重抽样，随机种子 = {opts.seed}（百分位法，被试重抽样）")
    rep.w(f"显著性水平 ：α = .05（双侧）")

    # ---------- 1 口径 ----------
    rep.h1("【1】计分口径")
    rep.w("本研究为被试内设计：呈现模式绑在「词」上（同一词对所有被试一致），")
    rep.w("每个主题词单 20 词 = 10 图文音 + 10 纯文字；测试覆盖主题1、主题2 各 20 词（一词一题）。")
    rep.w("全卷满分 50 分：接受性 30 分（认读 10 + 选义 10 + 听辨 10，每题 1 分）")
    rep.w("           ＋产出性 20 分（写假名 5 + 填空 5，每题 2 分）。")
    rep.w("按「模态 × 知识维度」交叉拆分为 4 个子分（每类词各 20 题 / 25 分）：")
    rep.table(["子分", "题量", "满分"],
              [[f"{MODE_MM}_{DIM_REC}", "15 题（认读5+选义5+听辨5）", "15"],
               [f"{MODE_MM}_{DIM_PRO}", "5 题（写假名/填空）", "10"],
               [f"{MODE_TX}_{DIM_REC}", "15 题（认读5+选义5+听辨5）", "15"],
               [f"{MODE_TX}_{DIM_PRO}", "5 题（写假名/填空）", "10"],
               ["合计", "40 题", "50"]])
    rep.w("派生量：图文音_总分 = 图文音_接受性 + 图文音_产出性（满分 25）")
    rep.w("        纯文字_总分 = 纯文字_接受性 + 纯文字_产出性（满分 25）")
    rep.w("        模态增益 = 图文音_总分 − 纯文字_总分（范围 −25 ~ +25，正值表示图文音词更优）")

    # ---------- 2 输入校验 ----------
    rep.h1("【2】输入校验")
    for s in info_lines:
        rep.w("  " + s)
    if warns:
        rep.w()
        rep.w("  告警：")
        for s in warns:
            rep.w("    ⚠ " + s)
    else:
        rep.w("  无告警。")

    # ---------- 3 样本与缺失 ----------
    rep.h1("【3】样本量与缺失值处理")
    rep.w(f"作答表聚合后的「被试 × 轮次 × 时点」记录数：{sinfo['n_raw_obs']}")
    rep.w(f"其中同一被试同时点有多行（A/B 卷分次录入）并被聚合的记录：{sinfo['n_multi_row']}")
    rep.w(f"完整记录（40 题全部有分）数：{sinfo['n_complete']}")
    rep.w(f"因缺失被剔除的整行记录数：{sinfo['n_excluded']}")
    rep.w()
    rep.w("缺失处理规则（整行剔除）：")
    rep.w("  1) 任一题号在该「被试 × 轮次 × 时点」内为空白/NA/非数字 → 该整行剔除，不参与计分；")
    rep.w("     （子分是求和量，缺题会造成系统性低估，故不做按比例补分）")
    rep.w("  2) 同一被试同一时点有多行时，按 (匿名编码, 轮次, 时点) 聚合：每个题号取首个非缺失值；")
    rep.w("     若同一题号出现两个不同得分，报告告警并保留首个；")
    rep.w("  3) 缺失即时数据的被试不进入 H1/H3；缺失延迟数据的不进入 H2；两者都有才进入保持率分析。")
    if excluded:
        rep.w()
        rep.w(f"被剔除的整行记录明细（最多列 50 条，共 {len(excluded)} 条）：")
        rep.table(["匿名编码", "轮次", "时点", "缺失题数", "缺失题号（前 5 个）"],
                  [[e[0], e[1], e[2], e[3], "、".join(e[4])] for e in excluded[:50]])
        codes = sinfo["codes_excluded"]
        rep.w(f"涉及被试共 {len(codes)} 人：{'、'.join(codes[:40])}"
              + ("……" if len(codes) > 40 else ""))
    else:
        rep.w("  没有被剔除的记录。")
    if responses["warns"]:
        rep.w()
        rep.w("  作答表解析告警：")
        for s in responses["warns"]:
            rep.w("    ⚠ " + s)

    rounds = list(OrderedDict.fromkeys(r[K_ROUND] for r in rows))
    rep.w()
    rep.w("各轮次 × 时点的可用样本量：")
    cnt_rows = []
    for rnd in rounds:
        for tpoint in (TIME_IMMEDIATE, TIME_DELAYED):
            n = sum(1 for r in rows if r[K_ROUND] == rnd and r[K_TIME] == tpoint)
            if n:
                cnt_rows.append([rnd, tpoint, n])
    for tpoint in (TIME_IMMEDIATE, TIME_DELAYED):
        n = sum(1 for r in rows if r[K_TIME] == tpoint)
        if n:
            cnt_rows.append(["（全部轮次合计）", tpoint, n])
    rep.table(["轮次", "时点", "n"], cnt_rows) if cnt_rows else rep.w("  无可用数据。")
    lv = OrderedDict()
    for r in rows:
        key = (r[K_ROUND], (r.get(K_LEVEL) or "（未填）"))
        lv[key] = lv.get(key, 0) + 1
    rep.w()
    rep.w("轮次 × 水平的记录分布：")
    rep.table(["轮次", "水平", "记录数"], [[a, b, c] for (a, b), c in lv.items()])

    # ---------- 4 分轮次 + 合并的检验 ----------
    rep.h1("【4】假设检验（按轮次分列；若有多轮，另附合并分析）")
    if not rows:
        rep.w("没有可用于分析的完整记录，无法进行统计检验。")
        return rep.text()
    if len(rounds) >= 1:
        for rnd in rounds:
            sub = [r for r in rows if r[K_ROUND] == rnd]
            lvs = sorted({(r.get(K_LEVEL) or "（未填）") for r in sub})
            emit_battery(rep, sub, f"【4.{rounds.index(rnd) + 1}】轮次：{rnd}"
                                   f"（水平：{'、'.join(lvs)}）", opts.n_boot, opts.seed)
    if len(rounds) > 1:
        rep.h1("【4.X】合并分析（全部轮次合并）")
        rep.w("⚠ 专业生与二外生的基线水平、词单版本（N3/N4）与施测时间不同，")
        rep.w("  合并分析仅作参考，主结论应以分轮次结果为准（H6 才是跨群体的正式检验）。")
        emit_battery(rep, rows, "【4.X】合并分析（全部轮次）", opts.n_boot, opts.seed)

    # ---------- 5 H6 ----------
    emit_h6(rep, rows)

    # ---------- 6 方法说明 ----------
    rep.h1("【6】方法说明与关键假设（供写作/复核用）")
    rep.w("1) 配对样本 t 检验：t = mean(d) / (sd(d)/√n)，df = n − 1，d = 图文音 − 纯文字；")
    rep.w("   sd 为样本标准差（ddof = 1）；Cohen's d_z = mean(d) / sd(d)（差值均数 ÷ 差值标准差）；")
    rep.w("   差值均数的 95% CI = mean(d) ± t_{.975, n−1} · sd(d)/√n。")
    rep.w("   p 值由 t 分布精确 CDF 计算：p = I_{df/(df+t²)}(df/2, ½)（正则化不完全 Beta 函数，")
    rep.w("   Numerical Recipes 连分式法），实现精度优于 1e-12。")
    rep.w("2) 2×2 重复测量 ANOVA（两因素均被试内）：用正交归一化对照法求 SS——")
    rep.w("   对照编码 A=(+1,+1,−1,−1)、B=(+1,−1,+1,−1)、A×B=(+1,−1,−1,+1)，Σc²=4；")
    rep.w("   SS_效应 = n·mean(L)²/Σc²，SS_误差 = Σ(L − mean(L))²/Σc²，L 为被试的对照分。")
    rep.w("   三个效应 df 均为 1；每个效应使用自己的「效应 × 被试」误差项，df = n − 1")
    rep.w("   （即 (n−1)(a−1)、(n−1)(b−1)、(n−1)(a−1)(b−1) 在 2×2 下同为 n−1）。")
    rep.w("   恒等式 SS_A + SS_B + SS_AB + ΣSS_误差 ≡ SS_被试内 已在报告中核对（偏差应为 0）。")
    rep.w("   ⚠ 三个误差项数值上一般并不相等（仅自由度相同）；本报告主结果采用「每效应匹配误差项」")
    rep.w("     （SPSS 默认、sphericity assumed），另附「合并误差」口径作对照。")
    rep.w("   ⚠ 三效应 df = 1 ⇒ 球形性假设自动满足，无需 Greenhouse-Geisser / Huynh-Feldt 校正。")
    rep.w("   ⚠ 偏 η² = SS_效应 / (SS_效应 + SS_误差)（等价于 F·df1/(F·df1 + df2)）。")
    rep.w("   ⚠ 知识维度主效应比较 15 分制与 10 分制原始分，数值本身不具实质意义，")
    rep.w("     只有 A×B 交互（= 两维度增益之差）是有量纲无关的实质结论。")
    rep.w("3) 2×2 混合设计 ANOVA（A 被试内、B 被试间，a = 2、b = 2 组）：")
    rep.w("   记 Δ_i = y_i(图文音) − y_i(纯文字)，Δ_g 为组均值，Δ = Σn_gΔ_g/N（加权总均值），")
    rep.w("   M_i 为被试均值，M_g 为组均值，GM 为总均值：")
    rep.w("     SS_B      = a·Σ_g n_g (M_g − GM)²                 df = b−1 = 1")
    rep.w("     SS_误差(B) = a·Σ_g Σ_i (M_i − M_g)²                 df = N − b   （被试(组内)效应）")
    rep.w("     SS_A      = N·Δ²/2                                df = a−1 = 1")
    rep.w("     SS_A×B    = Σ_g n_g (Δ_g − Δ)²/2                    df = (a−1)(b−1) = 1")
    rep.w("     SS_误差(A) = Σ_g Σ_i (Δ_i − Δ_g)²/2                  df = (a−1)(N−b) = N − b")
    rep.w("   其中 A 与 A×B 共用同一误差项「A × 被试(组内)」，故两者 df 相同（N − b）。")
    rep.w("   其中 1/2 因子来自 a = 2 时的恒等式 Σ_k (y_k − M_i)² = Δ_i²/2。")
    rep.w("   恒等式 SS_B + SS_误差(B) + SS_A + SS_A×B + SS_误差(A) ≡ SS_总 已在报告中核对。")
    rep.w("   等价关系（自检用）：SS_A×B = ½ × 「对差值 Δ 做单因素被试间 ANOVA」的组间 SS；")
    rep.w("   F_B 在平衡设计下 ⟺ 两组被试总分（图文音+纯文字）的合并方差独立样本 t² 。")
    rep.w("   ⚠ 不等组时上述分解不再正交（本脚本用加权均值口径，等价 SPSS Type III 的")
    rep.w("     被试内部分），建议研究者用 SPSS/Pingouin 的 Type III 平方和复核。")
    rep.w("4) Bootstrap：以被试为单位有放回重抽样（每次 n = 当前样本量），")
    rep.w("   统计量 = 「接受性模态增益 − 产出性模态增益」的均数；百分位法取 2.5 / 97.5 分位；")
    rep.w("   重抽样次数与随机种子见报告开头，固定种子可完全复现。")
    rep.w("5) 效应量：t 检验报告 d_z；ANOVA 报告偏 η²（0.01 小 / 0.06 中 / 0.14 大，Cohen 1988）。")
    rep.w("6) 未做（如需请另行处理）：正态性检验（Shapiro-Wilk）、Wilcoxon 符号秩备选检验、")
    rep.w("   Greenhouse-Geisser 校正、Type III 平方和、多重比较校正、协变量 ANCOVA（如认知负荷 Q11）。")

    # ---------- 7 逐被试子分表 ----------
    rep.h1("【7】附：逐被试 × 时点子分表（与 scores.csv 一致）")
    trows = []
    for r in rows:
        trows.append([r[K_CODE], r[K_ROUND], r.get(K_LEVEL) or "", r[K_TIME],
                      _fmt_cell(r[K_MA]), _fmt_cell(r[K_MP]), _fmt_cell(r[K_TA]),
                      _fmt_cell(r[K_TP]), _fmt_cell(r[K_MT]), _fmt_cell(r[K_TT]),
                      _fmt_cell(r[K_GAIN])])
    if trows:
        rep.table(["编码", "轮次", "水平", "时点", "图_接", "图_产", "纯_接", "纯_产",
                   "图_总", "纯_总", "增益"], trows)
    else:
        rep.w("  （无）")
    return rep.text()


def run_score(opts):
    bindings, items, warns, info_lines = load_and_validate(opts.bindings, opts.items)
    rows, excluded, sinfo, responses = compute_scores(items, opts.responses)
    outdir = opts.out or "."
    os.makedirs(outdir, exist_ok=True)
    scores_path = os.path.join(outdir, "scores.csv")
    stats_path = os.path.join(outdir, "stats.txt")
    write_scores_csv(scores_path, rows)
    text = build_report(rows, excluded, sinfo, responses, info_lines, warns, opts,
                        opts.bindings, opts.items, opts.responses)
    write_stats_report(stats_path, text)

    print(f"计分完成：")
    print(f"  题目数 {len(items)}，分值合计 {_fmt_cell(sum(i['分值'] for i in items))} 分")
    print(f"  完整记录 {sinfo['n_complete']} 条，剔除 {sinfo['n_excluded']} 条")
    print(f"  已写出：{os.path.abspath(scores_path)}")
    print(f"  已写出：{os.path.abspath(stats_path)}")
    if warns:
        print(f"  告警 {len(warns)} 条（详见 stats.txt）")
    print()
    print("关键结果速览：")
    for rnd in OrderedDict.fromkeys(r[K_ROUND] for r in rows):
        sub = [r for r in rows if r[K_ROUND] == rnd and r[K_TIME] == TIME_IMMEDIATE]
        if not sub:
            continue
        xs = [r[K_MT] for r in sub]
        ys = [r[K_TT] for r in sub]
        r = paired_t_test(xs, ys)
        if r["ok"]:
            print(f"  [{rnd}] H1 即时 总分：图文音 M = {r['mean_x']:.2f} vs 纯文字 M = "
                  f"{r['mean_y']:.2f}，t({r['df']}) = {r['t']:.3f}，p = {_fmt_p(r['p'])}，"
                  f"d_z = {r['dz']:.3f}（n = {r['n']}）")
    return 0


# ==============================================================================
# 9. 自测
# ==============================================================================

def _synth_items_and_bindings():
    b_rows = example_bindings()
    i_rows = example_items(b_rows)
    return b_rows, i_rows


def _synth_responses(b_rows, i_rows, spec, seed):
    """生成合成作答宽表。

    spec = [(轮次, 水平, n_subjects, theta_sd,
             mode_bonus_now, G_now, mode_bonus_delay, G_delay,
             theta_decay, decay_noise, delay_shift, prefix), ...]
    潜变量模型（logit 尺度）：
        logit p = θ_i·(时点衰减) + delay_shift(仅延迟) + dim_offset[dim] − difficulty_j
                  + (图文音 ? mode_bonus : 0)
                  + (图文音 ? +G·(接受性 ? +1 : −1) : 0)
    其中 mode_bonus 控制「模态主效应」，G 控制「模态 × 知识维度」交互
    （图文音在接受性上的增益比产出性高 2G）。交互只加在图文音一侧，
    以免它与模态主效应相互抵消。
    """
    rng = random.Random(seed)
    codes = [r[0] for r in i_rows]
    word_of = {r[0]: r[1] for r in i_rows}
    mode_of_word = {r[2]: r[3] for r in b_rows}
    dim_of = {r[0]: r[3] for r in i_rows}
    full_of = {r[0]: r[4] for r in i_rows}
    # 每题难度（固定，跨被试一致）
    diff = {c: rng.gauss(0.0, 0.35) for c in codes}
    dim_off = {DIM_REC: 1.05, DIM_PRO: -0.10}

    header_rows = []
    for (rnd, level, n_sub, theta_sd, mb_now, g_now, mb_delay, g_delay,
         decay, noise, delay_shift, prefix) in spec:
        for k in range(n_sub):
            code = f"{prefix}{k + 1:02d}"
            theta = rng.gauss(0.0, theta_sd)
            for tpoint in (TIME_IMMEDIATE, TIME_DELAYED):
                now = (tpoint == TIME_IMMEDIATE)
                th = theta if now else theta * decay + rng.gauss(0.0, noise)
                shift = 0.0 if now else delay_shift
                mb = mb_now if now else mb_delay
                g = g_now if now else g_delay
                vals = []
                for c in codes:
                    mode = mode_of_word[word_of[c]]
                    dim = dim_of[c]
                    sign = 1.0 if dim == DIM_REC else -1.0
                    bonus = 0.0
                    if mode == MODE_MM:
                        bonus = mb + g * sign
                    z = th + shift + bonus + dim_off[dim] - diff[c]
                    p = 1.0 / (1.0 + math.exp(-z))
                    vals.append(full_of[c] if rng.random() < p else 0)
                header_rows.append([code, rnd, tpoint, level] + vals)
    return header_rows, codes


def _pick_writable_dir(preferred=None):
    """挑一个真正可写的自测工作目录（某些沙箱环境禁止写系统临时目录）。"""
    cands = []
    if preferred:
        cands.append(preferred)
    try:
        cands.append(tempfile.mkdtemp(prefix="score_vocab_selftest_"))
    except OSError:
        pass
    cands.append(os.path.join(os.getcwd(), "_score_vocab_selftest"))
    for d in cands:
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, ".write_probe")
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write("ok")
            os.remove(probe)
            return d
        except OSError:
            continue
    raise DataError("找不到可写的自测工作目录，请用 `--out <目录>` 指定一个可写目录。")


def run_selftest(workdir=None):
    print("=" * 78)
    print("词汇测试卷计分脚本 · 自测（--selftest）")
    print("=" * 78)
    checks = []

    def check(label, cond, detail=""):
        ok = bool(cond)
        checks.append((label, ok, detail))
        print(f"  [{'OK  ' if ok else 'FAIL'}] {label}" + (f"   {detail}" if detail else ""))
        return ok

    # ---------- 步骤 0：数值函数精度 ----------
    print("\n[步骤 0] 分布函数精度自检")
    p = t_two_sided_p(2.228138852, 10)
    check("t 双侧 p：t=2.228138852, df=10 → 0.05（容差 1e-6）",
          abs(p - 0.05) < 1e-6, f"实得 p = {p:.12f}")
    tc = t_crit(0.05, 10)
    check("t 临界值：t_{.975,10} ≈ 2.228138852（容差 1e-6）",
          abs(tc - 2.228138852) < 1e-6, f"实得 t_crit = {tc:.12f}")
    tc_big = t_crit(0.05, 10 ** 7)
    check("t 临界值大 df 极限 ≈ 1.959964（容差 1e-4）",
          abs(tc_big - 1.959964) < 1e-4, f"实得 t_crit = {tc_big:.9f}")
    pf = f_sf(4.964602744, 1, 10)
    check("F 右尾 p：F=4.964602744, df=(1,10) → 0.05（容差 1e-6）",
          abs(pf - 0.05) < 1e-6, f"实得 p = {pf:.12f}")
    check("F 与 t 的一致性：F = t² → p 相同",
          abs(f_sf(2.228138852 ** 2, 1, 10) - t_two_sided_p(2.228138852, 10)) < 1e-9)

    # ---------- 步骤 1：生成合成数据并写出三份 CSV ----------
    print("\n[步骤 1] 生成合成数据（固定随机种子，可复现）")
    seed = 20260901
    b_rows, i_rows = _synth_items_and_bindings()
    # 第一轮：30 名专业生，模态效应量 d_z ≈ 0.5，且接受性增益 > 产出性增益
    # 第二轮：20 名二外生，模态效应较弱、且维度不均衡程度更小（用于演示 H6 交互）
    spec = [
        ("第一轮", "专业生", 30, 0.62, 0.10, 0.50, 0.22, 0.40, 0.90, 0.28, -0.55, "R1S"),
        ("第二轮", "二外生", 20, 0.80, 0.05, 0.35, 0.12, 0.28, 0.85, 0.32, -0.70, "R2S"),
    ]
    resp_rows, codes = _synth_responses(b_rows, i_rows, spec, seed)
    print(f"  题目数 {len(i_rows)}；被试数 {sum(s[2] for s in spec)}"
          f"（第一轮 30 / 第二轮 20）× 2 时点；随机种子 = {seed}")

    workdir = _pick_writable_dir(workdir)
    print(f"  自测工作目录：{os.path.abspath(workdir)}")

    bp = os.path.join(workdir, "bindings.csv")
    ip = os.path.join(workdir, "items.csv")
    rp = os.path.join(workdir, "responses.csv")
    with open(bp, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(BINDINGS_HEADER)
        w.writerows(b_rows)
    with open(ip, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(ITEMS_HEADER)
        w.writerows(i_rows)
    with open(rp, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([K_CODE, K_ROUND, K_TIME, K_LEVEL] + codes)
        w.writerows(resp_rows)

    # 顺手验证：模板 CSV 能被脚本自己读回来并校验通过（模板-校验往返）
    tdir = os.path.join(workdir, "template")
    write_templates(tdir)
    try:
        t_b, t_i, t_warns, t_info = load_and_validate(os.path.join(tdir, "bindings.csv"),
                                                      os.path.join(tdir, "items.csv"))
        check("--template 生成的 bindings.csv/items.csv 能通过校验（模板往返）", True,
              f"{len(t_i)} 题 / {len(t_b)} 词")
    except DataError as exc:
        check("--template 生成的 bindings.csv/items.csv 能通过校验（模板往返）", False, str(exc))

    # ---------- 步骤 2：跑全流程 ----------
    print("\n[步骤 2] 走完整计分 + 统计流程")
    bindings, items, warns, info_lines = load_and_validate(bp, ip)
    rows, excluded, sinfo, responses = compute_scores(items, rp)
    print(f"  题目 {len(items)} 题，分值合计 {_fmt_cell(sum(i['分值'] for i in items))} 分")
    print(f"  完整记录 {sinfo['n_complete']} 条，剔除 {sinfo['n_excluded']} 条")
    check("合成数据全部记录完整（无缺失剔除）", sinfo["n_excluded"] == 0 and sinfo["n_complete"] == 100,
          f"complete={sinfo['n_complete']}, excluded={sinfo['n_excluded']}")
    check("计分无口径告警", len(warns) == 0, "；".join(warns) if warns else "")
    # 手工核对一个子分
    r0 = [r for r in rows if r[K_CODE] == "R1S01" and r[K_TIME] == TIME_IMMEDIATE][0]
    raw = [x for x in resp_rows if x[0] == "R1S01" and x[2] == TIME_IMMEDIATE][0][4:]
    mm_rec = sum(raw[j] for j, c in enumerate(codes)
                 if items[j]["呈现模式"] == MODE_MM and items[j]["维度"] == DIM_REC)
    check("子分拆分手工核对（R1S01 即时 图文音_接受性）",
          abs(r0[K_MA] - mm_rec) < 1e-9, f"脚本 = {r0[K_MA]}，手工 = {mm_rec}")
    check("总分口径核对：图文音_总分 = 接受性 + 产出性",
          abs(r0[K_MT] - (r0[K_MA] + r0[K_MP])) < 1e-9 and abs(r0[K_GAIN] - (r0[K_MT] - r0[K_TT])) < 1e-9)

    r1 = [r for r in rows if r[K_ROUND] == "第一轮" and r[K_TIME] == TIME_IMMEDIATE]
    xs = [r[K_MT] for r in r1]
    ys = [r[K_TT] for r in r1]

    # ---------- 步骤 3：H1/H2 方向与效应量 ----------
    print("\n[步骤 3] H1 / H2 配对 t 检验")
    h1 = paired_t_test(xs, ys)
    print(f"  H1 即时：图文音 M = {h1['mean_x']:.3f} (SD {h1['sd_x']:.3f}) vs "
          f"纯文字 M = {h1['mean_y']:.3f} (SD {h1['sd_y']:.3f})")
    print(f"          t({h1['df']}) = {h1['t']:.4f}, p = {_fmt_p(h1['p'])}, "
          f"d_z = {h1['dz']:.4f}, 差值 95% CI = [{h1['ci_lo']:.3f}, {h1['ci_hi']:.3f}]")
    check("H1：图文音_总分 > 纯文字_总分", h1["mean_x"] > h1["mean_y"],
          f"{h1['mean_x']:.3f} > {h1['mean_y']:.3f}")
    check("H1：配对 t 检验显著（p < .05）", h1["p"] < 0.05, f"p = {_fmt_p(h1['p'])}")
    check("H1：效应量 d_z ≈ 0.5（落在 0.30 ~ 0.80）", 0.30 <= h1["dz"] <= 0.80,
          f"d_z = {h1['dz']:.4f}")
    check("H1：差值 95% CI 不包含 0", h1["ci_lo"] > 0, f"CI = [{h1['ci_lo']:.3f}, {h1['ci_hi']:.3f}]")

    r1d = [r for r in rows if r[K_ROUND] == "第一轮" and r[K_TIME] == TIME_DELAYED]
    h2 = paired_t_test([r[K_MT] for r in r1d], [r[K_TT] for r in r1d])
    print(f"  H2 延迟：图文音 M = {h2['mean_x']:.3f} vs 纯文字 M = {h2['mean_y']:.3f}，"
          f"t({h2['df']}) = {h2['t']:.4f}, p = {_fmt_p(h2['p'])}, d_z = {h2['dz']:.4f}")
    check("H2（延迟）：图文音 > 纯文字", h2["mean_x"] > h2["mean_y"],
          f"{h2['mean_x']:.3f} > {h2['mean_y']:.3f}")

    # ---------- 步骤 4：H3 重复测量 ANOVA + 自洽性 ----------
    print("\n[步骤 4] H3 2×2 重复测量 ANOVA")
    mat = [(r[K_MA], r[K_MP], r[K_TA], r[K_TP]) for r in r1]
    an = rm_anova_2x2(mat)
    eA, eB, eAB = an["effects"]["A"], an["effects"]["B"], an["effects"]["AB"]
    print(f"  呈现模式(A)   F(1,{eA['df_error']}) = {eA['F']:.4f}, p = {_fmt_p(eA['p'])}, "
          f"偏 η² = {eA['eta2p']:.4f}")
    print(f"  知识维度(B)   F(1,{eB['df_error']}) = {eB['F']:.4f}, p = {_fmt_p(eB['p'])}, "
          f"偏 η² = {eB['eta2p']:.4f}")
    print(f"  模态×维度(AB) F(1,{eAB['df_error']}) = {eAB['F']:.4f}, p = {_fmt_p(eAB['p'])}, "
          f"偏 η² = {eAB['eta2p']:.4f}")
    ga = an["gain_receptive"]
    gp = an["gain_productive"]
    print(f"  模态增益：接受性 M = {_mean(ga):.3f}，产出性 M = {_mean(gp):.3f}，"
          f"差值 M = {_mean(an['gain_diff']):.3f}")
    check("H3：接受性的模态增益 > 产出性的模态增益（交互方向）", _mean(ga) > _mean(gp),
          f"{_mean(ga):.3f} > {_mean(gp):.3f}")
    check("H3：A×B 交互显著（p < .05）", eAB["p"] < 0.05, f"p = {_fmt_p(eAB['p'])}")
    check("SS 分解恒等式：Σ(效应 + 误差) ≡ SS_被试内（相对偏差 < 1e-9）",
          an["identity_within"] < 1e-9, f"偏差 = {an['identity_within']:.3e}")
    check("SS 分解恒等式：SS_被试内 + SS_被试间 ≡ SS_总（相对偏差 < 1e-9）",
          an["identity_total"] < 1e-9, f"偏差 = {an['identity_total']:.3e}")
    # F_A 必须等于「模态总分」配对 t 的平方
    tA = paired_t_test([r[K_MT] for r in r1], [r[K_TT] for r in r1])
    check("自洽性：F(呈现模式) = t²（模态总分配对 t）",
          abs(eA["F"] - tA["t"] ** 2) < 1e-6, f"F = {eA['F']:.8f}, t² = {tA['t'] ** 2:.8f}")
    # F_B 必须等于「维度总分差」配对 t 的平方
    tB = paired_t_test([r[K_MA] + r[K_TA] for r in r1], [r[K_MP] + r[K_TP] for r in r1])
    check("自洽性：F(知识维度) = t²（维度总分配对 t）",
          abs(eB["F"] - tB["t"] ** 2) < 1e-6, f"F = {eB['F']:.8f}, t² = {tB['t'] ** 2:.8f}")
    # F_AB 必须等于「增益差值」配对 t 的平方
    tAB = paired_t_test(ga, gp)
    check("自洽性：F(A×B) = t²（两维度模态增益差值的配对 t）",
          abs(eAB["F"] - tAB["t"] ** 2) < 1e-6, f"F = {eAB['F']:.8f}, t² = {tAB['t'] ** 2:.8f}")

    # ---------- 步骤 5：Bootstrap ----------
    print("\n[步骤 5] Bootstrap 95% CI（两维度模态增益差值，被试重抽样）")
    bs = bootstrap_mean_ci(an["gain_diff"], n_boot=5000, seed=12345)
    print(f"  点估计 = {bs['mean']:.4f}，95% CI = [{bs['lo']:.4f}, {bs['hi']:.4f}]"
          f"（{bs['n_boot']} 次，seed = {bs['seed']}，n = {bs['n']}）")
    check("Bootstrap 95% CI 下限 > 0（模态收益在维度间不均衡）", bs["lo"] > 0,
          f"CI = [{bs['lo']:.4f}, {bs['hi']:.4f}]")
    bs2 = bootstrap_mean_ci(an["gain_diff"], n_boot=5000, seed=12345)
    check("Bootstrap 可复现（同种子结果完全一致）",
          bs["lo"] == bs2["lo"] and bs["hi"] == bs2["hi"])

    # ---------- 步骤 6：混合设计 ANOVA ----------
    print("\n[步骤 6] H6 2×2 混合设计 ANOVA（呈现模式 被试内 × 水平 被试间）")
    sel = [r for r in rows if r[K_TIME] == TIME_IMMEDIATE]
    pairs = [(r[K_MT], r[K_TT]) for r in sel]
    groups = [(r.get(K_LEVEL) or "") for r in sel]
    mx = mixed_anova_2x2(pairs, groups)
    check("混合 ANOVA 可运行（2 组、N > 2）", mx.get("ok", False),
          mx.get("reason", f"N = {mx.get('n_total')}"))
    if mx.get("ok"):
        print(f"  呈现模式(A)      F(1,{mx['A']['df_error']}) = {mx['A']['F']:.4f}, "
              f"p = {_fmt_p(mx['A']['p'])}, 偏 η² = {mx['A']['eta2p']:.4f}")
        print(f"  水平(B)          F(1,{mx['B']['df_error']}) = {mx['B']['F']:.4f}, "
              f"p = {_fmt_p(mx['B']['p'])}, 偏 η² = {mx['B']['eta2p']:.4f}")
        print(f"  模态×水平(A×B)   F(1,{mx['AB']['df_error']}) = {mx['AB']['F']:.4f}, "
              f"p = {_fmt_p(mx['AB']['p'])}, 偏 η² = {mx['AB']['eta2p']:.4f}")
        print(f"  各组模态增益：" + "、".join(
            f"{lab} M = {mx['D_g'][lab]:.3f}（n = {mx['group_n'][lab]}）" for lab in mx["groups"]))
        check("混合 ANOVA：df 口径正确（A/AB 误差 df = A/AB 自由度分母 = N − b）",
              mx["A"]["df_error"] == mx["n_total"] - 2 and mx["AB"]["df_error"] == mx["n_total"] - 2
              and mx["A"]["df"] == 1 and mx["B"]["df"] == 1 and mx["AB"]["df"] == 1,
              f"A:df_err={mx['A']['df_error']}, AB:df_err={mx['AB']['df_error']}, N={mx['n_total']}")
        check("混合 ANOVA：恒等式 SS_B+误差(B)+SS_A+SS_AB+误差(A) ≡ SS_总（偏差 < 1e-9）",
              mx["identity_total"] < 1e-9, f"偏差 = {mx['identity_total']:.3e}")
        # 独立编码核对：A×B 的被试间部分 = 对差值 Δ 的单因素被试间 ANOVA
        grp_vals = {}
        for (p, g) in zip(pairs, groups):
            grp_vals.setdefault(g, []).append(p[0] - p[1])
        ow = one_way_anova_between([grp_vals[g] for g in mx["groups"]])
        check("混合 ANOVA 独立编码核对：SS_A×B = ½ × (对差值 Δ 的被试间 SS)",
              ow.get("ok") and abs(mx["AB"]["SS"] - 0.5 * ow["SS_between"]) < 1e-9,
              f"脚本 SS_AB = {mx['AB']['SS']:.8f}, ½×独立编码 = {0.5 * ow['SS_between']:.8f}"
              if ow.get("ok") else "单因素 ANOVA 不可用")
        check("混合 ANOVA 独立编码核对：F_A×B = 对差值 Δ 的被试间 F",
              ow.get("ok") and abs(mx["AB"]["F"] - ow["F"]) < 1e-8,
              f"F_AB = {mx['AB']['F']:.8f}, 独立 F = {ow['F']:.8f}" if ow.get("ok") else "")
        # 独立编码核对：F_B = 两组总分的合并方差独立样本 t²
        gv = {}
        for (p, g) in zip(pairs, groups):
            gv.setdefault(g, []).append(sum(p))
        labs = mx["groups"]
        a1, a2 = gv[labs[0]], gv[labs[1]]
        n1, n2 = len(a1), len(a2)
        sp2 = ((n1 - 1) * _var(a1) + (n2 - 1) * _var(a2)) / (n1 + n2 - 2)
        tt = (_mean(a1) - _mean(a2)) / math.sqrt(sp2 * (1.0 / n1 + 1.0 / n2))
        check("混合 ANOVA 独立编码核对：F_B = 两组总分的合并方差 t²",
              abs(mx["B"]["F"] - tt ** 2) < 1e-8,
              f"F_B = {mx['B']['F']:.8f}, t² = {tt ** 2:.8f}")
        check("混合 ANOVA 简单效应：各组内部配对 t 的误差 df = n_g − 1",
              all(mx["simple_effects"][lab]["df"] == mx["group_n"][lab] - 1 for lab in labs))

    # ---------- 步骤 7：写盘并检查产物 ----------
    print("\n[步骤 7] 写出 scores.csv / stats.txt 并检查")
    opts = argparse.Namespace(bindings=bp, items=ip, responses=rp, out=workdir,
                              n_boot=5000, seed=12345)
    rc = run_score(opts)
    sp = os.path.join(workdir, "scores.csv")
    stp = os.path.join(workdir, "stats.txt")
    check("scores.csv 已生成", os.path.exists(sp))
    check("stats.txt 已生成", os.path.exists(stp))
    with open(sp, "r", encoding="utf-8-sig", newline="") as fh:
        rdr = list(csv.reader(fh))
    check("scores.csv 表头与口径完全一致", rdr[0] == SCORE_HEADER,
          "、".join(rdr[0]))
    check("scores.csv 行数 = 被试数 × 2 时点（50 × 2 = 100）", len(rdr) - 1 == 100,
          f"实得 {len(rdr) - 1} 行")
    with open(stp, "r", encoding="utf-8") as fh:
        body = fh.read()
    for kw in ("【1】计分口径", "【3】样本量与缺失值处理", "H1（即时后测）", "H3：2×2 重复测量 ANOVA",
               "H6：2×2 混合设计 ANOVA", "Bootstrap 95% CI", "【6】方法说明与关键假设"):
        check(f"stats.txt 含章节「{kw}」", kw in body)

    # ---------- 步骤 8：错误处理 ----------
    print("\n[步骤 8] 错误处理自检（分值不符 / 缺列 / 文件缺失）")
    bad_dir = os.path.join(workdir, "bad")
    os.makedirs(bad_dir, exist_ok=True)
    bad_items = os.path.join(bad_dir, "items_bad_score.csv")
    with open(bad_items, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(ITEMS_HEADER)
        for row in i_rows:
            r = list(row)
            if r[0] == "A01":
                r[4] = 2          # 把 1 分题改成 2 分 → 合计 51
            w.writerow(r)
    try:
        load_and_validate(bp, bad_items)
        check("分值合计 ≠ 50 时应报错", False, "未报错")
    except DataError as exc:
        check("分值合计 ≠ 50 时应报错", "50" in str(exc), str(exc).splitlines()[0])

    bad_items2 = os.path.join(bad_dir, "items_bad_modesplit.csv")
    with open(bad_items2, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(ITEMS_HEADER)
        flipped = 0
        for row in i_rows:
            r = list(row)
            if r[2] == "听辨" and flipped < 2:
                r[3] = DIM_PRO   # 维度与题型矛盾
                flipped += 1
            w.writerow(r)
    try:
        load_and_validate(bp, bad_items2)
        check("维度与题型矛盾时应报错", False, "未报错")
    except DataError as exc:
        check("维度与题型矛盾时应报错", "矛盾" in str(exc), str(exc).splitlines()[0])

    bad_resp = os.path.join(bad_dir, "responses_missing_col.csv")
    with open(bad_resp, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([K_CODE, K_ROUND, K_TIME] + codes[:30])   # 少了 10 个题号列
        w.writerow(["X001", "第一轮", TIME_IMMEDIATE] + [1] * 30)
    try:
        compute_scores(items, bad_resp)
        check("作答表缺题号列时应报错", False, "未报错")
    except DataError as exc:
        check("作答表缺题号列时应报错", "缺少以下题号列" in str(exc), str(exc).splitlines()[0])

    try:
        load_and_validate(os.path.join(bad_dir, "不存在.csv"), ip)
        check("输入文件缺失时应报错", False, "未报错")
    except DataError as exc:
        check("输入文件缺失时应报错", "找不到文件" in str(exc), str(exc).splitlines()[0])

    # 缺列
    bad_bind = os.path.join(bad_dir, "bindings_missing_col.csv")
    with open(bad_bind, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["主题", "序号", "单词"])
        w.writerow(["主题1", 1, "会話"])
    try:
        load_and_validate(bad_bind, ip)
        check("绑定表缺「呈现模式」列时应报错", False, "未报错")
    except DataError as exc:
        check("绑定表缺「呈现模式」列时应报错", "缺少必需的列" in str(exc), str(exc).splitlines()[0])

    # ---------- 汇总 ----------
    print("\n" + "=" * 78)
    n_fail = sum(1 for _, ok, _ in checks if not ok)
    print(f"自测断言：共 {len(checks)} 条，通过 {len(checks) - n_fail} 条，失败 {n_fail} 条")
    if n_fail:
        print("失败项：")
        for label, ok, detail in checks:
            if not ok:
                print(f"  - {label}  {detail}")
        print("FAIL")
        return 1
    print(f"产物目录：{os.path.abspath(workdir)}")
    print("PASS")
    return 0


# ==============================================================================
# 10. 命令行入口
# ==============================================================================

def build_parser():
    p = argparse.ArgumentParser(
        prog="score_vocab_test.py",
        description="词汇测试卷「4 子分计分 + 统计」脚本（纯标准库）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=("示例：\n"
                "  python score_vocab_test.py                     # 用当前目录的三份 CSV 计分\n"
                "  python score_vocab_test.py --template ./模板    # 生成三份 CSV 模板\n"
                "  python score_vocab_test.py --selftest          # 自测并断言，结尾输出 PASS\n"))
    p.add_argument("command", nargs="?", default="score",
                   choices=["score", "template", "selftest"],
                   help="子命令：score（默认）/ template / selftest")
    p.add_argument("--bindings", default="bindings.csv",
                   help="词-模态绑定表路径（默认当前目录 bindings.csv）")
    p.add_argument("--items", default="items.csv",
                   help="题目表路径（默认当前目录 items.csv）")
    p.add_argument("--responses", default="responses.csv",
                   help="作答表路径（默认当前目录 responses.csv）")
    p.add_argument("--out", default=".", help="输出目录（默认当前目录）")
    p.add_argument("--n-boot", type=int, default=5000, help="Bootstrap 重抽样次数（默认 5000）")
    p.add_argument("--seed", type=int, default=12345, help="Bootstrap 随机种子（默认 12345）")
    p.add_argument("--template", nargs="?", const="", metavar="DIR",
                   help="在 DIR 生成三份 CSV 空模板（含表头与示例行）；省略 DIR 时用 --out")
    p.add_argument("--selftest", action="store_true",
                   help="用内置合成数据跑通全流程并断言，结尾输出 PASS"
                        "（产物写入系统临时目录；不可写时回退到当前目录 _score_vocab_selftest/）")
    return p


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.selftest or args.command == "selftest":
            return run_selftest(args.out if args.out and args.out != "." else None)
        if args.template is not None or args.command == "template":
            tdir = args.template if args.template else args.out
            paths = write_templates(tdir)
            print("已生成模板（UTF-8 with BOM，含表头与示例行）：")
            for pth in paths:
                print(f"  {os.path.abspath(pth)}")
            print()
            print("提示：示例行为可用的骨架——请在保留列名与结构的前提下替换为真实词表/题表/作答。")
            print("      items.csv 的 40 题骨架与 bindings.csv 的模态分配已按口径配平")
            print("      （每组接受性 15 分 / 产出性 10 分，全卷 50 分）。")
            return 0
        if args.n_boot < 10:
            raise DataError(f"--n-boot 至少为 10，当前为 {args.n_boot}。")
        if not (1.0 <= args.seed < 2 ** 31):
            raise DataError(f"--seed 需在 [1, 2^31) 范围内，当前为 {args.seed}。")
        return run_score(args)
    except DataError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("已中断。", file=sys.stderr)
        return 130
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
