#!/bin/bash
# 测试火山引擎视觉智能开放平台「通用图像生成 3.0」（AK/SK 签名）
set -u
cd /opt/riyucihui

echo "=== 容器内安装火山 SDK ==="
docker compose exec -T backend pip install -q volcengine 2>&1 | tail -2

echo "=== 上传 key 到容器 ==="
docker compose cp /tmp/keytest/ApiKey.txt backend:/tmp/ApiKey.txt

echo "=== 调用通用图像生成 3.0 ==="
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
print(f"AK len={len(ak)} SK len={len(sk)}")

svc = VisualService()
svc.set_ak(ak)
svc.set_sk(sk)

for req_key in ("high_aes_general_v30", "high_aes_general_v30l", "high_aes_general_v21"):
    try:
        resp = svc.cv_process({
            "req_key": req_key,
            "prompt": "a red apple on a wooden table, photorealistic, natural lighting",
            "width": 1024,
            "height": 1024,
            "return_url": True,
        })
        code = resp.get("code")
        msg = str(resp.get("message"))[:80]
        has_img = bool((resp.get("data") or {}).get("image_urls"))
        print(f"[{req_key}] code={code} msg={msg} 有图片={has_img}")
        if has_img:
            print("   图片URL示例:", resp["data"]["image_urls"][0][:100])
            break
    except Exception as exc:
        print(f"[{req_key}] 异常: {type(exc).__name__}: {str(exc)[:150]}")
PYEOF

echo "=== 清理容器内 key ==="
docker compose exec -T backend rm -f /tmp/ApiKey.txt
