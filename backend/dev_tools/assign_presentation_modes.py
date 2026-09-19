# -*- coding: utf-8 -*-
"""按「模态分配方案」批量设置实验词单的词级呈现模式（教师用）。

被试内设计的核心操纵变量是**词的呈现模式**：每份实验词单 20 词中，
10 词为「图文音」（显示配图 + 发音）、10 词为「纯文字」（不显示配图/发音）。
本脚本把论文《实验词单80词示例》里的「模态分配方案」表落到平台数据上。

## 用法

    # 1) 先看某词单现有词与序号（确认分配表的序号对应关系）
    python dev_tools/assign_presentation_modes.py list --user 教师账号 --topic "实验:学校生活"

    # 2) 按序号批量绑定（给出图文音词的序号，其余自动置为纯文字）
    python dev_tools/assign_presentation_modes.py apply --user 教师账号 \
        --topic "实验:学校生活" --multimodal 1,4,6,7,9,12,14,16,17,20

    # 3) 导出「词-模态绑定表」CSV（供 score_vocab_test.py 计分用）
    python dev_tools/assign_presentation_modes.py export --out docs/绑定表.csv

    # 4) 校验：每词单是否恰为 10 图文音 + 10 纯文字
    python dev_tools/assign_presentation_modes.py check

## 说明

- 序号 = 该词单内单词按 `id` 升序排列的位次（与平台词库/PDF 导出顺序一致）。
- 绑定是**词级**的：同一词对所有被试呈现模式一致，避免词—模态混淆。
- 脚本直接读写数据库（不经 HTTP），故可在服务器容器内运行：
    docker compose exec -T -e PYTHONPATH=/app -w /app backend \
        python /app/dev_tools/assign_presentation_modes.py check
"""
import argparse
import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.database import SessionLocal            # noqa: E402
from app.models import User, Word                # noqa: E402
from app.services.experiment import (            # noqa: E402
    MODE_MULTIMODAL,
    MODE_TEXT_ONLY,
    is_locked_topic,
    mode_label,
)


def _words_of(db, user: User, topic: str):
    return (
        db.query(Word)
        .filter(Word.user_id == user.id, Word.topic == topic)
        .order_by(Word.id)
        .all()
    )


