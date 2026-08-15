#!/bin/bash
cd /opt/riyucihui
echo "=== 1. users 表 name 列 + 回填检查 ==="
docker compose exec -T postgres psql -U jpvocab -d jpvocab -c "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='name';" 2>&1 | tail -3
docker compose exec -T postgres psql -U jpvocab -d jpvocab -c "SELECT count(*) AS total, count(name) AS has_name, count(*) FILTER (WHERE name = username) AS name_eq_username FROM users;" 2>&1 | tail -3
echo "=== 2. 注册带昵称 ==="
U="prod_$(date +%s)"
curl -sk -X POST "https://127.0.0.1/api/register" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$U\",\"password\":\"Prod123456\",\"name\":\"测试昵称\"}" | head -c 200
echo ""
echo "=== 3. 清理测试账号 ==="
docker compose exec -T postgres psql -U jpvocab -d jpvocab -c "DELETE FROM users WHERE username LIKE 'prod_%';" 2>&1 | tail -1
