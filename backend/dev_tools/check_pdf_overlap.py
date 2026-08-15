# -*- coding: utf-8 -*-
"""bbox 级重叠检测：x 与 y 均交叠才算内容堆叠（排除左右列并排误报）。"""
import pdfplumber

pdf = pdfplumber.open(r"C:\Users\Administrator\Desktop\11\backend\cards_test.pdf")
total = 0
for pno, page in enumerate(pdf.pages, 1):
    words = page.extract_words()
    n = len(words)
    ov = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = words[i], words[j]
            xov = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
            yov = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
            if xov > 2 and yov > 2:
                ov += 1
                if ov <= 6:
                    print(f"第{pno}页 真重叠: [{a['text']}] vs [{b['text']}] xov={xov:.1f} yov={yov:.1f}")
    total += ov
    print(f"第{pno}页: 真重叠 {ov} 对")
print(f"总计真重叠: {total}")
