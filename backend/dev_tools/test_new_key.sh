#!/bin/bash
# 实测新 API Key 在方舟图片生成端点的可用鉴权形式
set -u
KEYFILE="/tmp/keytest/ApiKey.txt"
BASE="https://ark.cn-beijing.volces.com/api/v3"
MODEL="doubao-seedream-5-0-260128"

ID=$(grep -i 'API Key ID' "$KEYFILE" | sed 's/.*: *//' | tr -d '\r\n ')
SECRET=$(grep -i 'API Key Secret' "$KEYFILE" | sed 's/.*: *//' | tr -d '\r\n ')
echo "ID 长度: ${#ID} | Secret 长度: ${#SECRET}"
echo ""

PROMPT='{"model":"'"$MODEL"'","prompt":"a red apple on a wooden table, photorealistic","sequential_image_generation":"disabled","response_format":"url","size":"2K","stream":false,"watermark":true}'

test_auth() {
  local label="$1"; local token="$2"
  local code
  code=$(curl -s -o /tmp/keytest/resp.json -w '%{http_code}' --max-time 90 \
    -X POST "$BASE/images/generations" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $token" \
    -d "$PROMPT")
  local head
  head=$(head -c 160 /tmp/keytest/resp.json | tr -d '\n')
  echo "[$label] HTTP $code | $head"
}

echo "=== 形式 1：Bearer + Secret ==="
test_auth "secret-only" "$SECRET"
echo ""
echo "=== 形式 2：Bearer + ID ==="
test_auth "id-only" "$ID"
echo ""
echo "=== 形式 3：Bearer + ID.Secret ==="
test_auth "id.secret" "$ID.$SECRET"
echo ""
echo "=== 对照：现有生产 key ==="
OLDKEY=$(cat /opt/riyucihui/secrets/VOLCANO_API_KEY 2>/dev/null | tr -d '\r\n')
test_auth "current-prod-key" "$OLDKEY"
