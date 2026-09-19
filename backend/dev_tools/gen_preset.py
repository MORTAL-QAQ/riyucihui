# -*- coding: utf-8 -*-
"""生成预置实验套题（20 词 = 10 多模态 + 10 非多模态，并生成多模态配图）。

在 backend 容器内执行：
    docker compose exec -T -e PYTHONPATH=/app -w /app backend \
        python /tmp/gen_preset.py "套题 A · 食物料理" "食物料理" N3

可断点续跑：已存在同名套题时复用，仅补齐缺失的配图。
"""
import sys
import random

from app.database import SessionLocal
from app.models import ExperimentPreset, ExperimentPresetWord
from app.services.ai_service import generate_words
from app.services.image_service import generate_word_image

TOTAL = 20
MM = 10

name = sys.argv[1] if len(sys.argv) > 1 else "套题 A · 食物料理"
topic = sys.argv[2] if len(sys.argv) > 2 else "食物料理"
level = sys.argv[3] if len(sys.argv) > 3 else "N3"

db = SessionLocal()

preset = db.query(ExperimentPreset).filter(ExperimentPreset.name == name).first()
if not preset:
    print(f"[1/3] 生成 {TOTAL} 个单词（领域：{topic}）...")
    words, _tokens = generate_words(topic, level, None, TOTAL, None)
    if not words or len(words) < TOTAL:
        print(f"❌ 生成数量不足：{len(words) if words else 0}")
        sys.exit(1)
    words = words[:TOTAL]
    random.shuffle(words)

    preset = ExperimentPreset(name=name, topic=topic, word_count=TOTAL,
                              multimodal_count=MM, is_active=True)
    db.add(preset)
    db.flush()

    for i, w in enumerate(words):
        is_mm = i < MM
        db.add(ExperimentPresetWord(
            preset_id=preset.id,
            is_multimodal=is_mm,
            japanese=str(w.get("japanese", ""))[:100],
            kana=str(w.get("kana", ""))[:200],
            chinese=str(w.get("chinese", ""))[:200],
            example_ja=(str(w.get("example_ja", ""))[:500] if is_mm else None),
            example_cn=(str(w.get("example_cn", ""))[:500] if is_mm else None),
            image_pending=is_mm,   # 多模态组待配图
        ))
    db.commit()
    print(f"    套题已创建：id={preset.id}")
else:
    print(f"[1/3] 套题「{name}」已存在（id={preset.id}），检查配图...")

# ── 逐张补齐多模态配图（断点续跑） ──
pending = db.query(ExperimentPresetWord).filter(
    ExperimentPresetWord.preset_id == preset.id,
    ExperimentPresetWord.is_multimodal == True,   # noqa: E712
    ExperimentPresetWord.image_base64.is_(None),
).all()

if pending:
    print(f"[2/3] 生成配图 {len(pending)} 张（每张约 10-30 秒）...")
    for idx, pw in enumerate(pending, 1):
        try:
            img = generate_word_image(pw.japanese, pw.chinese, pw.kana,
                                      pw.example_ja or "", pw.example_cn or "")
        except Exception as exc:
            print(f"    [{idx}/{len(pending)}] {pw.japanese} 配图失败：{exc}")
            continue
        if img:
            pw.image_base64 = img
            pw.image_pending = False
            db.commit()
            print(f"    [{idx}/{len(pending)}] {pw.japanese} ✅ ({len(img)} bytes)")
        else:
            print(f"    [{idx}/{len(pending)}] {pw.japanese} 返回空图")
else:
    print("[2/3] 配图已齐备，跳过")

# ── 汇总 ──
rows = db.query(ExperimentPresetWord).filter(
    ExperimentPresetWord.preset_id == preset.id
).all()
mm_rows = [r for r in rows if r.is_multimodal]
with_img = [r for r in mm_rows if r.image_base64]
print(f"[3/3] 套题「{preset.name}」：{len(rows)} 词（多模态 {len(mm_rows)}，其中配图 {len(with_img)} 张）")
print(f"    领域：{preset.topic} | 可用于新实验：{preset.is_active}")
db.close()
