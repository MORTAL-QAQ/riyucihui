#!/bin/bash
cd /opt/riyucihui
docker compose exec -T backend python - << 'PYEOF'
"""生成各类型 PDF 验证：列宽/布局无异常（抛 LayoutError 即失败）。"""
import io, sys
from datetime import date

from app.database import SessionLocal
from app.models import Word, StudyRecord, Essay, Cloze, GrammarCompare, User
from app.services import pdf_service

db = SessionLocal()

def report(name, buf):
    data = buf.getvalue()
    print(f"{name}: OK, {len(data)} bytes")
    if len(data) < 1000:
        print(f"  ⚠️ {name} 文件过小，可能内容异常")

# 1) 词库 table 模式（取第一个用户的词）
user = db.query(User).first()
words = db.query(Word).filter(Word.user_id == user.id).limit(30).all()
print(f"测试用户: {user.username}, 单词数: {len(words)}")
report("词库-table", pdf_service.generate_words_pdf(words, "测试词单", len(words), layout="table", include_images=False))

# 2) 词库 card 模式（含图片，若存在）
report("词库-card", pdf_service.generate_words_pdf(words, "测试词单", len(words), layout="card", include_images=True))

# 3) 学习报告
report("学习报告", pdf_service.generate_study_report_pdf(db, user.id))

# 4) 短文 PDF
essay = db.query(Essay).filter(Essay.user_id == user.id).first()
if essay:
    report("短文", pdf_service.generate_essay_pdf(essay))

# 5) 完型 PDF
cloze = db.query(Cloze).filter(Cloze.user_id == user.id).first()
if cloze:
    report("完型", pdf_service.generate_cloze_pdf(cloze))

# 6) 语法 PDF
grammar = db.query(GrammarCompare).filter(GrammarCompare.user_id == user.id).first()
if grammar:
    report("语法", pdf_service.generate_grammar_compare_pdf(grammar))

db.close()
print("全部生成完成")
PYEOF
