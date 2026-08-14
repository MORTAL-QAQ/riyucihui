#!/bin/bash
# P1 生产部署验证（临时脚本）
cd /opt/riyucihui
echo "== backend 启动日志（应连 PostgreSQL 且无 SQLite 警告）=="
docker compose logs backend 2>&1 | grep -E "SQLite|postgres|startup complete|Uvicorn running" | tail -5
echo "== 数据库备份试跑（#17）=="
bash scripts/backup_db.sh
echo "== 备份文件 =="
ls -lh backups/ | tail -3
echo "== 索引检查（#27，run_migrations 已执行）=="
PGPASSWORD=$(cat secrets/DB_PASSWORD) docker compose exec -T postgres psql -U jpvocab -d jpvocab -tAc "SELECT indexname FROM pg_indexes WHERE tablename='study_records' ORDER BY indexname"
echo "== nginx 配置校验（#20 SSE buffering off）=="
docker exec jp-vocab-nginx nginx -t 2>&1 | tail -1
docker exec jp-vocab-nginx grep -A2 "proxy_buffering" /etc/nginx/conf.d/default.conf | head -3
echo "== 线上验证 =="
curl -sk -m 10 -o /dev/null -w "health=%{http_code}\n" https://127.0.0.1/api/health
curl -sk -m 10 -o /dev/null -w "login_probe(401 expected)=%{http_code}\n" -X POST https://127.0.0.1/api/login -H "Content-Type: application/json" -d '{"username":"nonexistent_probe","password":"wrongpass123"}'
curl -sk -m 10 -o /dev/null -w "me_unauth(401 expected)=%{http_code}\n" https://127.0.0.1/api/me
