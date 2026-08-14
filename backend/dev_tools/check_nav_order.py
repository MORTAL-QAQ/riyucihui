# -*- coding: utf-8 -*-
"""验证侧边栏顺序与顶栏一致。"""
import io, re

h = io.open(r"C:\Users\Administrator\Desktop\11\frontend\index.html", encoding="utf-8").read()
nav = re.search(r'<nav class="nav">(.*?)</nav>', h, re.S).group(1)
tabs = re.findall(r'data-tab="([a-z]+)"', nav)
print("侧边栏顺序:", tabs)
expected = ["home", "wordbank", "study", "generate", "community",
            "essay", "cloze", "grammar", "image", "achievement", "saved",
            "settings", "admin"]
print("匹配顶栏顺序:", tabs == expected)
