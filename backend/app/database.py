"""数据库引擎与会话管理。

- 创建 SQLAlchemy 引擎和会话工厂
- SQLite 模式自动启用 WAL 日志、外键约束和忙等待超时
- run_migrations() 在应用启动时执行，自动创建缺失的表和列
- get_db() 依赖注入：每个 HTTP 请求一个数据库会话
"""

import sys

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

_connect_args = {}
_engine_kwargs = {}

if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
    _engine_kwargs = {"pool_size": 1, "max_overflow": 4}
    _IS_SQLITE = True
else:
    _IS_SQLITE = False

engine = create_engine(DATABASE_URL, connect_args=_connect_args, **_engine_kwargs)

if _IS_SQLITE:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    print(
        "\n"
        + "=" * 64
        + "\n"
        "  NOTE: Running with SQLite.\n"
        "  SQLite is fine for single-user / light usage.\n"
        "  For multi-user production, set DATABASE_URL to PostgreSQL:\n"
        "    DATABASE_URL=postgresql://user:pass@host:5432/dbname\n"
        + "=" * 64
        + "\n",
        file=sys.stderr,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def run_migrations():
    """Add new columns for existing databases (SQLite / PostgreSQL compat)."""
    with engine.connect() as conn:
        inspector = inspect(engine)
        dialect = engine.dialect.name  # 'sqlite' or 'postgresql'

        # study_records columns
        existing_sr = {c["name"] for c in inspector.get_columns("study_records")}
        for col, col_type_sqlite, col_type_pg in [
            ("easiness_factor", "FLOAT DEFAULT 2.5", "DOUBLE PRECISION DEFAULT 2.5"),
            ("interval", "INTEGER DEFAULT 0", "INTEGER DEFAULT 0"),
            ("repetition", "INTEGER DEFAULT 0", "INTEGER DEFAULT 0"),
            ("user_id", "INTEGER", "INTEGER"),
        ]:
            if col not in existing_sr:
                col_type = col_type_pg if dialect == "postgresql" else col_type_sqlite
                conn.execute(text(f"ALTER TABLE study_records ADD COLUMN {col} {col_type}"))
                conn.commit()

        # words columns
        existing_w = {c["name"] for c in inspector.get_columns("words")}
        for col, col_type_sqlite, col_type_pg in [
            ("user_id", "INTEGER", "INTEGER"),
            ("jlpt_level", "VARCHAR(3)", "VARCHAR(3)"),
        ]:
            if col not in existing_w:
                col_type = col_type_pg if dialect == "postgresql" else col_type_sqlite
                conn.execute(text(f"ALTER TABLE words ADD COLUMN {col} {col_type}"))
                conn.commit()

        # words indexes — create if they don't exist (for pre-existing databases)
        for col in ("japanese", "kana", "chinese"):
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_words_{col} ON words ({col})"))
            conn.commit()

        # words — image_base64 column (added for AI image generation feature)
        existing_w_img = {c["name"] for c in inspector.get_columns("words")}
        if "image_base64" not in existing_w_img:
            col_type = "TEXT" if dialect == "postgresql" else "TEXT"
            conn.execute(text(f"ALTER TABLE words ADD COLUMN image_base64 {col_type}"))
            conn.commit()

        # users columns
        existing_u = {c["name"] for c in inspector.get_columns("users")}
        for col, col_type_sqlite, col_type_pg in [
            ("is_admin", "BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE"),
            ("token_version", "INTEGER DEFAULT 0", "INTEGER DEFAULT 0"),
            ("daily_ai_limit", "INTEGER", "INTEGER"),
            ("daily_voice_limit", "INTEGER", "INTEGER"),
            ("daily_image_limit", "INTEGER", "INTEGER"),
        ]:
            if col not in existing_u:
                col_type = col_type_pg if dialect == "postgresql" else col_type_sqlite
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {col_type}"))
                conn.commit()

        # usage_records table
        if "usage_records" not in inspector.get_table_names():
            if dialect == "postgresql":
                conn.execute(
                    text("""
                    CREATE TABLE usage_records (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        kind VARCHAR(20) NOT NULL,
                        tokens_used INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                )
            else:
                conn.execute(
                    text("""
                    CREATE TABLE usage_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        kind VARCHAR(20) NOT NULL,
                        tokens_used INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_records(user_id)")
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_usage_kind ON usage_records(kind)"))
            conn.commit()

        # essays table
        if "essays" not in inspector.get_table_names():
            if dialect == "postgresql":
                conn.execute(
                    text("""
                    CREATE TABLE essays (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title VARCHAR(200) NOT NULL,
                        content VARCHAR(5000) NOT NULL,
                        chinese_translation VARCHAR(5000) NOT NULL,
                        topics VARCHAR(500) NOT NULL,
                        words_used VARCHAR(2000) NOT NULL,
                        word_count INTEGER DEFAULT 300,
                        jlpt_level VARCHAR(3) DEFAULT 'N3',
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                )
            else:
                conn.execute(
                    text("""
                    CREATE TABLE essays (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title VARCHAR(200) NOT NULL,
                        content VARCHAR(5000) NOT NULL,
                        chinese_translation VARCHAR(5000) NOT NULL,
                        topics VARCHAR(500) NOT NULL,
                        words_used VARCHAR(2000) NOT NULL,
                        word_count INTEGER DEFAULT 300,
                        jlpt_level VARCHAR(3) DEFAULT 'N3',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_essays_user ON essays(user_id)")
            )
            conn.commit()

        # clozes table
        if "clozes" not in inspector.get_table_names():
            if dialect == "postgresql":
                conn.execute(
                    text("""
                    CREATE TABLE clozes (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title VARCHAR(200) NOT NULL,
                        passage VARCHAR(5000) NOT NULL,
                        blanks VARCHAR(5000) NOT NULL,
                        chinese_translation VARCHAR(5000) NOT NULL,
                        topics VARCHAR(500) NOT NULL,
                        length INTEGER DEFAULT 400,
                        jlpt_level VARCHAR(3) DEFAULT 'N3',
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                )
            else:
                conn.execute(
                    text("""
                    CREATE TABLE clozes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title VARCHAR(200) NOT NULL,
                        passage VARCHAR(5000) NOT NULL,
                        blanks VARCHAR(5000) NOT NULL,
                        chinese_translation VARCHAR(5000) NOT NULL,
                        topics VARCHAR(500) NOT NULL,
                        length INTEGER DEFAULT 400,
                        jlpt_level VARCHAR(3) DEFAULT 'N3',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_clozes_user ON clozes(user_id)")
            )
            conn.commit()

        # achievements table
        if "achievements" not in inspector.get_table_names():
            if dialect == "postgresql":
                conn.execute(
                    text("""
                    CREATE TABLE achievements (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        key VARCHAR(50) NOT NULL,
                        achieved_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(user_id, key)
                    )
                """)
                )
            else:
                conn.execute(
                    text("""
                    CREATE TABLE achievements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        key VARCHAR(50) NOT NULL,
                        achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, key)
                    )
                """)
                )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_achievements_user ON achievements(user_id)")
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_achievements_key ON achievements(key)")
            )
            conn.commit()

        # login_history table
        if "login_history" not in inspector.get_table_names():
            if dialect == "postgresql":
                conn.execute(
                    text("""
                    CREATE TABLE login_history (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        ip_address VARCHAR(45),
                        user_agent VARCHAR(500),
                        login_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                )
            else:
                conn.execute(
                    text("""
                    CREATE TABLE login_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        ip_address VARCHAR(45),
                        user_agent VARCHAR(500),
                        login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_login_history_user ON login_history(user_id)")
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_login_history_time ON login_history(login_at)")
            )
            conn.commit()

        # ── Backfill orphaned rows ──
        _backfill_orphans(conn, dialect)


def _backfill_orphans(conn, dialect: str):
    """Assign rows with NULL user_id to the first admin user.

    When the user_id column was added to words and study_records,
    existing rows got NULL.  Without a backfill those rows become
    invisible — every query in the app filters by user_id.
    """
    tables = ["words", "study_records"]
    orphan_counts = {}

    for table in tables:
        try:
            result = conn.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE user_id IS NULL")
            ).scalar()
            if result:
                orphan_counts[table] = result
        except Exception:
            pass

    if not orphan_counts:
        return

    total = sum(orphan_counts.values())

    # Find the first admin to adopt orphaned data
    admin_row = conn.execute(
        text("SELECT id, username FROM users WHERE is_admin = 1 ORDER BY id LIMIT 1")
    ).first()

    if admin_row is None:
        print(
            "\n"
            + "=" * 64
            + "\n"
            f"  WARNING: Found {total} orphaned rows across {list(orphan_counts.keys())}\n"
            "  (user_id is NULL — data added before multi-user support).\n"
            "  No admin user exists yet, so these rows cannot be auto-assigned.\n"
            "  They will remain invisible until manually assigned.\n"
            "  To recover: create an admin user, then run:\n"
            "    UPDATE words SET user_id = <admin_id> WHERE user_id IS NULL;\n"
            "    UPDATE study_records SET user_id = <admin_id> WHERE user_id IS NULL;\n"
            + "=" * 64
            + "\n",
            file=sys.stderr,
        )
        return

    admin_id, admin_name = admin_row

    for table, count in orphan_counts.items():
        conn.execute(
            text(f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL"),
            {"uid": admin_id},
        )
        conn.commit()

    print(
        "\n"
        + "=" * 64
        + "\n"
        f"  Migration: assigned {total} orphaned rows to admin '{admin_name}' (id={admin_id}):\n"
        + "".join(f"    {t}: {c} rows\n" for t, c in orphan_counts.items())
        + "  These rows are now visible to this admin user.\n"
        + "=" * 64
        + "\n",
        file=sys.stderr,
    )


def get_db():
    """FastAPI 依赖：为每个请求创建一个数据库会话，请求结束后自动关闭。

    用法：
        @app.get("/something")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
