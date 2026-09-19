# -*- coding: utf-8 -*-
"""问卷定义（科研用，措辞冻结）。

来源：`问卷/` 目录下的五份「建卷清单」与《问卷总表（整理版）》，
逐题照抄原文，**不得随意改动措辞**——措辞变更必须同时提升 `version`，
否则不同批次的数据将不可比。

结构说明：
- 每份问卷 = 一个 form（卷 2 / 卷 4 各有两个版本，分开计分）
- `code` 内部标识；`number` + `name` 组成展示名（「卷N 名称」）
- `pages[].items[]`：题型 text / textarea / radio / matrix
  - matrix 的每一行有稳定 key：`{item_key}_r{行号}`（行号跨块连续，用于反向计分）
- `dimensions`：量表-题号对照（分析计分用），`reverse` 列出需反向计分的条目 key
- 计分口径：**维度分 = 该维度条目均值**（不做简单加总）

⚠️ 修改本文件后请同步核对 `问卷/问卷总表（整理版）.md` 的第三节与第四节。

版本沿革（`VERSION` 变更 = 学生可见措辞变更，必须留痕）：
- `2026-08`：按五份《建卷清单》落笔
- `2026-09`：按权威源《问卷设计（SDT与学习效果）.md》统一（总表规定「条目原文有改动以《问卷设计》为准」）：
  · BPNS 第 1/4/13 行补回【主语】（卷1 前测=「我的日语学习」，卷2 后测两版=网站名）
    —— 此前卷2 实验组缺主语、对照组有主语，两组作答情境不一致
  · BPNS 第 10/14 行补回括号举例（如阶段提升、成就解锁 / 如社区发帖、评论）
  · 卷3 开放题补回「你觉得」
  以上变更发生在 **T0 前测尚未施测**之前，无历史数据受影响
"""

VERSION = "2026-09"

# ── 常用量表标签 ──
AGREE5 = {"min": 1, "max": 5, "min_label": "完全不符合", "max_label": "完全符合"}
EMOTION5 = {"min": 1, "max": 5, "min_label": "几乎没有", "max_label": "非常强烈"}
SUS5 = {"min": 1, "max": 5, "min_label": "非常不同意", "max_label": "非常同意"}
CHANGE5 = {
    "min": 1, "max": 5,
    "labels": {
        1: "明显下降", 2: "略有下降", 3: "没有变化", 4: "略有提高", 5: "明显提高",
    },
}

# ── 复用条目（前后测必须完全一致的措辞）──
def bpns_blocks(subject: str) -> list:
    """BPNS 三块（自主/胜任/归属），按《问卷设计（SDT与学习效果）》3.1 权威条目生成。

    ⚠️ 两条措辞纪律（改动前先跑 dev_tools/check_questionnaire_design.py）：
    1. 第 1/4/13 行的【主语】按组别/时点替换——卷1 前测在平台使用**之前**，
       主语为「我的日语学习」；卷2 后测两版均为《多模态日语词汇学习网站》。
       少写主语会让两组作答情境不一致（曾出过该问题）。
    2. 第 10/14 行的括号举例（如阶段提升、成就解锁 / 如社区发帖、评论）
       **属于条目原文**，不是注释，删掉即条目含义变窄。
    """
    return [
        {
            "title": "自主性",
            "rows": [
                f"在{subject}中，我可以按照自己喜欢的方式安排词汇学习",
                "我能自由决定先学什么、后学什么（如选择主题、新词或复习）",
                "我的学习节奏是由我自己掌控的",
                f"在{subject}中，我有机会表达自己的意见和想法",
                "我觉得自己被要求按照固定的方式学习，没有选择的余地",
                "很多时候我感到自己不得不学习，而不是自愿学习",
            ],
        },
        {
            "title": "胜任感",
            "rows": [
                "我确信自己能掌握所学的日语词汇",
                "我对自己记住单词的能力有信心",
                "完成每天的学习/复习任务让我很有成就感",
                "我能看到自己的进步（如阶段提升、成就解锁），这让我觉得自己是有能力的",
                "有些词汇任务我觉得自己应付不来",
                "我常常担心自己学不会这些单词",
            ],
        },
        {
            "title": "归属感",
            "rows": [
                f"在{subject}中，我觉得自己是学习群体的一员",
                "和同学交流学习心得（如社区发帖、评论）时，我感到亲近",
                "我的发言或分享能得到他人的回应和认可",
                "学习时我经常感到孤单",
                "我觉得自己在学习群体中是孤立无援的",
                "即使没有直接互动，我也能感受到来自学习社群的支持",
            ],
        },
    ]


