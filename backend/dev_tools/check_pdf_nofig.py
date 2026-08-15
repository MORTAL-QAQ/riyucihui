# -*- coding: utf-8 -*-
"""验证 generate_words_pdf 新签名（无 include_images）。"""
import sys

sys.path.insert(0, r"C:\Users\Administrator\Desktop\11\backend")
from app.database import SessionLocal, run_migrations
from app.models import User, Word
from app.services import pdf_service

run_migrations()
db = SessionLocal()
user = db.query(User).first()
words = db.query(Word).filter(Word.user_id == user.id).limit(5).all()
if not words:
    print("本地库无单词，跳过生成")
else:
    for layout in ("table", "card"):
        buf = pdf_service.generate_words_pdf(words, "验证", len(words), layout=layout)
        print(f"{layout}: {len(buf.getvalue())} bytes OK")
db.close()
print("done")
