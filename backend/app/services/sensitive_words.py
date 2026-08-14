"""敏感词过滤服务。

社区内容（帖子/评论）发布前检查；命中则拒绝发布（配合管理员删帖形成双重审核）。
词表为内置示例，可按需增删；后续可扩展为配置驱动（环境变量 / settings.json）。
"""

# 内置敏感词表（示例词，覆盖常见违法违规类别；命中即拦截）
SENSITIVE_WORDS: set[str] = {
    "赌博", "赌场", "色情", "裸聊", "毒品", "冰毒", "海洛因",
    "诈骗", "洗钱", "代考", "办证", "枪支", "弹药", "爆炸物",
    "传销", "赌博网站",
}


def check_sensitive(text: str | None) -> str | None:
    """检查文本是否含敏感词。

    Returns:
        命中的敏感词；无命中返回 None。
    """
    if not text:
        return None
    for word in SENSITIVE_WORDS:
        if word in text:
            return word
    return None
