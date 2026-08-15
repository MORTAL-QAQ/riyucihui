# -*- coding: utf-8 -*-
"""生成并检测 table 模式 + 学习报告 PDF 重叠。"""
import io
import sys

import pdfplumber

sys.path.insert(0, r"C:\Users\Administrator\Desktop\11\backend")
from app.database import SessionLocal, run_migrations
from app.models import User, Word
from app.services import pdf_service

run_migrations()  # 本地库补齐迁移（name 列等）

db = SessionLocal()
user = db.query(User).first()
words = db.query(Word).filter(Word.user_id == user.id).limit(60).all()

def check(name, buf):
    open(rf"C:\Users\Administrator\Desktop\11\backend\{name}.pdf", "wb").write(buf.getvalue())
    pdf = pdfplumber.open(rf"C:\Users\Administrator\Desktop\11\backend\{name}.pdf")
    total = 0
    for pno, page in enumerate(pdf.pages, 1):
        ws = page.extract_words()
        for i in range(len(ws)):
            for j in range(i + 1, len(ws)):
                a, b = ws[i], ws[j]
                xov = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
                yov = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
                if xov > 2 and yov > 2:
                    total += 1
                    print(f"{name} 第{pno}页 真重叠: [{a['text']}] vs [{b['text']}]")
        print(f"{name} 第{pno}页: {len(ws)} 词")
    print(f"{name}: 总真重叠 {total}")
    db_ = db
    return total

check("table_test", pdf_service.generate_words_pdf(words, "表格核验", len(words), layout="table", include_images=False))
check("report_test", pdf_service.generate_study_report_pdf(db, user.id))
db.close()
print("done")
