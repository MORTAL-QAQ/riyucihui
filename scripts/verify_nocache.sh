#!/bin/bash
cd /opt/riyucihui
echo "== nginx 配置校验 =="
docker exec jp-vocab-nginx nginx -t 2>&1 | tail -1
echo "== community.html 响应头（应含 no-cache）=="
curl -sk -m 10 -o /dev/null -D - https://127.0.0.1/community | grep -iE "cache-control|http/|last-modified"
echo "== community.html 顶栏内联样式 =="
curl -sk -m 10 https://127.0.0.1/community | grep -oE 'background:linear-gradient\(135deg,#1a1a2e|id="btn-logout"|href="/settings"' | sort -u
echo "== 版本号 =="
grep -oE 'community\.js\?v=[0-9a-f]{8}' frontend/community.html