def _resolve_user(db, username: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        print(f"[错误] 找不到账号：{username}", file=sys.stderr)
        sys.exit(2)
    return user


def _parse_indexes(text: str) -> list:
    out = []
    for part in text.replace("，", ",").replace("、", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit():
            print(f"[错误] 序号必须为正整数：{part!r}", file=sys.stderr)
            sys.exit(2)
        out.append(int(part))
    return out


def cmd_list(args) -> int:
    db = SessionLocal()
    try:
        user = _resolve_user(db, args.user)
        words = _words_of(db, user, args.topic)
        if not words:
            print(f"[错误] 账号 {args.user} 下没有词单「{args.topic}」", file=sys.stderr)
            return 2
        print(f"词单「{args.topic}」共 {len(words)} 词（账号 {args.user}）：")
        for i, w in enumerate(words, 1):
            print(f"  {i:>3}. {w.japanese:<10} {w.kana:<14} {w.chinese:<12} "
                  f"呈现模式={mode_label(w.presentation_mode)}")
        mm = sum(1 for w in words if (w.presentation_mode or "") == MODE_MULTIMODAL)
        tx = sum(1 for w in words if (w.presentation_mode or "") == MODE_TEXT_ONLY)
        print(f"\n统计：图文音 {mm} 词、纯文字 {tx} 词、未指定 {len(words) - mm - tx} 词")
        return 0
    finally:
        db.close()


def cmd_apply(args) -> int:
    db = SessionLocal()
    try:
        user = _resolve_user(db, args.user)
        words = _words_of(db, user, args.topic)
        if not words:
            print(f"[错误] 账号 {args.user} 下没有词单「{args.topic}」", file=sys.stderr)
            return 2

        idx = _parse_indexes(args.multimodal)
        n = len(words)
        bad = [i for i in idx if i < 1 or i > n]
        if bad:
            print(f"[错误] 序号超出范围（该词单共 {n} 词）：{bad}", file=sys.stderr)
            return 2
        mm = set(idx)
        if args.expect and len(mm) != args.expect:
            print(f"[错误] 图文音词数 {len(mm)} ≠ 预期 {args.expect}"
                  f"（--expect 未加 --force 时不允许写入）", file=sys.stderr)
            if not args.force:
                return 2

        for i, w in enumerate(words, 1):
            w.presentation_mode = MODE_MULTIMODAL if i in mm else MODE_TEXT_ONLY
        db.commit()

        print(f"已设置「{args.topic}」共 {n} 词："
              f"图文音 {len(mm)} 词、纯文字 {n - len(mm)} 词")
        print("  图文音：" + "、".join(f"{i}.{words[i-1].japanese}" for i in sorted(mm)))
        tx = [i for i in range(1, n + 1) if i not in mm]
        print("  纯文字：" + "、".join(f"{i}.{words[i-1].japanese}" for i in tx))
        if is_locked_topic(args.topic):
            print("  （实验词单：已按 EXPERIMENT_TOPIC_OPEN 决定是否向全体被试开放）")
        return 0
    finally:
        db.close()


def cmd_check(args) -> int:
    """校验每个实验词单是否恰为 10 图文音 + 10 纯文字（被试内设计的前提）。"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        bad = 0
        checked = 0
        for user in users:
            topics = [
                t for (t,) in db.query(Word.topic).filter(Word.user_id == user.id)
                .distinct().all()
            ]
            for topic in topics:
                if not is_locked_topic(topic):
                    continue
                words = _words_of(db, user, topic)
                mm = sum(1 for w in words if (w.presentation_mode or "") == MODE_MULTIMODAL)
                tx = sum(1 for w in words if (w.presentation_mode or "") == MODE_TEXT_ONLY)
                none = len(words) - mm - tx
                checked += 1
                ok = (mm == tx == len(words) // 2) and none == 0 and len(words) % 2 == 0
                flag = "✓" if ok else "✗"
                if not ok:
                    bad += 1
                print(f"  {flag} {user.username} / {topic}：共 {len(words)} 词，"
                      f"图文音 {mm}、纯文字 {tx}、未指定 {none}")
        print()
        if checked == 0:
            print("没有发现实验词单（主题以「实验:」开头）。")
            return 0
        if bad:
            print(f"FAIL：{bad}/{checked} 个实验词单的模态绑定不符合「各半」要求"
                  f"（图文音与纯文字应各占一半且无未指定）")
            return 1
        print(f"PASS：{checked} 个实验词单的模态绑定均符合「图文音与纯文字各半」")
        return 0
    finally:
        db.close()


def cmd_export(args) -> int:
    """导出「词-模态绑定表」CSV（列：主题,序号,单词,假名,呈现模式）。"""
    db = SessionLocal()
    try:
        q = db.query(Word)
        if args.user:
            q = q.filter(Word.user_id == _resolve_user(db, args.user).id)
        if args.topic:
            q = q.filter(Word.topic == args.topic)
        words = q.order_by(Word.topic, Word.id).all()
        if not words:
            print("[错误] 没有可导出的单词", file=sys.stderr)
            return 2

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["主题", "序号", "单词", "假名", "呈现模式"])
        counters = {}
        for w in words:
            counters[w.topic] = counters.get(w.topic, 0) + 1
            writer.writerow([w.topic, counters[w.topic], w.japanese, w.kana,
                             mode_label(w.presentation_mode)])
        out = args.out
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with io.open(out, "w", encoding="utf-8-sig", newline="") as f:
            f.write(buf.getvalue())
        print(f"已导出 {len(words)} 行 → {out}")
        print("（可直接作为 score_vocab_test.py 的 --bindings 输入）")
        return 0
    finally:
        db.close()


def cmd_distribute(args) -> int:
    """把模板账号下的一份词单**分发到多个被试账号**（含呈现模式与配图）。

    为什么需要：平台的单词是按账号（`Word.user_id`）存储的，而控制实验要求
    全班学生学**完全相同的词表与相同的模态分配**，不能各自用 AI 生成
    （生成结果随机，会破坏材料等价性）。故流程为：
    ① 教师在模板账号下准备好词单并绑定模态 → ② 本命令分发到全体被试账号。

    幂等：同一账号下若已存在同名词单且同名单词，则跳过（不重复插入）。
    """
    db = SessionLocal()
    try:
        src_user = _resolve_user(db, args.src_user)
        src_words = _words_of(db, src_user, args.topic)
        if not src_words:
            print(f"[错误] 模板账号 {args.src_user} 下没有词单「{args.topic}」", file=sys.stderr)
            return 2

        mm = sum(1 for w in src_words if (w.presentation_mode or "") == MODE_MULTIMODAL)
        if args.require_balanced and mm * 2 != len(src_words):
            print(f"[错误] 模板词单模态未按「各半」绑定（图文音 {mm} / 共 {len(src_words)}）；"
                  f"先用 apply 绑定，或加 --no-require-balanced 跳过检查", file=sys.stderr)
            return 2

        if args.to:
            names = [n.strip() for n in args.to.replace("，", ",").split(",") if n.strip()]
            targets = [_resolve_user(db, n) for n in names]
        else:
            targets = [
                u for u in db.query(User).filter(User.is_admin == False).all()  # noqa: E712
                if u.id != src_user.id
            ]
        if not targets:
            print("[错误] 没有目标账号", file=sys.stderr)
            return 2

        print(f"模板：{args.src_user} / {args.topic}，共 {len(src_words)} 词"
              f"（图文音 {mm}、纯文字 {len(src_words) - mm}）")
        print(f"目标账号 {len(targets)} 个；{'试运行（不写入）' if args.dry_run else '开始分发'}"
              f"{'；不复制配图' if args.skip_images else ''}")
        print()

        created_total = skipped_total = synced_total = 0
        for t in targets:
            existing = {w.japanese: w for w in _words_of(db, t, args.topic)}
            created = skipped = synced = 0
            for w in src_words:
                old = existing.get(w.japanese)
                if old is not None:
                    skipped += 1
                    # 自愈：已存在的同名词对齐模板的呈现模式（避免出现「未指定」残留）
                    if (old.presentation_mode or "") != (w.presentation_mode or ""):
                        if not args.dry_run:
                            old.presentation_mode = w.presentation_mode
                        synced += 1
                    continue
                new = Word(
                    user_id=t.id,
                    topic=args.topic,
                    japanese=w.japanese,
                    kana=w.kana,
                    chinese=w.chinese,
                    example_ja=w.example_ja,
                    example_cn=w.example_cn,
                    jlpt_level=w.jlpt_level,
                    presentation_mode=w.presentation_mode,
                    image_base64=None if args.skip_images else w.image_base64,
                )
                db.add(new)
                created += 1
            if not args.dry_run:
                db.commit()
            created_total += created
            skipped_total += skipped
            synced_total += synced
            print(f"  {t.username:<16} 新增 {created:>2} 词、已存在 {skipped:>2} 词"
                  f"（其中同步模态 {synced} 词）")

        print()
        print(f"{'[试运行] 将' if args.dry_run else '已'}分发 {created_total} 条词记录"
              f"（已存在 {skipped_total} 条，其中同步模态 {synced_total} 条）")
        if not args.dry_run:
            print("下一步：python dev_tools/assign_presentation_modes.py check")
        return 0
    finally:
        db.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="批量设置/校验/导出/分发 词的呈现模式（被试内实验）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="列出某词单的词与序号")
    p.add_argument("--user", required=True, help="教师/管理员账号（用户名）")
    p.add_argument("--topic", required=True)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("apply", help="按序号批量绑定呈现模式")
    p.add_argument("--user", required=True)
    p.add_argument("--topic", required=True)
    p.add_argument("--multimodal", required=True,
                   help="图文音词的序号，逗号/顿号分隔（如 1,4,6,7,9,12,14,16,17,20）")
    p.add_argument("--expect", type=int, default=10, help="预期图文音词数（默认 10）")
    p.add_argument("--force", action="store_true", help="数量不符时仍写入")
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("check", help="校验每个实验词单是否各半")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("export", help="导出词-模态绑定表 CSV")
    p.add_argument("--out", default="docs/词-模态绑定表.csv")
    p.add_argument("--user", default=None)
    p.add_argument("--topic", default=None)
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("distribute", help="把模板账号的词单分发到多个被试账号（含模态与配图）")
    p.add_argument("--src-user", required=True, help="模板账号（教师账号）")
    p.add_argument("--topic", required=True)
    p.add_argument("--to", default=None, help="目标账号，逗号分隔；省略=全部非管理员账号")
    p.add_argument("--skip-images", action="store_true", help="不复制配图（可大幅减小库体积）")
    p.add_argument("--dry-run", action="store_true", help="只统计不写入")
    p.add_argument("--no-require-balanced", dest="require_balanced", action="store_false",
                   help="不检查模板是否已按各半绑定")
    p.set_defaults(func=cmd_distribute, require_balanced=True)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
