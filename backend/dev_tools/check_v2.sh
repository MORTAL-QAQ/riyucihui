#!/bin/bash
cd /opt/riyucihui
echo "api.js version: $(grep -o 'api.js?v=[0-9a-f]*' frontend/generate.html)"
echo "common.js version: $(grep -o 'common.js?v=[0-9a-f]*' frontend/generate.html)"
echo "--- 新 api.js 含 blob 返回 ---"
V=$(grep -o 'api.js?v=[0-9a-f]*' frontend/generate.html | cut -d= -f2)
curl -sk "https://127.0.0.1/js/api.js?v=$V" | grep -c 'return res.blob()'
echo "--- 新 common.js 无 fetch(blob) ---"
V2=$(grep -o 'common.js?v=[0-9a-f]*' frontend/generate.html | cut -d= -f2)
curl -sk "https://127.0.0.1/js/common.js?v=$V2" | grep -c 'blob.arrayBuffer'
