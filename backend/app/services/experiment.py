"""实验支持：实验词单可见性 + 词级呈现模式（被试内教学实验用）。

## 两条与实验设计强相关的约定

1. **实验词单**：词单（`Word.topic`）以 `LOCKED_TOPIC_PREFIX`（"实验:"）开头即为实验词单。
   - **默认向全体被试开放**（`EXPERIMENT_TOPIC_OPEN=true`）：被试内设计下，全体被试都要学习
     同一批实验词单（每份词单内含 10 个图文音词 + 10 个纯文字词），因此不能再按组隔离，
     否则未分组的学生看不到材料。
   - 若因故需要恢复「按组隔离」（原先的组间设计），在服务器 `.env` 设
     `EXPERIMENT_TOPIC_OPEN=false`，则只有 `experiment_group == "experiment"` 的用户与管理员可见。

2. **词级呈现模式**（`Word.presentation_mode`）：被试内设计的核心操纵变量。
   - `"multimodal"` 图文音：学习卡片显示 AI 配图，并提供发音按钮
   - `"text_only"`  纯文字：**不显示配图、不提供发音**，其余界面元素完全一致
   - `None` 未指定：等同 multimodal 的呈现行为

   该模式绑在**词**上（同一词对所有被试一致），由教师按论文「模态分配方案」批量设置，
   见 `dev_tools/assign_presentation_modes.py`。
"""

from .. import config
from ..models import User, Word

# 实验词单主题前缀（教师建词单时按此前缀命名，如「实验:学校生活」）
LOCKED_TOPIC_PREFIX = "实验:"

# 呈现模式取值
MODE_MULTIMODAL = "multimodal"
MODE_TEXT_ONLY = "text_only"


def is_locked_topic(topic: str | None) -> bool:
    """判断主题名是否为实验词单。"""
    return bool(topic and topic.startswith(LOCKED_TOPIC_PREFIX))


def can_access_locked(user: User) -> bool:
    """是否允许访问实验词单。

    被试内设计下**默认全体开放**（config.EXPERIMENT_TOPIC_OPEN=true）；
    设 EXPERIMENT_TOPIC_OPEN=false 可恢复原先的「仅实验组 + 管理员」隔离。
    """
    if getattr(config, "EXPERIMENT_TOPIC_OPEN", True):
        return True
    if user.is_admin:
        return True
    return (user.experiment_group or "").strip().lower() == "experiment"


def is_text_only(word: Word) -> bool:
    """该词是否为纯文字呈现（不显示配图、不提供发音）。"""
    return (word.presentation_mode or "").strip().lower() == MODE_TEXT_ONLY


def mode_label(mode: str | None) -> str:
    """呈现模式的中文标签（导出/展示用）。"""
    return {
        MODE_MULTIMODAL: "图文音",
        MODE_TEXT_ONLY: "纯文字",
    }.get((mode or "").strip().lower(), "未指定")


def group_label(user: User) -> str:
    """实验分组的中文标签（管理后台展示用；被试内设计下仅作历史字段保留）。"""
    if user.is_admin:
        return "管理员"
    return {"experiment": "实验组", "control": "对照组"}.get(
        (user.experiment_group or "").strip().lower(), "未分组"
    )
