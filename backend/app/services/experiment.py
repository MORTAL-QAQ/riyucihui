"""实验支持：用户分组标签 + 实验词单锁定（大创教学实验用）。

约定：
- 词单（Word.topic）以 `LOCKED_TOPIC_PREFIX`（"实验:"）开头即为**实验词单**，
  仅实验组用户（experiment_group == "experiment"）和管理员可访问，对照组/未分组用户不可见、不可操作。
- 该前缀集中于此模块，改动一处即可全局生效。
"""

from ..models import User

# 实验词单主题前缀（教师建词单时按此前缀命名，如「实验:学校生活」）
LOCKED_TOPIC_PREFIX = "实验:"


def is_locked_topic(topic: str | None) -> bool:
    """判断主题名是否为实验词单。"""
    return bool(topic and topic.startswith(LOCKED_TOPIC_PREFIX))


def can_access_locked(user: User) -> bool:
    """是否允许访问实验词单：管理员或实验组成员。"""
    if user.is_admin:
        return True
    return (user.experiment_group or "").strip().lower() == "experiment"


def group_label(user: User) -> str:
    """实验分组的中文标签（管理后台展示用）。"""
    if user.is_admin:
        return "管理员"
    return {"experiment": "实验组", "control": "对照组"}.get(
        (user.experiment_group or "").strip().lower(), "未分组"
    )