SITE = "《多模态日语词汇学习网站》"
Q1_SUBJECT_PRE = "我的日语学习"          # 卷1 前测：平台使用之前
Q1_SUBJECT_POST = SITE                   # 卷2 后测：两组均以网站为主语
Q1_BLOCKS_PRE = bpns_blocks(Q1_SUBJECT_PRE)
Q1_BLOCKS_EXP = bpns_blocks(Q1_SUBJECT_POST)
Q1_BLOCKS_CTRL = bpns_blocks(Q1_SUBJECT_POST)
Q1_REVERSE_ROWS = [5, 6, 11, 12, 16, 17]

Q4_ROWS_COMMON = ["感兴趣的", "愉悦的", "兴奋的", "有活力的", "自豪的",
                  "焦虑的", "沮丧的", "紧张的", "厌倦的", "烦躁的"]

Q7_EFFICACY_ROWS = [
    "我对自己记住日语单词有信心",
    "面对新单词，我敢于尝试记忆",
    "即使在陌生语境中，我也能根据学过的单词推断意思",
    "我相信只要坚持，我的日语词汇一定能进步",
]

Q12A_ROWS = [
    "我对学习日语词汇的兴趣程度（1 = 完全没兴趣 → 5 = 非常有兴趣）",
    "我背记日语单词的效率（1 = 很低 → 5 = 很高）",
]
Q12B_ROWS = [
    "使用《多模态日语词汇学习网站》后，我学习日语词汇的兴趣",
    "使用《多模态日语词汇学习网站》后，我背记日语单词的效率",
]

Q2_REASON_ROWS = [
    "老师或学校要求我这样做",
    "不学习的话我会落后于同学或受到批评",
    "这是课程/任务的一部分，不得不完成",
    "不认真学习我会感到内疚",
    "我想证明自己不比别人差",
    "不好好学习我会觉得自己很没用",
    "学习日语词汇对我很重要",
    "我想真正提高自己的日语能力",
    "这对我的考试和未来发展有用",
    "学习词汇本身很有趣",
    "探索新单词让我感到快乐",
    "我很享受在《多模态日语词汇学习网站》中学习的时光",
]
Q3_IMI_ROWS = [
    "使用《多模态日语词汇学习网站》学习词汇让我感到愉快",
    "我觉得《多模态日语词汇学习网站》中的学习内容很有意思",
    "学习时我常常忘记了时间",
    "相比其他方式，我更喜欢在《多模态日语词汇学习网站》中学习词汇",
]
Q6_UWES_ROWS = [
    "学习词汇时我充满精力",
    "即使遇到难记的词，我也愿意坚持练下去",
    "学习时我全神贯注，很少分心",
    "复习时我能很快进入状态",
    "我对学习日语词汇充满热情",
    "我会主动寻找额外的词汇学习内容",
]
Q7_EFFECT_EXP_ROWS = [
    "使用《多模态日语词汇学习网站》后，我觉得自己记住的单词比以前多",
    "我能更快地回忆起学过的单词",
    "我觉得自己的词汇量有明显提高",
    "听日语时，我能更快听懂学过的单词",
    "我能用学过的单词进行造句和简单表达",
    "《多模态日语词汇学习网站》帮我用更短的时间记住更多单词",
    "AI 生成的例句和短文帮助我理解单词的用法",
    "配图帮助我记住单词的意思",
    "语音/听力功能帮助我记住单词的发音",
    *Q7_EFFICACY_ROWS,
]
Q7_EFFECT_CTRL_ROWS = [
    "使用《多模态日语词汇学习网站》后，我觉得自己记住的单词比以前多",
    "我能更快地回忆起学过的单词",
    "我觉得自己的词汇量有明显提高",
    "听日语时，我能更快听懂学过的单词",
    "我能用学过的单词进行造句和简单表达",
    *Q7_EFFICACY_ROWS,
]

