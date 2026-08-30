#!/bin/bash
cd /opt/riyucihui
echo "=== DB 中最近登录记录（login_at 原始存储） ==="
docker compose exec -T postgres psql -U jpvocab -d jpvocab -c "SELECT id, user_id, login_at, ip_address FROM login_history ORDER BY login_at DESC LIMIT 8;"
echo ""
echo "=== 服务器当前 UTC / 本地时间 ==="
date -u
date
