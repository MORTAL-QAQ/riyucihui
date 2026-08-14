#!/bin/bash
# PostgreSQL 定期备份 — 供服务器 crontab 调用
#
# 用法: bash scripts/backup_db.sh
# 建议 crontab: 0 3 * * * cd /opt/riyucihui && bash scripts/backup_db.sh >> backups/backup.log 2>&1
#
# 行为：
#   - docker compose exec postgres pg_dump → gzip 压缩到 backups/
#   - 文件名带时间戳，保留最近 14 份，更早的自动删除
#   - DB 密码从 secrets/DB_PASSWORD 读取（若存在），不回显

set -e
cd "$(dirname "$0")/.."  # 项目根目录

BACKUP_DIR="${BACKUP_DIR:-backups}"
KEEP="${KEEP:-14}"
mkdir -p "$BACKUP_DIR"

# 容器未运行则直接报错（避免生成空备份）
if ! docker compose ps postgres 2>/dev/null | grep -q Up; then
    echo "[$(date '+%F %T')] ERROR: postgres 容器未运行，跳过备份" >&2
    exit 1
fi

STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$BACKUP_DIR/riyucihui_${STAMP}.sql.gz"

# 密码（postgres 容器内 local 连接通常 trust，此处兜底从 secrets 读取）
if [ -f secrets/DB_PASSWORD ]; then
    export PGPASSWORD
    PGPASSWORD=$(cat secrets/DB_PASSWORD)
fi

docker compose exec -T postgres pg_dump -U jpvocab -d jpvocab | gzip > "$OUT"
SIZE=$(du -h "$OUT" | cut -f1)
echo "[$(date '+%F %T')] 备份完成: $OUT ($SIZE)"

# 保留最近 $KEEP 份，删除更早的
ls -1t "$BACKUP_DIR"/riyucihui_*.sql.gz 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
    rm -f "$old"
    echo "[$(date '+%F %T')] 已清理旧备份: $old"
done