Q3_FLOW_ROWS = [
    "学习时我的注意力完全集中在单词上",
    "学习时我感觉自己完全沉浸其中",
    "学习任务对我来说有挑战但可以完成",
    "每次学习结束后我都有意犹未尽的感觉",
]
Q3_PERSONAL_ROWS = [
    "《多模态日语词汇学习网站》提供的内容难度适合我的日语水平",
    "《多模态日语词汇学习网站》的复习安排符合我的记忆情况",
    "我觉得《多模态日语词汇学习网站》的学习内容是为我量身定制的",
    "《多模态日语词汇学习网站》推荐的学习任务与我的需要相匹配",
]
Q3_QUALITY_ROWS = [
    "AI 生成的例句自然、地道",
    "AI 生成的短文有趣、与生活相关",
    "AI 配图与单词意思贴切",
    "《多模态日语词汇学习网站》操作流畅，学习过程顺畅",
    "《多模态日语词汇学习网站》界面清晰，功能容易找到",
]
Q3_SUS_ROWS = [
    "我愿意经常使用《多模态日语词汇学习网站》",
    "我觉得《多模态日语词汇学习网站》没有必要这么复杂",
    "我认为《多模态日语词汇学习网站》容易使用",
    "我觉得需要有技术人员的帮助才能使用《多模态日语词汇学习网站》",
    "我觉得《多模态日语词汇学习网站》的各种功能整合得很好",
    "我觉得《多模态日语词汇学习网站》有太多不一致的地方",
    "我认为大多数人都能很快学会使用《多模态日语词汇学习网站》",
    "我觉得《多模态日语词汇学习网站》使用起来很麻烦",
    "使用《多模态日语词汇学习网站》时我感觉很自信",
    "使用《多模态日语词汇学习网站》前我需要学习很多东西",
]
Q3_SUS_REVERSE_ROWS = [2, 4, 6, 8, 10]
Q3_INTENTION_ROWS = [
    "我愿意继续使用《多模态日语词汇学习网站》学习日语词汇",
    "我会向同学推荐《多模态日语词汇学习网站》",
    "以后学习新词汇时，我会优先考虑使用《多模态日语词汇学习网站》",
]

# ── 卷首语 ──
INTRO_Q1 = (
    "同学你好！我们是「基于AIGC的个性化日语词汇多模态学习体系」课题组成员。"
    "本问卷用于了解你的日语学习基本情况与学习感受，所有数据仅用于学术研究，"
    "匿名处理，不记入任何课程成绩。预计用时 13 分钟。填写即表示你已知情并同意参与本研究。谢谢！\n\n"
    "匿名编码说明：请填写“学号后 4 位 + 姓名拼音首字母”（如 0521LX），"
    "该编码仅用于前后测数据配对，与真实身份分离，请与后测保持一致。"
)
INTRO_Q2 = (
    "同学你好！这是本次研究的后测问卷，请你根据过去四周的真实学习感受作答。"
    "答案没有对错，请如实填写。数据仅用于学术研究，匿名处理。预计用时 16 分钟。谢谢！\n\n"
    "匿名编码请与前测保持一致：学号后 4 位 + 姓名拼音首字母。\n\n"
    "本问卷中的“《多模态日语词汇学习网站》”指你使用的日语词汇学习网站。"
)
INTRO_Q3 = (
    "同学你好！以下是关于你使用的《多模态日语词汇学习网站》的体验问卷，请根据真实感受作答。"
    "所有数据仅用于学术研究，匿名处理。预计用时 8 分钟。谢谢！"
)
INTRO_Q4 = (
    "同学你好！请根据你在《多模态日语词汇学习网站》中学习这批词汇时的真实感受作答，"
    "答案没有对错。数据仅用于学术研究。预计用时 3 分钟。谢谢！"
)

OUTRO_Q1 = "前测问卷已完成，再次感谢你的参与！"
OUTRO_Q2 = "后测问卷已完成，请继续参加词汇测试。感谢你的参与！"
OUTRO_Q3 = "问卷全部完成，感谢你的参与！请继续参加词汇测试。"
OUTRO_Q4 = "感谢你的配合！请继续完成词汇测试。"


