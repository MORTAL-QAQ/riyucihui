#!/bin/bash
# 生产故障诊断：实测 voicevox 合成 + DeepSeek 连通
cd /opt/riyucihui
echo "=== 1. voicevox audio_query ==="
curl -s -X POST 'http://voicevox:50021/audio_query?text=%E3%81%93%E3%82%93%E3%81%AB%E3%81%A1%E3%81%AF&speaker=1' -H 'Content-Type: application/json' -d '{}' -o /tmp/aq.json -w 'audio_query:%{http_code}\n' 2>&1 || echo "aq fail"
echo "=== 2. voicevox synthesis ==="
if [ -s /tmp/aq.json ]; then
  curl -s -X POST 'http://voicevox:50021/synthesis?speaker=1' -H 'Content-Type: application/json' -d @/tmp/aq.json -o /tmp/out.wav -w 'synthesis:%{http_code} size:%{size_download}\n' 2>&1 || echo "synth fail"
fi
echo "=== 3. DeepSeek 连通（容器内读 secrets）==="
docker compose exec -T backend sh -c 'KEY=$(cat /run/secrets/DEEPSEEK_API_KEY 2>/dev/null || echo "NO_SECRET"); echo "key_len:${#KEY}"; curl -s -o /dev/null -w "deepseek_http:%{http_code}\n" --max-time 20 -X POST https://api.deepseek.com/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer $KEY" -d "{\"model\":\"deepseek-chat\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":5}" 2>&1 || echo "deepseek curl fail"'
