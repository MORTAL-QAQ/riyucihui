#!/bin/bash
# ============================================================
# 一键部署脚本 — 本地修改 → 服务器更新
#
# 用法:
#   bash deploy.sh             正常部署（同步 + 构建 + 重启 + 备份 cron）
#   bash deploy.sh rollback    回滚 backend 到上次部署版本（backend.bak）
#
# 前置条件:
#   1. 本地已配置 SSH Key 并添加到服务器
#      ssh-copy-id root@你的服务器IP
#   2. 服务器上项目路径为 /opt/riyucihui
# ============================================================
set -e

# ── 配置（修改为你的服务器信息） ──
SERVER_USER="root"
SERVER_IP="101.37.204.74"          # ← 改成实际 IP
SERVER_PROJECT_DIR="/opt/riyucihui"

# ── 颜色输出 ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── rollback 子命令（#22）：从 backend.bak 恢复上次部署版本 ──
if [ "${1:-}" = "rollback" ]; then
  echo -e "${YELLOW}回滚 backend 到上次部署版本...${NC}"
  ssh "${SERVER_USER}@${SERVER_IP}" "cd ${SERVER_PROJECT_DIR} && \
    [ -d backend.bak ] || { echo '无 backend.bak 备份，无法回滚'; exit 1; } && \
    rm -rf backend && cp -a backend.bak backend && \
    docker compose build backend && \
    docker compose up -d --force-recreate backend && \
    docker compose restart nginx"
  echo -e "${GREEN}✅ 回滚完成！${NC}"
  exit 0
fi

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  一键部署：日语词汇学习平台${NC}"
echo -e "${YELLOW}========================================${NC}"

# ── 1. 同步文件到服务器 ──
echo -e "${GREEN}[1/4] 同步代码到服务器...${NC}"

# 后端代码（tar 流传输，排除本地临时/缓存目录；--delete 语义：先清空再解压，
# 保证服务器上无本地已删除文件的残留；失败可从 backend.bak 恢复）
echo "  → backend/"
ssh "${SERVER_USER}@${SERVER_IP}" "rm -rf ${SERVER_PROJECT_DIR}/backend.bak && cp -a ${SERVER_PROJECT_DIR}/backend ${SERVER_PROJECT_DIR}/backend.bak"
tar --exclude='.tmp' --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
    -C backend -cf - . | ssh "${SERVER_USER}@${SERVER_IP}" "rm -rf ${SERVER_PROJECT_DIR}/backend/* && tar -C ${SERVER_PROJECT_DIR}/backend -xf -"