def _m(key, text, rows, scale, reverse_rows=None):
    """构造矩阵量表题（rows 按顺序编号，反向题用全局行号标注）。"""
    item = {"key": key, "type": "matrix", "text": text, "rows": rows,
            "scale": scale, "required": True}
    if reverse_rows:
        item["reverse_rows"] = reverse_rows
    return item


def _m_blocks(key, text, blocks, scale, reverse_rows=None):
    """构造分块矩阵题（行号跨块连续）。"""
    rows = [r for b in blocks for r in b["rows"]]
    item = {"key": key, "type": "matrix", "text": text, "blocks": blocks,
            "rows": rows, "scale": scale, "required": True}
    if reverse_rows:
        item["reverse_rows"] = reverse_rows
    return item


QUESTIONNAIRES = [
    # ══════════════════════ 卷 1 · 前测问卷 ══════════════════════
    {
        "code": "q1",
        "number": "1",
        "name": "前测问卷",
        "version": VERSION,
        "audience": "两组（实验组 + 对照组）",
        "timing": "T0 · 第 1 周（第二轮 11–12 月第一周）",
        "minutes": 13,
        "intro": INTRO_Q1,
        "outro": OUTRO_Q1,
        "pages": [
            {"title": "基本信息", "items": [
                {"key": "p1q1", "type": "text", "required": True,
                 "text": "你的匿名编码是？（学号后4位+姓名首字母，如 0521LX）",
                 "placeholder": "如 0521LX"},
                {"key": "p1q2", "type": "radio", "required": True,
                 "text": "你的性别是？", "options": ["男", "女", "其他"]},
                {"key": "p1q3", "type": "text", "required": True,
                 "text": "你的年级与班级是？（如“大二1班”）", "placeholder": "如 大二1班"},
                {"key": "p1q4", "type": "radio", "required": True,
                 "text": "你学习日语的年限是？",
                 "options": ["不足1年", "1–2年", "2–3年", "3年以上"]},
                {"key": "p1q5", "type": "radio", "required": True,
                 "text": "你的日语水平（最近一次 JLPT 或自评）是？",
                 "options": ["N1", "N2", "N3", "N4", "N5", "未考级"]},
                {"key": "p1q6", "type": "radio", "required": True,
                 "text": "你每天平均花多少时间学日语？",
                 "options": ["不足30分钟", "30–60分钟", "1–2小时", "2小时以上"]},
                {"key": "p1q7", "type": "radio", "required": True,
                 "text": "你目前主要用什么方式积累日语词汇？",
                 "options": ["教材/课本", "背词App", "网络资源", "其他"]},
                {"key": "p1q8", "type": "text", "required": True,
                 "text": "你每天实际学习日语词汇的时长是？（分钟，填数字）",
                 "placeholder": "如 30"},
            ]},
            {"title": "近期学习感受（一）", "items": [
                _m_blocks("p2m1", "请回想你近两周日语词汇学习的情况，评价下列描述与你的符合程度。",
                          Q1_BLOCKS_PRE, AGREE5, Q1_REVERSE_ROWS),
            ]},
            {"title": "学习情绪", "items": [
                _m("p3m1", "回想你在学习日语词汇时的感受，以下情绪在你身上出现的程度是……",
                   Q4_ROWS_COMMON, EMOTION5),
            ]},
            {"title": "学习信心", "items": [
                _m("p4m1", "请评价以下说法……", Q7_EFFICACY_ROWS, AGREE5),
            ]},
            {"title": "当前学习状况", "items": [
                _m("p5m1", "请评价你目前的日语词汇学习状况。", Q12A_ROWS, AGREE5),
            ]},
        ],
        "dimensions": {
            "Q1_自主性": ["p2m1_r1", "p2m1_r2", "p2m1_r3", "p2m1_r4", "p2m1_r5", "p2m1_r6"],
            "Q1_胜任感": ["p2m1_r7", "p2m1_r8", "p2m1_r9", "p2m1_r10", "p2m1_r11", "p2m1_r12"],
            "Q1_归属感": ["p2m1_r13", "p2m1_r14", "p2m1_r15", "p2m1_r16", "p2m1_r17", "p2m1_r18"],
            "Q4_积极情绪": ["p3m1_r1", "p3m1_r2", "p3m1_r3", "p3m1_r4", "p3m1_r5"],
            "Q4_消极情绪": ["p3m1_r6", "p3m1_r7", "p3m1_r8", "p3m1_r9", "p3m1_r10"],
            "Q7_自我效能": ["p4m1_r1", "p4m1_r2", "p4m1_r3", "p4m1_r4"],
            "Q12A_现状水平": ["p5m1_r1", "p5m1_r2"],
        },
        "reverse": [f"p2m1_r{i}" for i in Q1_REVERSE_ROWS],
    },
]


