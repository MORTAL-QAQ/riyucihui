# -*- coding: utf-8 -*-
"""提取两份成绩表的学生（学号, 姓名）并输出 JSON。"""
import io
import json

import xlrd

FILES = [
    r"C:\Users\Administrator\Desktop\11\日语阅读学生成绩录入模板[徐明]1.xls",
    r"C:\Users\Administrator\Desktop\11\日语阅读学生成绩录入模板[徐明] (2).xls",
]

students = []
seen = set()
for f in FILES:
    wb = xlrd.open_workbook(f)
    sh = wb.sheet_by_index(0)
    # 表头：序号 | 班级 | 学号 | 姓名
    for r in range(1, sh.nrows):
        cls = str(sh.cell_value(r, 1)).strip()
        sid = str(sh.cell_value(r, 2)).strip()
        name = str(sh.cell_value(r, 3)).strip()
        if not sid or not name:
            continue
        if sid in seen:
            print(f"跳过重复学号: {sid} {name}")
            continue
        seen.add(sid)
        students.append({"sid": sid, "name": name, "cls": cls})

out = r"C:\Users\Administrator\Desktop\11\backend\dev_tools\students.json"
io.open(out, "w", encoding="utf-8", newline="\n").write(
    json.dumps(students, ensure_ascii=False, indent=1)
)
print(f"共提取 {len(students)} 名学生 → {out}")
for s in students[:5]:
    print(" ", s["cls"], s["sid"], s["name"])
print("  ...")
for s in students[-3:]:
    print(" ", s["cls"], s["sid"], s["name"])