# 前端静态文件（用 frontend/* 避免在服务器上嵌套成 frontend/frontend/；含独立子页 html）
echo "  → frontend/"
scp -r frontend/css frontend/js frontend/*.html "${SERVER_USER}@${SERVER_IP}:${SERVER_PROJECT_DIR}/frontend/"

# 配置文件
echo "  → 配置文件"
scp docker-compose.yml Dockerfile nginx.conf .dockerignore entrypoint.sh "${SERVER_USER}@${SERVER_IP}:${SERVER_PROJECT_DIR}/"

# 运维脚本（备份 / 证书 / secrets 初始化）
echo "  → scripts/ 运维脚本"
ssh "${SERVER_USER}@${SERVER_IP}" "mkdir -p ${SERVER_PROJECT_DIR}/scripts"
scp -r scripts/*.sh "${SERVER_USER}@${SERVER_IP}:${SERVER_PROJECT_DIR}/scripts/"

# ── secrets/ 密钥目录（不自动覆盖，避免本地占位符覆盖服务器真实密钥）──
# Docker secrets 源文件（SECRET_KEY / API Key / DB 密码）。服务器上已存在时跳过；
# 首次部署或需要轮换密钥时，请在服务器上手动维护：
#   服务器: /opt/riyucihui/secrets/ 下放置 SECRET_KEY、DEEPSEEK_API_KEY、
#           VOLCANO_API_KEY、DB_PASSWORD、DATABASE_URL（详见 secrets/README.md）
if [ -d secrets ]; then
  echo "  → secrets/：检测到本地 secrets 目录"
  if ssh "${SERVER_USER}@${SERVER_IP}" "[ -d ${SERVER_PROJECT_DIR}/secrets ]"; then
    echo "    ⚠️  服务器 secrets/ 已存在，跳过覆盖（避免覆盖真实密钥）"
    echo "    如需轮换 SECRET_KEY，请在服务器上更新 secrets/SECRET_KEY 后重建 backend"
  else
    echo "    ⚠️  服务器无 secrets/，未自动创建——请先确认本地 secrets/ 中为真实值，"
    echo "    再手动执行: scp -r secrets ${SERVER_USER}@${SERVER_IP}:${SERVER_PROJECT_DIR}/"
  fi
fi

# ── 2. 重建后端镜像 ──
echo -e "${GREEN}[2/4] 重建后端镜像...${NC}"
ssh "${SERVER_USER}@${SERVER_IP}" "cd ${SERVER_PROJECT_DIR} && docker compose build backend"

# ── 3. 重启服务 ──
echo -e "${GREEN}[3/4] 重启服务...${NC}"
ssh "${SERVER_USER}@${SERVER_IP}" "cd ${SERVER_PROJECT_DIR} && docker compose up -d --force-recreate backend"

# 如果 nginx.conf 或 frontend 有变化，重启 nginx
ssh "${SERVER_USER}@${SERVER_IP}" "cd ${SERVER_PROJECT_DIR} && docker compose restart nginx"

# ── 3.5 前端资源版本号注入（#37） ──
# nginx 静态托管不经过 FastAPI 的 index()，需在部署时用内容哈希替换 index.html 占位符，
# 使 css/js 修改后浏览器能拿到新 URL（避免 1 天强缓存内的旧版本）
# 阶段二：对全部 HTML（index + 独立子页）统一注入版本号
echo -e "${GREEN}[3.5] 注入前端资源版本号...${NC}"
ssh "${SERVER_USER}@${SERVER_IP}" "cd ${SERVER_PROJECT_DIR}/frontend && \
  H_DESKTOP=\$(md5sum css/desktop.css | cut -c1-8); \
  H_MOBILE=\$(md5sum css/mobile.css | cut -c1-8); \
  H_API=\$(md5sum js/api.js | cut -c1-8); \
  H_APP=\$(md5sum js/app.js | cut -c1-8); \
  for html in index.html community.html wordbank.html study.html; do \
    [ -f \"\$html\" ] || continue; \
    sed -i \"s|{desktop_version}|\$H_DESKTOP|g; s|{mobile_version}|\$H_MOBILE|g; s|{api_version}|\$H_API|g; s|{app_version}|\$H_APP|g\" \"\$html\"; \
  done && echo '  版本号注入完成' && grep -l 'v={[a-z_]*}' *.html 2>/dev/null || echo '  (无未替换占位符)'"

# ── 4. 等待并检查 ──
echo -e "${GREEN}[4/4] 等待服务健康检查...${NC}"
sleep 5
ssh "${SERVER_USER}@${SERVER_IP}" "cd ${SERVER_PROJECT_DIR} && docker compose ps"

# ── 5. 注册数据库备份 cron（幂等：先移除旧条目再追加） ──
echo -e "${GREEN}[5/5] 配置每日数据库备份（cron 03:00）...${NC}"
ssh "${SERVER_USER}@${SERVER_IP}" "cd ${SERVER_PROJECT_DIR} && mkdir -p backups && (crontab -l 2>/dev/null | grep -v 'scripts/backup_db.sh' ; echo '0 3 * * * cd ${SERVER_PROJECT_DIR} && bash scripts/backup_db.sh >> backups/backup.log 2>&1') | crontab - && echo '  crontab 已注册:' && crontab -l | grep backup_db"

echo ""
echo -e "${GREEN}✅ 部署完成！${NC}"
echo -e "访问地址: https://${SERVER_IP}"
