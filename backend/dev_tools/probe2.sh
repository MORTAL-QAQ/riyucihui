#!/bin/bash
set -u
KEYFILE="/tmp/keytest/ApiKey.txt"
BASE="https://ark.cn-beijing.volces.com/api/v3"
SECRET=$(grep -i 'API Key Secret' "$KEYFILE" | sed 's/.*: *//' | tr -d '\r\n ')

for M in doubao-seedream-5-0-pro-260628 doubao-seedream-4-5-251128 doubao-seedream-4-0-20260415; do
  code=$(curl -s -o /tmp/keytest/m2.json -w '%{http_code}' --max-time 120 \
    -X POST "$BASE/images/generations" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $SECRET" \
    -d "{\"model\":\"$M\",\"prompt\":\"a red apple on a wooden table, photorealistic\",\"sequential_image_generation\":\"disabled\",\"response_format\":\"url\",\"size\":\"2K\",\"stream\":false,\"watermark\":true}")
  msg=$(head -c 150 /tmp/keytest/m2.json | tr -d '\n')
  echo "[$M] HTTP $code | $msg"
done

echo ""
echo "=== 用现有生产 key 试同一组模型作对照 ==="
OLDKEY=$(cat /opt/riyucihui/secrets/VOLCANO_API_KEY | tr -d '\r\n')
for M in doubao-seedream-5-0-pro-260628 doubao-seedream-4-5-251128; do
  code=$(curl -s -o /tmp/keytest/m3.json -w '%{http_code}' --max-time 120 \
    -X POST "$BASE/images/generations" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OLDKEY" \
    -d "{\"model\":\"$M\",\"prompt\":\"a red apple\",\"sequential_image_generation\":\"disabled\",\"response_format\":\"url\",\"size\":\"2K\",\"stream\":false,\"watermark\":true}")
  msg=$(head -c 120 /tmp/keytest/m3.json | tr -d '\n')
  echo "[$M] HTTP $code | $msg"
done
