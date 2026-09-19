#!/bin/bash
set -u
KEYFILE="/tmp/keytest/ApiKey.txt"
BASE="https://ark.cn-beijing.volces.com/api/v3"
SECRET=$(grep -i 'API Key Secret' "$KEYFILE" | sed 's/.*: *//' | tr -d '\r\n ')

curl -s --max-time 30 -H "Authorization: Bearer $SECRET" "$BASE/models" > /tmp/keytest/models.json

echo "=== 该 key 可见模型总数 ==="
python3 -c "
import json
d = json.load(open('/tmp/keytest/models.json'))
items = d.get('data', [])
print('总数:', len(items))
print()
print('=== 图片/视觉类模型（seed / image / vision）===')
for m in items:
    mid = m.get('id','')
    if any(k in mid.lower() for k in ('seedream','seeded','image','vision','t2i','i2i')):
        print(' ', mid, '| status:', m.get('status'))
print()
print('=== 全部模型 id（前 60 个）===')
for m in items[:60]:
    print(' ', m.get('id',''), '|', m.get('status'))
"
