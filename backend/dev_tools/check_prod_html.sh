#!/bin/bash
cd /opt/riyucihui
echo "=== 生产 generate.html stream-preview ==="
grep -c 'id="stream-preview"' frontend/generate.html
echo "=== 生产 generate.html 版本号 ==="
grep -o 'generate.js?v=[0-9a-f]*' frontend/generate.html
grep -o 'common.js?v=[0-9a-f]*' frontend/generate.html
echo "=== 生产 essay/cloze/grammar preview 元素 ==="
grep -c 'id="essay-stream-preview"' frontend/essay.html
grep -c 'id="cloze-stream-preview"' frontend/cloze.html
grep -c 'grammar-.*-stream-preview' frontend/grammar.html
echo "=== nginx Cache-Control 配置 ==="
grep -n 'Cache-Control' nginx.conf | head -10
echo "=== 实际响应头 ==="
curl -skI "https://127.0.0.1/generate" | grep -i 'cache-control\|content-type\|etag'
