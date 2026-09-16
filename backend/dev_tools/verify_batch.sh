#!/bin/bash
echo "=== 抽查学生账号登录 ==="
for sid in 202521123001 202521123034 202521123066; do
  resp=$(curl -sk -X POST "https://127.0.0.1/api/login" -H 'Content-Type: application/json' \
    -d "{\"username\":\"$sid\",\"password\":\"123456\"}")
  echo "$sid → $(echo "$resp" | head -c 120)"
done
echo ""
echo "=== 用户总数与最近创建 ==="
cd /opt/riyucihui
docker compose exec -T postgres psql -U jpvocab -d jpvocab -c "SELECT count(*) AS 总数 FROM users;"
docker compose exec -T postgres psql -U jpvocab -d jpvocab -c "SELECT username, name FROM users WHERE username LIKE '2025%' ORDER BY username LIMIT 5;"
