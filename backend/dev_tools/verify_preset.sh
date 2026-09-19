#!/bin/bash
# 验证预置套题秒开：学生创建会话应直接返回材料与图片
BASE="https://127.0.0.1"
U="preset_$(date +%s)"

TOKEN=$(curl -sk -X POST "$BASE/api/register" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$U\",\"password\":\"Pre123456\",\"name\":\"套题测试\"}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')

echo "=== 1. 套题列表 ==="
curl -sk "$BASE/api/experiment/presets" -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys, json
d = json.load(sys.stdin)
for p in d.get("presets", []):
    print(f"  #{p[\"preset_id\"]} {p[\"name\"]} | {p[\"topic\"]} | {p[\"word_count\"]} 词（多模态 {p[\"multimodal_count\"]}）")
'

echo "=== 2. 创建会话（计时，套题应秒开） ==="
START=$(date +%s)
curl -sk --max-time 60 -X POST "$BASE/api/experiment/sessions" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"preset_id":1}' > /tmp/preset_session.json
END=$(date +%s)
echo "耗时: $((END-START)) 秒"

python3 - << 'PYEOF'
import json
d = json.load(open('/tmp/preset_session.json'))
print("from_preset:", d.get("from_preset"), "| 套题:", d.get("preset_name"))
words = d.get("words", [])
mm = [w for w in words if w["is_multimodal"]]
pl = [w for w in words if not w["is_multimodal"]]
print(f"单词 {len(words)}（多模态 {len(mm)} / 非多模态 {len(pl)}）")
with_img = [w for w in mm if w.get("image_base64")]
print(f"多模态中已带图片: {len(with_img)}/{len(mm)}")
assert len(words) == 20 and len(with_img) == 10, "预置材料应直接带齐图片"
print("秒开验证通过 ✅（20 词 + 10 图 一次性返回，无需逐张生成）")
PYEOF

echo "=== 3. 清理测试账号 ==="
cd /opt/riyucihui
docker compose exec -T postgres psql -U jpvocab -d jpvocab -c "DELETE FROM users WHERE username LIKE 'preset_%';" 2>&1 | tail -1
echo "=== 4. 套题数据统计 ==="
docker compose exec -T postgres psql -U jpvocab -d jpvocab -c "SELECT p.id, p.name, count(w.id) AS 词数, count(w.image_base64) AS 配图数 FROM experiment_presets p LEFT JOIN experiment_preset_words w ON w.preset_id = p.id GROUP BY p.id, p.name ORDER BY p.id;"
