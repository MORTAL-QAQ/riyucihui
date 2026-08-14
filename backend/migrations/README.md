# Alembic 迁移版本目录

当前应用启动流程仍使用 `Base.metadata.create_all()` + `run_migrations()`（兼容历史库，
含 DDL 并发锁与索引补建）。Alembic 已作为渐进式迁移框架引入（#18）。

## 用法（backend/ 目录）

```bash
# 生成迁移（对比 models 与当前库）
python -m alembic revision --autogenerate -m "描述"

# 在备份库上先验证
python -m alembic upgrade head

# 查看待执行迁移
python -m alembic history
```

## 生产切换注意

- 生产库由 `create_all` 建成，首次接入 Alembic 需生成 baseline（stamp 当前版本）
- 建议切换前先在测试/备份库完整演练，并在 deploy 流程中显式执行迁移
- 迁移与 worker 启动分离（#16/#18）：不要在 lifespan 中自动执行 alembic upgrade
