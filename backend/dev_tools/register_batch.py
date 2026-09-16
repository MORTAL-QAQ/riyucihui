# -*- coding: utf-8 -*-
"""批量注册学生账号：学号=账号，姓名=昵称，密码 123456。

在 backend 容器内执行（docker compose exec backend python /tmp/register_batch.py）。
"""
import json
from pathlib import Path

from app import config
from app.auth import hash_password
from app.database import SessionLocal
from app.models import User

DATA = Path("/tmp/students.json")
DEFAULT_PASSWORD = "123456"

students = json.loads(DATA.read_text(encoding="utf-8"))
db = SessionLocal()

created, skipped = [], []
for s in students:
    sid = str(s["sid"]).strip()
    name = str(s["name"]).strip()
    if not sid or not name:
        continue
    if db.query(User).filter(User.username == sid).first():
        skipped.append(f"{sid} {name}")
        continue
    db.add(User(
        username=sid,
        name=name,
        password_hash=hash_password(DEFAULT_PASSWORD),
        daily_ai_limit=config.DEFAULT_DAILY_AI_LIMIT,
        daily_image_limit=config.DEFAULT_DAILY_IMAGE_LIMIT,
        daily_word_limit=config.DEFAULT_DAILY_WORD_LIMIT,
        daily_voice_limit=config.DEFAULT_DAILY_VOICE_LIMIT,
    ))
    created.append(f"{sid} {name}")

db.commit()
print(f"✅ 新建 {len(created)} 个账号，跳过已存在 {len(skipped)} 个")
for c in created:
    print("  +", c)
for s in skipped:
    print("  = 已存在，跳过:", s)

total = db.query(User).count()
print(f"当前用户总数: {total}")
db.close()
