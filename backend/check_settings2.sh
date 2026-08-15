#!/bin/bash
echo "=== /settings 响应头 ==="
curl -skI https://127.0.0.1/settings | grep -iE 'cache-control|content-type|etag|last-modified'
echo ""
echo "=== 生产 settings.html 内容核验 ==="
H=$(curl -skL https://127.0.0.1/settings)
echo "账号设置模块: $(echo "$H" | grep -c '账号设置')"
echo "发声设置模块: $(echo "$H" | grep -c '发声设置')"
echo "账号信息子块: $(echo "$H" | grep -c '账号信息')"
echo "修改密码子块: $(echo "$H" | grep -c '修改密码')"
echo "发音参数子块: $(echo "$H" | grep -c '发音参数')"
echo "旧三卡样式 margin-top:16px: $(echo "$H" | grep -c 'margin-top:16px')"
echo "settings-box-title 数量: $(echo "$H" | grep -o 'settings-box-title' | wc -l)"
echo ""
echo "=== 服务器上文件时间戳 ==="
ls -la /opt/riyucihui/frontend/settings.html
echo ""
echo "=== 文件 md5（与本地对比用）==="
md5sum /opt/riyucihui/frontend/settings.html
