#!/bin/bash
cd /opt/riyucihui
echo "== index.html 是否含社区页 =="
grep -c "page-community\|nav-community" frontend/index.html
echo "== index.html 版本号 =="
grep -oE '(css|js)/[a-z.]+\.(css|js)\?v=[0-9a-f]{8}' frontend/index.html
echo "== 残留占位符 =="
grep -c '{desktop_version}\|{api_version}\|{app_version}\|{mobile_version}' frontend/index.html || echo "0 残留"
echo "== app.js 是否含社区逻辑 =="
grep -c "loadCommunity\|page-community" frontend/js/app.js
echo "== 文件时间戳 =="
ls -la frontend/index.html frontend/js/app.js frontend/js/api.js
echo "== nginx 挂载 =="
docker inspect jp-vocab-nginx --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}' | grep frontend
echo "== 线上 index.html 响应（含版本号）=="
curl -sk -m 10 https://127.0.0.1/ | grep -oE 'app\.js\?v=[0-9a-f]{8}'
