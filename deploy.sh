#!/bin/bash
# ============================================================
# 一键部署脚本 — 本地修改 → 服务器更新
#
# 用法: bash deploy.sh
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

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  一键部署：日语词汇学习平台${NC}"
echo -e "${YELLOW}========================================${NC}"

# ── 1. 同步文件到服务器 ──
echo -e "${GREEN}[1/4] 同步代码到服务器...${NC}"

# 后端代码（tar 流传输，排除本地临时/缓存目录；用 backend/* 避免嵌套 backend/backend/）
echo "  → backend/"
ssh "${SERVER_USER}@${SERVER_IP}" "rm -rf ${SERVER_PROJECT_DIR}/backend.bak"
ssh "${SERVER_USER}@${SERVER_IP}" "cp -a ${SERVER_PROJECT_DIR}/backend ${SERVER_PROJECT_DIR}/backend.bak"
tar --exclude='.tmp' --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
    -C backend -cf - . | ssh "${SERVER_USER}@${SERVER_IP}" "tar -C ${SERVER_PROJECT_DIR}/backend -xf -"

# 前端静态文件（用 frontend/* 避免在服务器上嵌套成 frontend/frontend/）
echo "  → frontend/"
scp -r frontend/css frontend/js frontend/index.html "${SERVER_USER}@${SERVER_IP}:${SERVER_PROJECT_DIR}/frontend/"

# 配置文件
echo "  → 配置文件"
scp docker-compose.yml Dockerfile nginx.conf .dockerignore "${SERVER_USER}@${SERVER_IP}:${SERVER_PROJECT_DIR}/"

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

# ── 4. 等待并检查 ──
echo -e "${GREEN}[4/4] 等待服务健康检查...${NC}"
sleep 5
ssh "${SERVER_USER}@${SERVER_IP}" "cd ${SERVER_PROJECT_DIR} && docker compose ps"

echo ""
echo -e "${GREEN}✅ 部署完成！${NC}"
echo -e "访问地址: https://${SERVER_IP}"
