#!/bin/bash
cd /opt/riyucihui
# 生成词库卡片 PDF（含图片、跨页）并转 PNG 供核验
docker compose exec -T backend python - << 'PYEOF'
from app.database import SessionLocal
from app.models import Word, User
from app.services import pdf_service

db = SessionLocal()
user = db.query(User).first()
words = db.query(Word).filter(Word.user_id == user.id).limit(60).all()
buf = pdf_service.generate_words_pdf(words, "卡片核验", len(words), layout="card", include_images=True)
open("/tmp/cards_test.pdf", "wb").write(buf.getvalue())
print(f"卡片 PDF 生成: {len(words)} 词, {len(buf.getvalue())} bytes")
db.close()
PYEOF
# 转 PNG
which pdftoppm && pdftoppm -png -r 60 /tmp/cards_test.pdf /tmp/cardpage || echo "no pdftoppm"
ls -la /tmp/cardpage* 2>/dev/null | head -5
