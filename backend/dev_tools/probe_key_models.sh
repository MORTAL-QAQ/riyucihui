#!/bin/bash
# 探测新 key（Secret 作为 Bearer）可用的图片生成模型
set -u
KEYFILE="/tmp/keytest/ApiKey.txt"
BASE="https://ark.cn-beijing.volces.com/api/v3"
SECRET=$(grep -i 'API Key Secret' "$KEYFILE" | sed 's/.*: *//' | tr -d '\r\n ')

echo "=== 1. 列出可用模型 ==="
curl -s --max-time 30 -H "Authorization: Bearer $SECRET" "$BASE/models" | head -c 400
echo ""
echo ""

for M in doubao-seedream-5-0-260128 doubao-seedream-4-0-250828 doubao-seedream-3-0-t2i-250415 doubao-seededit-3-0-i2i-250628; do
  code=$(curl -s -o /tmp/keytest/m.json -w '%{http_code}' --max-time 90 \
    -X POST "$BASE/images/generations" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $SECRET" \
    -d "{\"model\":\"$M\",\"prompt\":\"a red apple on a wooden table, photorealistic\",\"sequential_image_generation\":\"disabled\",\"response_format\":\"url\",\"size\":\"2K\",\"stream\":false,\"watermark\":true}")
  msg=$(head -c 120 /tmp/keytest/m.json | tr -d '\n')
  echo "[$M] HTTP $code | $msg"
done
