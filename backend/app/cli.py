"""Admin management CLI — run from backend/ with: python -m app.cli create-admin <user> <pass>"""

import argparse
from datetime import datetime, timezone

from .auth import hash_password
from .database import SessionLocal
from .models import LoginHistory, User


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

        for user_id, data in user_logins.items():
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

    args = parser.parse_args()

    if args.command == "create-admin":
        print(create_admin(args.username, args.password))
    elif args.command == "list-users":
        print(list_users())
    elif args.command == "login-report":
        print(login_report(args.user))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
