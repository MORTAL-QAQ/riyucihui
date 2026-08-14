#!/bin/bash
echo "=== 生产 app.js 版本与内容检查 ==="
V=$(curl -skL https://127.0.0.1/ | grep -o 'app.js?v=[0-9a-f]*' | cut -d= -f2)
echo "app.js?v=$V"
echo "audioCtx 声明残留(应为0): $(curl -skL "https://127.0.0.1/js/app.js?v=$V" | grep -c '^let audioCtx')"
echo "common.js audioCtx(应为1): $(curl -skL "https://127.0.0.1/js/common.js?v=$V" | grep -c 'let audioCtx = null')"
echo "index: $(curl -skL -o /dev/null -w '%{http_code}' https://127.0.0.1/)"
