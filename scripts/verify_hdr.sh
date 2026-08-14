#!/bin/bash
cd /opt/riyucihui
echo "== nginx 配置 =="
docker exec jp-vocab-nginx nginx -t 2>&1 | tail -1
echo "== community.html 响应头 =="
curl -sk -m 10 -o /dev/null -D /tmp/h.txt https://127.0.0.1/community
cat /tmp/h.txt
rm -f /tmp/h.txt
