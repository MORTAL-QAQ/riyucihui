# -*- coding: utf-8 -*-
"""验证表格 PDF：无 JLPT 列、无文字重叠。"""
import sys

import pdfplumber

sys.path.insert(0, r"C:\Users\Administrator\Desktop\11\backend")
from app.database import SessionLocal, run_migrations
from app.models import User, Word
from app.services import pdf_service

run_migrations()
db = SessionLocal()
user = db.query(User).first()
words = db.query(Word).filter(Word.user_id == user.id).limit(40).all()
buf = pdf_service.generate_words_pdf(words, "验证", len(words), layout="table")
path = r"C:\Users\Administrator\Desktop\11\backend\table_nocheck.pdf"
open(path, "wb").write(buf.getvalue())

pdf = pdfplumber.open(path)
print(f"页数: {len(pdf.pages)}")
total = 0
for pno, page in enumerate(pdf.pages, 1):
    ws = page.extract_words()
    # 检查是否还有 N 列（表头不应有 N）
    texts = [w["text"] for w in ws]
    has_n_header = "N" in texts[:8]
    if has_n_header:
        print(f"第{pno}页 表头仍含 N ❌")
    for i in range(len(ws)):
        for j in range(i + 1, len(ws)):
            a, b = ws[i], ws[j]
            xov = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
            yov = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
            if xov > 2 and yov > 2:
                total += 1
                if total <= 6:
                    print(f"第{pno}页 真重叠: [{a['text']}] vs [{b['text']}]")
    print(f"第{pno}页: {len(ws)} 词")
print(f"总真重叠: {total}")
db.close()