def _q2_pages(blocks, effect_rows, p2_intro, reason_intro, emotion_intro):
    """卷 2 两个版本共用页面骨架。

    ⚠️ 引导语按版本分别传入：实验组与对照组的第 2 页引导语措辞**并不相同**
    （实验组主语是《多模态日语词汇学习网站》，对照组主语是「我的日语学习」），
    误用同一份会让两版数据的作答情境不一致，影响组间可比性。
    """
    return [
        {"title": "基本信息复核", "items": [
            {"key": "p1q1", "type": "text", "required": True,
             "text": "你的匿名编码是？（与前测一致）", "placeholder": "如 0521LX"},
            {"key": "p1q2", "type": "radio", "required": True,
             "text": "过去四周，你平均每周有几天学习日语词汇？",
             "options": ["0–2天", "3–4天", "5–6天", "每天"]},
        ]},
        {"title": "学习感受（一）", "items": [
            _m_blocks("p2m1", p2_intro, blocks, AGREE5, Q1_REVERSE_ROWS),
        ]},
        {"title": "学习原因", "items": [
            _m("p3m1", reason_intro, Q2_REASON_ROWS, AGREE5),
        ]},
        {"title": "学习感受（二）", "items": [
            _m("p4m1", "请评价以下说法……", Q3_IMI_ROWS, AGREE5),
        ]},
        {"title": "学习情绪", "items": [
            _m("p5m1", emotion_intro, Q4_ROWS_COMMON, EMOTION5),
        ]},
        {"title": "学习投入", "items": [
            _m("p6m1", "请评价以下说法……", Q6_UWES_ROWS, AGREE5),
        ]},
        {"title": "学习效果自评", "items": [
            _m("p7m1", "请评价以下说法……", effect_rows, AGREE5),
        ]},
        {"title": "学习兴趣与效率（前后对比）", "items": [
            _m("p8m1", "A 组 · 现状水平（与前测卷 1 第 5 页文字完全一致）",
               Q12A_ROWS, AGREE5),
            _m("p8m2", "B 组 · 变化感知", Q12B_ROWS, CHANGE5),
        ]},
    ]


Q2_EXP_PAGES = _q2_pages(
    Q1_BLOCKS_EXP, Q7_EFFECT_EXP_ROWS,
    "回想过去四周在《多模态日语词汇学习网站》中学习的情况，评价下列描述……",
    "我使用《多模态日语词汇学习网站》学习日语词汇，主要是因为……",
    "回想在《多模态日语词汇学习网站》中学习词汇时的感受，以下情绪出现的程度……",
)
Q2_CTRL_PAGES = _q2_pages(
    Q1_BLOCKS_CTRL, Q7_EFFECT_CTRL_ROWS,
    "请回想你过去四周日语词汇学习的情况，评价下列描述与你的符合程度。",
    "我学习日语词汇，主要是因为……",
    "回想你在学习日语词汇时的感受，以下情绪在你身上出现的程度是……",
)

