# -*- coding: utf-8 -*-
"""验证统一后顶栏：导航按钮数 + 当前页高亮数 + div 配对。"""
import io, re

PAGES = ["community", "wordbank", "study", "generate", "essay", "cloze",
         "grammar", "image", "settings", "achievement", "admin", "saved"]

for page in PAGES:
    path = r"C:\Users\Administrator\Desktop\11\frontend" + "\\" + page + ".html"
    text = io.open(path, encoding="utf-8").read()
    btns = text.count("border-radius:999px")
    active = text.count("rgba(99,102,241,0.35)")
    expected = 12 if page == "admin" else 11
    # 高亮 href 校验
    hl_href = re.search(r'<a href="([^"]+)" style="[^"]*rgba\(99,102,241,0\.35\)[^"]*">', text)
    ok_hl = "OK" if hl_href and hl_href.group(1) == "/" + page else f"异常(高亮指向 {hl_href.group(1) if hl_href else '无'})"
    ok_n = "OK" if btns == expected else f"异常(按钮数 {btns} != {expected})"
    # 导航区 div 配对粗检
    nav_start = text.find("flex-wrap:wrap; justify-content:center")
    seg = text[nav_start:text.find("</header>", nav_start)]
    opens = seg.count("<div")
    closes = seg.count("</div>")
    ok_div = "OK" if opens == closes else f"异常(div {opens}/{closes})"
    print(f"{page}: 按钮={btns}({ok_n}) 高亮={active}({ok_hl}) div={opens}/{closes}({ok_div})")

print("done")
