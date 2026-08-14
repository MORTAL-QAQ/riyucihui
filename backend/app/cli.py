"""Admin management CLI — run from backend/ with: python -m app.cli create-admin <user> <pass>"""

import argparse
from datetime import datetime, timezone

from .auth import hash_password
from .database import SessionLocal, engine
from .models import LoginHistory, User


def backfill_orphans() -> str:
    """把 user_id 为 NULL 的 words/study_records 行分配给第一个管理员（#19）。

    此前该逻辑在应用启动时隐式执行，现已拆出为显式命令，避免启动时静默改数据。
    """
    from sqlalchemy import text

    tables = ["words", "study_records"]
    orphan_counts = {}
    with engine.connect() as conn:
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
            return "没有需要回填的孤儿数据"

        admin_row = conn.execute(
            text("SELECT id, username FROM users WHERE is_admin = 1 ORDER BY id LIMIT 1")
        ).first()
        if admin_row is None:
            return (
                "存在孤儿数据但无管理员用户：请先运行 create-admin，"
                "然后手动执行 UPDATE words/study_records SET user_id=<admin_id> WHERE user_id IS NULL"
            )

        admin_id, admin_name = admin_row
        for table, count in orphan_counts.items():
            conn.execute(
                text(f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL"),
                {"uid": admin_id},
            )
            conn.commit()

    detail = "、".join(f"{t}: {c} 行" for t, c in orphan_counts.items())
    return f"已将孤儿数据分配给管理员 {admin_name} (id={admin_id})：{detail}"


def create_admin(username: str, password: str) -> str:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user:
            user.is_admin = True
            user.password_hash = hash_password(password)
            db.commit()
            return f"用户 {username} 已是管理员（密码已更新）"
        user = User(
            username=username,
            password_hash=hash_password(password),
            is_admin=True,
        )
        db.add(user)
        db.commit()
        return f"管理员 {username} 创建成功 (id={user.id})"
    finally:
        db.close()


def list_users() -> str:
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.id).all()
        if not users:
            return "(no users)"
        lines = [f"{'ID':>4}  {'Admin':>5}  Username"]
        for u in users:
            lines.append(f"{u.id:>4}  {str(u.is_admin):>5}  {u.username}")
        return "\n".join(lines)
    finally:
        db.close()


def login_report(username: str | None = None) -> str:
    """生成每个用户的登录历史报告。

    每个用户一张表格，包含每次登录时间和累计登录次数。
    可通过 username 参数筛选单个用户。
    """
    db = SessionLocal()
    try:
        # 查询所有用户的登录记录
        query = (
            db.query(
                LoginHistory.user_id,
                User.username,
                LoginHistory.login_at,
                LoginHistory.ip_address,
            )
            .join(User, LoginHistory.user_id == User.id)
            .order_by(LoginHistory.user_id, LoginHistory.login_at)
        )

        if username:
            query = query.filter(User.username == username)

        records = query.all()

        if not records:
            return f"(没有找到 {'用户 ' + username + ' 的' if username else ''}登录记录)"

        # 按用户分组
        from collections import defaultdict

        user_logins: dict[int, dict] = defaultdict(lambda: {"username": "", "logins": []})

        for user_id, uname, login_at, ip_addr in records:
            user_logins[user_id]["username"] = uname
            user_logins[user_id]["logins"].append((login_at, ip_addr))

        lines = []
        lines.append("=" * 78)
        lines.append("  用户登录历史报告")
        lines.append(f"  生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("=" * 78)

        # 按最后一次登陆时间降序排列用户
        sorted_users = sorted(
            user_logins.items(),
            key=lambda item: item[1]["logins"][-1][0] if item[1]["logins"] else datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        for user_id, data in sorted_users:
            uname = data["username"]
            logins = data["logins"]
            total = len(logins)

            lines.append("")
            lines.append(f"  用户: {uname} (ID: {user_id})")
            lines.append(f"  总登录次数: {total}")
            lines.append(f"  {'─' * 70}")
            lines.append(f"  {'序号':<6} {'登录时间':<26} {'IP 地址':<20}")
            lines.append(f"  {'─' * 70}")

            for i, (login_at, ip_addr) in enumerate(logins, 1):
                time_str = login_at.strftime("%Y-%m-%d %H:%M:%S UTC") if login_at else "N/A"
                ip_str = ip_addr or "N/A"
                lines.append(f"  {i:<6} {time_str:<26} {ip_str:<20}")

            lines.append(f"  {'─' * 70}")
            lines.append(f"  合计: {total} 次登录")
            lines.append("")

        lines.append("=" * 78)
        return "\n".join(lines)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="JP Vocab admin CLI")
    sub = parser.add_subparsers(dest="command")

    ca = sub.add_parser("create-admin", help="Create an admin or promote existing user")
    ca.add_argument("username")
    ca.add_argument("password")

    sub.add_parser("list-users", help="List all users")

    lr = sub.add_parser("login-report", help="Generate per-user login history report")
    lr.add_argument("--user", "-u", default=None, help="Show report for a specific username only")

    sub.add_parser("backfill-orphans", help="Assign NULL user_id rows to the first admin (one-time)")

    args = parser.parse_args()

    if args.command == "create-admin":
        print(create_admin(args.username, args.password))
    elif args.command == "list-users":
        print(list_users())
    elif args.command == "login-report":
        print(login_report(args.user))
    elif args.command == "backfill-orphans":
        print(backfill_orphans())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