_Q2_DIM_BASE = {
    "Q2_外在调节": ["p3m1_r1", "p3m1_r2", "p3m1_r3"],
    "Q2_内摄调节": ["p3m1_r4", "p3m1_r5", "p3m1_r6"],
    "Q2_认同调节": ["p3m1_r7", "p3m1_r8", "p3m1_r9"],
    "Q2_内在动机": ["p3m1_r10", "p3m1_r11", "p3m1_r12"],
    "Q3_兴趣享受": ["p4m1_r1", "p4m1_r2", "p4m1_r3", "p4m1_r4"],
    "Q4_积极情绪": ["p5m1_r1", "p5m1_r2", "p5m1_r3", "p5m1_r4", "p5m1_r5"],
    "Q4_消极情绪": ["p5m1_r6", "p5m1_r7", "p5m1_r8", "p5m1_r9", "p5m1_r10"],
    "Q6_活力": ["p6m1_r1", "p6m1_r2"],
    "Q6_专注": ["p6m1_r3", "p6m1_r4"],
    "Q6_奉献": ["p6m1_r5", "p6m1_r6"],
    "Q7_自我效能": ["p7m1_r10", "p7m1_r11", "p7m1_r12", "p7m1_r13"],
    "Q12A_现状水平": ["p8m1_r1", "p8m1_r2"],
    "Q12B_变化感知": ["p8m2_r1", "p8m2_r2"],
}
QUESTIONNAIRES.append({
    "code": "q2_exp",
    "number": "2",
    "name": "后测核心（实验组）",
    "version": VERSION,
    "audience": "实验组",
    "timing": "T1 · 第 5 周末（第二轮 11–12 月）",
    "minutes": 16,
    "intro": INTRO_Q2,
    "outro": OUTRO_Q2,
    "pages": Q2_EXP_PAGES,
    "dimensions": {
        "Q1_自主性": ["p2m1_r1", "p2m1_r2", "p2m1_r3", "p2m1_r4", "p2m1_r5", "p2m1_r6"],
        "Q1_胜任感": ["p2m1_r7", "p2m1_r8", "p2m1_r9", "p2m1_r10", "p2m1_r11", "p2m1_r12"],
        "Q1_归属感": ["p2m1_r13", "p2m1_r14", "p2m1_r15", "p2m1_r16", "p2m1_r17", "p2m1_r18"],
        **_Q2_DIM_BASE,
        "Q7_感知习得": ["p7m1_r1", "p7m1_r2", "p7m1_r3", "p7m1_r4", "p7m1_r5"],
        "Q7_感知学习效率": ["p7m1_r6", "p7m1_r7", "p7m1_r8", "p7m1_r9"],
    },
    "reverse": [f"p2m1_r{i}" for i in Q1_REVERSE_ROWS],
})
QUESTIONNAIRES.append({
    "code": "q2_ctrl",
    "number": "2",
    "name": "后测核心（对照组）",
    "version": VERSION,
    "audience": "对照组",
    "timing": "T1 · 第 5 周末（第二轮 11–12 月）",
    "minutes": 16,
    "intro": INTRO_Q2,
    "outro": OUTRO_Q2,
    "pages": Q2_CTRL_PAGES,
    "dimensions": {
        "Q1_自主性": ["p2m1_r1", "p2m1_r2", "p2m1_r3", "p2m1_r4", "p2m1_r5", "p2m1_r6"],
        "Q1_胜任感": ["p2m1_r7", "p2m1_r8", "p2m1_r9", "p2m1_r10", "p2m1_r11", "p2m1_r12"],
        "Q1_归属感": ["p2m1_r13", "p2m1_r14", "p2m1_r15", "p2m1_r16", "p2m1_r17", "p2m1_r18"],
        # 对照组不测「感知学习效率」（无多模态功能），故不含该项
        **_Q2_DIM_BASE,
        "Q7_感知习得": ["p7m1_r1", "p7m1_r2", "p7m1_r3", "p7m1_r4", "p7m1_r5"],
        # 对照组第 7 页仅 9 行：感知习得 5 行 + 自我效能 4 行（r6–r9），
        # 自我效能不能沿用实验组的 r10–r13（会指向不存在的行，导致该维度恒为空）
        "Q7_自我效能": ["p7m1_r6", "p7m1_r7", "p7m1_r8", "p7m1_r9"],
    },
    "reverse": [f"p2m1_r{i}" for i in Q1_REVERSE_ROWS],
})

