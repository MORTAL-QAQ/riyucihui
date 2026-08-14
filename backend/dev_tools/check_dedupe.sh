#!/bin/bash
echo "=== 生产 index.html 脚本引用 ==="
curl -skL https://127.0.0.1/ | grep -o 'js/[a-z]*\.js?v=[0-9a-f]*'
echo "=== 独立页 common.js 引用 ==="
curl -skL https://127.0.0.1/generate | grep -o 'common.js?v=[0-9a-f]*'
echo "=== 首页统计接口 ==="
curl -skL -o /dev/null -w 'index:%{http_code}\n' https://127.0.0.1/
