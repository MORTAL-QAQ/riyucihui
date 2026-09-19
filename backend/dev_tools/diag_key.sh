#!/bin/bash
set -u
cd /opt/riyucihui
docker compose cp /tmp/keytest/ApiKey.txt backend:/tmp/ApiKey.txt

docker compose exec -T -e PYTHONPATH=/app -w /app backend python - << 'PYEOF'
import json, urllib.request

txt = open("/tmp/ApiKey.txt", encoding="utf-8").read()
kid = sec = ""
for line in txt.splitlines():
    if "API Key ID" in line:
        kid = line.split(":", 1)[1].strip()
    elif "API Key Secret" in line:
        sec = line.split(":", 1)[1].strip()

BASE = "https://ark.cn-beijing.volces.com/api/v3"

def call(path, token, body, extra_headers=None, label=""):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (extra_headers or {}).items():
        req.add_header(k, v)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.read().decode()[:150]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as e:
        return "ERR", str(e)[:120]

# 文本模型（判断 key 是否有任何模型权限）
TEXT_BODY = {"model": "doubao-seed-1-6-250615", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}
IMG_BODY = {"model": "doubao-seedream-5-0-260128", "prompt": "a red apple",
            "sequential_image_generation": "disabled", "response_format": "url",
            "size": "2K", "stream": False, "watermark": True}

print("=== 用 Secret 调文本模型（有权限吗）===")
print("Bearer:", call("/chat/completions", sec, TEXT_BODY))
print("X-Api-Key:", call("/chat/completions", None, TEXT_BODY, {"X-Api-Key": sec}))
print("Bearer ID:Secret:", call("/chat/completions", f"{kid}:{sec}", TEXT_BODY))
print()
print("=== 用 Secret 调图片模型 ===")
print("Bearer:", call("/images/generations", sec, IMG_BODY))
print("X-Api-Key:", call("/images/generations", None, IMG_BODY, {"X-Api-Key": sec}))
print()
print("=== 对照：现有生产 key 调文本模型 ===")
old = open("/run/secrets/VOLCANO_API_KEY").read().strip()
print("Bearer(old):", call("/chat/completions", old, TEXT_BODY))
PYEOF

docker compose exec -T backend rm -f /tmp/ApiKey.txt