QUESTIONNAIRES.append({
    "code": "q3",
    "number": "3",
    "name": "实验组附加卷",
    "version": VERSION,
    "audience": "仅实验组",
    "timing": "T1 同日（填完卷 2 之后）",
    "minutes": 8,
    "intro": INTRO_Q3,
    "outro": OUTRO_Q3,
    "pages": [
        {"title": "学习状态", "items": [
            _m("p1m1", "回想你在平台上学习词汇时的状态……", Q3_FLOW_ROWS, AGREE5),
        ]},
        {"title": "个性化体验", "items": [
            _m("p2m1", "请评价平台与你的匹配程度……", Q3_PERSONAL_ROWS, AGREE5),
        ]},
        {"title": "平台质量", "items": [
            _m("p3m1", "请评价平台的内容与系统……", Q3_QUALITY_ROWS, AGREE5),
        ]},
        {"title": "可用性", "items": [
            _m("p4m1", "请评价平台的易用性……", Q3_SUS_ROWS, SUS5,
               reverse_rows=Q3_SUS_REVERSE_ROWS),
        ]},
        {"title": "使用意愿", "items": [
            _m("p5m1", "请评价以下说法……", Q3_INTENTION_ROWS, AGREE5),
        ]},
        {"title": "开放题（选填）", "items": [
            {"key": "p6q1", "type": "textarea", "required": False,
             "text": "使用《多模态日语词汇学习网站》学习词汇，你觉得最大的收获是什么？",
             "placeholder": "选填，可留空"},
            {"key": "p6q2", "type": "textarea", "required": False,
             "text": "你觉得《多模态日语词汇学习网站》最需要改进的地方是什么？",
             "placeholder": "选填，可留空"},
        ]},
    ],
    "dimensions": {
        "Q5_心流": ["p1m1_r1", "p1m1_r2", "p1m1_r3", "p1m1_r4"],
        "Q8_感知个性化": ["p2m1_r1", "p2m1_r2", "p2m1_r3", "p2m1_r4"],
        "Q9_内容质量": ["p3m1_r1", "p3m1_r2", "p3m1_r3"],
        "Q9_系统质量": ["p3m1_r4", "p3m1_r5"],
        "Q9_SUS": [f"p4m1_r{i}" for i in range(1, 11)],
        "Q9_持续使用意愿": ["p5m1_r1", "p5m1_r2", "p5m1_r3"],
    },
    "reverse": [f"p4m1_r{i}" for i in Q3_SUS_REVERSE_ROWS],
})

DIFFICULTY9 = {
    "min": 1, "max": 9,
    "labels": {1: "非常容易", 5: "一般", 9: "非常困难"},
}
_Q4_ROWS_EXP = [
    "学习内容本身（单词的意思和用法）对我来说很难",
    "学习材料的呈现方式（图片/语音/排版等）让理解变得复杂，分散了我的注意力",
    "我要花很大精力才能把图片、语音和文字的信息整合起来",
    "总的来说，在《多模态日语词汇学习网站》中学习让我感到很吃力",
]
_Q4_ROWS_CTRL = [
    "学习内容本身（单词的意思和用法）对我来说很难",
    "学习材料的呈现方式（排版等）让理解变得复杂，分散了我的注意力",
    "我要花很大精力才能把学到的信息整合起来",
    "总的来说，在《多模态日语词汇学习网站》中学习让我感到很吃力",
]

for _code, _name, _rows in [
    ("q4_exp", "认知负荷问卷（实验组）", _Q4_ROWS_EXP),
    ("q4_ctrl", "认知负荷问卷（对照组）", _Q4_ROWS_CTRL),
]:
    QUESTIONNAIRES.append({
        "code": _code,
        "number": "4",
        "name": _name,
        "version": VERSION,
        "audience": "第二轮二外组（两组同卷）",
        "timing": "T1（仅第二轮 11–12 月）",
        "minutes": 3,
        "intro": INTRO_Q4,
        "outro": OUTRO_Q4,
        "pages": [
            {"title": "学习难度", "items": [
                {"key": "p1q1", "type": "radio", "required": True,
                 "text": "在《多模态日语词汇学习网站》中学习这批词汇，你觉得难度如何？",
                 "options": [str(i) for i in range(1, 10)],
                 "scale": DIFFICULTY9},
            ]},
            {"title": "负荷感受", "items": [
                _m("p2m1", "请评价以下说法……", _rows, AGREE5),
            ]},
        ],
        "dimensions": {
            "Q11_整体难度": ["p1q1"],
            "Q11_内在负荷": ["p2m1_r1"],
            "Q11_外在负荷": ["p2m1_r2"],
            "Q11_相关负荷": ["p2m1_r3"],
            "Q11_疲劳感": ["p2m1_r4"],
        },
        "reverse": [],
    })


