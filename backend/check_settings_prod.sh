#!/bin/bash
echo "=== 生产 settings.html 检查 ==="
curl -skL https://127.0.0.1/settings | grep -c 'settings-box-title'
curl -skL https://127.0.0.1/settings | grep -c 'setting-pw-toggle'
curl -skL https://127.0.0.1/settings | grep -c 'margin-top:16px'
echo "=== 版本号 ==="
curl -skL https://127.0.0.1/settings | grep -o 'settings.js?v=[0-9a-f]*'
curl -skL https://127.0.0.1/settings | grep -o 'desktop.css?v=[0-9a-f]*'
echo "=== 生产 settings.js 是否含 toggle ==="
V=$(curl -skL https://127.0.0.1/settings | grep -o 'settings.js?v=[0-9a-f]*' | cut -d= -f2)
curl -skL "https://127.0.0.1/js/settings.js?v=$V" | grep -c 'setting-pw-toggle'
echo "=== 生产 desktop.css 是否含 box-title ==="
CV=$(curl -skL https://127.0.0.1/settings | grep -o 'desktop.css?v=[0-9a-f]*' | cut -d= -f2)
curl -skL "https://127.0.0.1/css/desktop.css?v=$CV" | grep -c 'settings-box-title'
