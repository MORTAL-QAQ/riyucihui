# -*- coding: utf-8 -*-
"""导出问卷定义为 JSON（供前端渲染回归测试使用）。

用法：cd backend && python dev_tools/dump_questionnaires.py [输出路径]
默认输出：../docs/_qq_defs.json
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import questionnaires as qq  # noqa: E402


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "docs", "_qq_defs.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    data = [
        {
            "code": q["code"], "number": q["number"], "name": q["name"],
            "version": q["version"], "audience": q["audience"], "timing": q["timing"],
            "minutes": q["minutes"], "intro": q["intro"], "outro": q["outro"],
            "pages": q["pages"], "dimensions": q.get("dimensions", {}),
            "reverse": q.get("reverse", []),
        }
        for q in qq.list_questionnaires()
    ]
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"已导出 {len(data)} 份问卷定义 → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
