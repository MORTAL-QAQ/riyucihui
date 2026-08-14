#!/bin/bash
# 端到端实测：注册 → 登录 → 生成 → 发声（走 nginx 完整链路）
BASE="https://127.0.0.1"
U="diag_$(date +%s)"
P="Diag123456"

echo "=== 1. 注册 $U ==="
REG=$(curl -sk -X POST "$BASE/api/register" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$U\",\"password\":\"$P\"}")
echo "$REG" | head -c 120; echo ""
TOKEN=$(echo "$REG" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))' 2>/dev/null)
echo "token_len:${#TOKEN}"

echo "=== 3. 生成单词（SSE，限时 60s）==="
curl -sk --max-time 60 -X POST "$BASE/api/generate" -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"topic":"天气","difficulty":"N3","count":5,"stream":true}' \
  -w '\ngenerate_http:%{http_code}\n' | tail -6

echo "=== 4. 发声（语音合成）==="
curl -sk --max-time 30 -X POST "$BASE/api/voice" -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"text":"こんにちは"}' -o /tmp/voice_test.wav \
  -w 'voice_http:%{http_code} size:%{size_download}\n'
file /tmp/voice_test.wav 2>/dev/null | head -1

echo "=== 5. 清理测试账号（走管理 API 需管理员，改用直接 SQL 提示）==="
echo "测试账号: $U (稍后可手动删除)"
