#!/bin/bash
echo "=== 生产首页检查 ==="
curl -skL https://127.0.0.1/ | grep -c 'home-quick'
curl -skL https://127.0.0.1/ | grep -c 'home-welcome-cta'
curl -skL https://127.0.0.1/ | grep -c 'home-stat-icon'
echo "=== css 版本 ==="
curl -skL https://127.0.0.1/ | grep -o 'desktop.css?v=[0-9a-f]*'