# ── 索引与工具函数 ──
_BY_CODE = {q["code"]: q for q in QUESTIONNAIRES}


def list_questionnaires() -> list:
    """按卷号顺序返回全部问卷定义。"""
    return list(QUESTIONNAIRES)


def get_questionnaire(code: str) -> dict | None:
    return _BY_CODE.get(code)


def parse_code(code: str):
    """拆分内部编码，便于按「卷号」聚合（q2_exp → ('2', 'exp')）。"""
    if not code:
        return ("", "")
    body = code[1:] if code.startswith("q") else code
    if "_" in body:
        number, variant = body.split("_", 1)
        return (number, variant)
    return (body, "")


def display_name(q: dict) -> str:
    """展示名：卷号 + 名称（如「卷2 后测核心（实验组）」）。"""
    return f"卷{q['number']} {q['name']}"


def item_keys(q: dict) -> list:
    """全部条目 key（矩阵题展开到行）。"""
    keys = []
    for page in q["pages"]:
        for item in page["items"]:
            if item["type"] == "matrix":
                keys.extend(f"{item['key']}_r{i}" for i in range(1, len(item["rows"]) + 1))
            else:
                keys.append(item["key"])
    return keys


def required_keys(q: dict) -> list:
    """必答条目 key（矩阵题整体必答）。"""
    keys = []
    for page in q["pages"]:
        for item in page["items"]:
            if not item.get("required"):
                continue
            if item["type"] == "matrix":
                keys.extend(f"{item['key']}_r{i}" for i in range(1, len(item["rows"]) + 1))
            else:
                keys.append(item["key"])
    return keys


def item_labels(q: dict) -> dict:
    """条目 key → 题干/行文本（导出 CSV 与管理员查看时用）。"""
    labels = {}
    for page in q["pages"]:
        for item in page["items"]:
            if item["type"] == "matrix":
                for i, row in enumerate(item["rows"], 1):
                    labels[f"{item['key']}_r{i}"] = f"{item['text']}｜{row}"
            else:
                labels[item["key"]] = item["text"]
    return labels


def choice_options(q: dict) -> dict:
    """选择题（含矩阵行）的选项范围，用于提交校验。"""
    opts = {}
    for page in q["pages"]:
        for item in page["items"]:
            if item["type"] == "radio":
                opts[item["key"]] = [str(o) for o in item.get("options", [])]
            elif item["type"] == "matrix":
                scale = item.get("scale") or {}
                lo, hi = scale.get("min", 1), scale.get("max", 5)
                for i in range(1, len(item["rows"]) + 1):
                    opts[f"{item['key']}_r{i}"] = [str(v) for v in range(lo, hi + 1)]
    return opts


def compute_scores(q: dict, answers: dict) -> dict:
    """按维度计算均值分（反向题先反转），供管理员查看与科研导出。

    返回 {维度名: 均值}；条目缺失时跳过该条目，全缺则不计该维度。
    """
    reverse = set(q.get("reverse") or [])
    out = {}
    for dim, keys in (q.get("dimensions") or {}).items():
        vals = []
        for k in keys:
            raw = answers.get(k)
            if raw is None or raw == "":
                continue
            try:
                v = float(raw)
            except (TypeError, ValueError):
                continue
            if k in reverse:
                v = _reverse_value(q, k, v)
            vals.append(v)
        if vals:
            out[dim] = round(sum(vals) / len(vals), 3)
    return out


def _reverse_value(q: dict, key: str, v: float) -> float:
    """反转到量表两端之和（1–5 → 6−v；1–9 → 10−v）。"""
    for page in q["pages"]:
        for item in page["items"]:
            if item["type"] == "matrix" and key.startswith(item["key"] + "_r"):
                scale = item.get("scale") or {}
                return (scale.get("min", 1) + scale.get("max", 5)) - v
    return v
