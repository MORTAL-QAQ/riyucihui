#!/bin/bash
set -u
cd /opt/riyucihui
docker compose cp /tmp/keytest/ApiKey.txt backend:/tmp/ApiKey.txt

docker compose exec -T -e PYTHONPATH=/app -w /app backend python - << 'PYEOF'
import json
from volcengine.visual.VisualService import VisualService

txt = open("/tmp/ApiKey.txt", encoding="utf-8").read()
ak = sk = ""
for line in txt.splitlines():
    if "API Key ID" in line:
        ak = line.split(":", 1)[1].strip()
    elif "API Key Secret" in line:
        sk = line.split(":", 1)[1].strip()

svc = VisualService()
svc.set_ak(ak)
svc.set_sk(sk)

resp = svc.cv_process({
    "req_key": "high_aes_general_v30",
    "prompt": "a red apple on a wooden table, photorealistic",
    "width": 1024,
    "height": 1024,
    "return_url": True,
})
print("=== 完整响应 ===")
print(json.dumps(resp, ensure_ascii=False, indent=2)[:1500])
PYEOF

docker compose exec -T backend rm -f /tmp/ApiKey.txt
