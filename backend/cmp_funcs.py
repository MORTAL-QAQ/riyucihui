# -*- coding: utf-8 -*-
"""对比 app.js 与 common.js 重复函数实现是否一致。"""
import io, re

def read(p):
    return io.open(p, encoding="utf-8").read()

app = read(r"C:\Users\Administrator\Desktop\11\frontend\js\app.js")
com = read(r"C:\Users\Administrator\Desktop\11\frontend\js\common.js")

def extract(src, name):
    m = re.search(r"function " + name + r"\([^)]*\) \{", src)
    if not m:
        return None
    start = m.start()
    i = src.index("{", start)
    depth = 0
    j = i
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return src[start : j + 1]

for fn in ["esc", "fmtTime", "showToast", "handleApiError", "unlockAudio",
           "clearSpeaking", "speakWord", "runStreamToPreview"]:
    a = extract(app, fn)
    c = extract(com, fn)
    if a is None or c is None:
        print(f"{fn}: app={'有' if a else '无'} common={'有' if c else '无'}")
    else:
        print(f"{fn}: {'一致' if a == c else '不同！'}")
