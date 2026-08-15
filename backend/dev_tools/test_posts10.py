# -*- coding: utf-8 -*-
"""单元验证 posts_10：注册用户 → 直接插 10 条帖子 → check_achievements。"""
import sys

sys.path.insert(0, r"C:\Users\Administrator\Desktop\11\backend")
from app.auth import hash_password
from app.database import SessionLocal, run_migrations
from app.models import Post, User
from app.services.achievement_service import check_achievements

run_migrations()
db = SessionLocal()
u = db.query(User).filter(User.username == "p10test").first()
if not u:
    u = User(username="p10test", name="p10test", password_hash=hash_password("Pass123456"))
    db.add(u)
    db.commit()
    db.refresh(u)
# 清理旧成就与帖子，重测
from app.models import Achievement
db.query(Achievement).filter(Achievement.user_id == u.id).delete()
db.query(Post).filter(Post.user_id == u.id).delete()
db.commit()

for i in range(10):
    db.add(Post(user_id=u.id, type="post", title=f"帖 {i}", content="x"))
db.commit()

new = check_achievements(db, u.id)
print("新解锁:", [a["name"] for a in new])
from app.models import Achievement
rows = db.query(Achievement).filter(Achievement.user_id == u.id).all()
keys = {r.key for r in rows}
print("成就记录:", sorted(keys))
assert "first_post" in keys and "posts_10" in keys, "first_post/posts_10 未解锁"
print("first_post + posts_10 解锁 ✅")
db.close()
