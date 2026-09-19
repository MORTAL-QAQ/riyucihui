#!/bin/bash
BASE="https://127.0.0.1"
U="plist_$(date +%s)"
TOKEN=$(curl -sk -X POST "$BASE/api/register" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$U\",\"password\":\"Pre123456\"}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')
echo "=== 套题列表接口 ==="
curl -sk "$BASE/api/experiment/presets" -H "Authorization: Bearer $TOKEN" > /tmp/presets.json
python3 - << 'PYEOF'
import json
d = json.load(open('/tmp/presets.json'))
ps = d.get("presets", [])
print("套题数量:", len(ps))
for p in ps:
    print("  #%s %s | %s | %s 词（多模态 %s）" % (p["preset_id"], p["name"], p["topic"], p["word_count"], p["multimodal_count"]))
assert len(ps) >= 2, "应至少两套"
print("列表接口正常 ✅")
PYEOF
cd /opt/riyucihui
docker compose exec -T postgres psql -U jpvocab -d jpvocab -c "DELETE FROM users WHERE username LIKE 'plist_%';" 2>&1 | tail -1
