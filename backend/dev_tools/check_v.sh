#!/bin/bash
cd /opt/riyucihui
echo "common.js version: $(grep -o 'common.js?v=[0-9a-f]*' frontend/generate.html)"
echo "generate.js version: $(grep -o 'generate.js?v=[0-9a-f]*' frontend/generate.html)"
echo "stream-preview count: $(grep -c 'id="stream-preview"' frontend/generate.html)"
echo "--- 带新版本号拉取 JS 并验证内容含修复 ---"
V=$(grep -o 'common.js?v=[0-9a-f]*' frontend/generate.html | cut -d= -f2)
curl -sk "https://127.0.0.1/js/common.js?v=$V" | grep -c 'getElementById(previewId)'
