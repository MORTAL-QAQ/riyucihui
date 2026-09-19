#!/bin/bash
cd /opt/riyucihui
echo "=== 生产 secrets 中的火山配置 ==="
for f in VOLCANO_API_KEY VOLCANO_IMAGE_BASE_URL VOLCANO_IMAGE_MODEL VOLCANO_API_KEY_ID VOLCANO_API_KEY_SECRET; do
  if [ -f "secrets/$f" ]; then
    v=$(cat "secrets/$f")
    echo "$f = ${v:0:20}...(len=${#v})"
  fi
done
echo ""
echo "=== 容器内环境变量（VOLCANO 相关）==="
docker compose exec -T backend sh -c 'env | grep -i volcano' 2>/dev/null || echo "（无 env 注入，走 secrets 文件）"
echo ""
echo "=== 容器内 /run/secrets 文件 ==="
docker compose exec -T backend sh -c 'ls /run/secrets/ 2>/dev/null'
