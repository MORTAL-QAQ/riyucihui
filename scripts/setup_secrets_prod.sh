#!/bin/bash
# 生产服务器 Docker secrets 初始化脚本 v2（一次性，执行后删除）
# 从现有 .env 提取真实密钥 → 验证 DB 密码可连接 → 创建 secrets/ → 清除明文 → 轮换 SECRET_KEY
set -e
cd /opt/riyucihui

# 1. 备份 .env
cp .env ".env.bak.$(date +%s)"

# 2. 确定 DB_PASSWORD：优先 DB_PASSWORD= 键，否则从 DATABASE_URL 提取
DB_PASSWORD=""
if grep -q "^DB_PASSWORD=" .env; then
  DB_PASSWORD=$(grep "^DB_PASSWORD=" .env | cut -d= -f2-)
else
  URL=$(grep "^DATABASE_URL=" .env | cut -d= -f2-)
  DB_PASSWORD=$(echo "$URL" | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|')
fi
[ -n "$DB_PASSWORD" ] || { echo "FATAL: cannot determine DB_PASSWORD"; exit 1; }

# 3. 验证密码能连接 postgres（不回显密码）
if ! docker compose exec -T postgres env PGPASSWORD="$DB_PASSWORD" psql -U jpvocab -d jpvocab -tAc "select 1" >/dev/null 2>&1; then
  echo "FATAL: DB password verification FAILED (postgres may be down or password wrong)"
  exit 1
fi
echo "DB_PASSWORD verified OK (len=${#DB_PASSWORD})"

# 4. 提取 API 密钥
DEEPSEEK_API_KEY=$(grep "^DEEPSEEK_API_KEY=" .env | cut -d= -f2-)
VOLCANO_API_KEY=$(grep "^VOLCANO_API_KEY=" .env | cut -d= -f2-)
[ -n "$DEEPSEEK_API_KEY" ] || { echo "FATAL: DEEPSEEK_API_KEY missing in .env"; exit 1; }
[ -n "$VOLCANO_API_KEY" ] || { echo "FATAL: VOLCANO_API_KEY missing in .env"; exit 1; }

# 5. 轮换 SECRET_KEY（服务器端生成新随机值）
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 6. 创建 secrets/（保持现有 DB 密码不变，避免 pgdata 卷失配）
mkdir -p secrets
printf '%s' "$SECRET_KEY" > secrets/SECRET_KEY
printf '%s' "$DEEPSEEK_API_KEY" > secrets/DEEPSEEK_API_KEY
printf '%s' "$VOLCANO_API_KEY" > secrets/VOLCANO_API_KEY
printf '%s' "$DB_PASSWORD" > secrets/DB_PASSWORD
printf 'postgresql://jpvocab:%s@postgres:5432/jpvocab' "$DB_PASSWORD" > secrets/DATABASE_URL
# 权限：目录 700（仅 root 可进）、文件 644——非 root 容器用户（appuser）需可读
# （容器内 secrets 为只读挂载无法 chmod，权限必须由宿主机源文件控制，配合 #8）
chmod 700 secrets
chmod 644 secrets/*

# 7. 清除 .env 中的明文密钥行
sed -i -E '/^(SECRET_KEY|DEEPSEEK_API_KEY|VOLCANO_API_KEY|DB_PASSWORD|DATABASE_URL)=/d' .env

# 8. CORS 收敛为具体域名
sed -i 's|^CORS_ORIGINS=.*|CORS_ORIGINS=https://riyucihuixuexi.cn,https://www.riyucihuixuexi.cn|' .env

echo "== secrets created =="
ls -la secrets/
echo "== .env keys after =="
grep -oE '^[A-Z_]+' .env
echo "== SECRET_KEY sha256 (新值指纹) =="
sha256sum secrets/SECRET_KEY
