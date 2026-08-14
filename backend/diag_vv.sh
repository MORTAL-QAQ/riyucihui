#!/bin/bash
cd /opt/riyucihui
docker compose exec -T backend sh -c 'curl -s -X POST "http://voicevox:50021/audio_query?text=konnichiwa&speaker=1" -H "Content-Type: application/json" -d "{}" -o /tmp/aq.json -w "audio_query:%{http_code}\n" && if [ -s /tmp/aq.json ]; then curl -s -X POST "http://voicevox:50021/synthesis?speaker=1" -H "Content-Type: application/json" -d @/tmp/aq.json -o /tmp/out.wav -w "synthesis:%{http_code} size:%{size_download}\n"; fi'
