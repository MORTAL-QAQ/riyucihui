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

# 后端代码（用 backend/* 避免在服务器上嵌套成 backend/backend/）
echo "  → backend/"
ssh "${SERVER_USER}@${SERVER_IP}" "rm -rf ${SERVER_PROJECT_DIR}/backend.bak"
ssh "${SERVER_USER}@${SERVER_IP}" "cp -a ${SERVER_PROJECT_DIR}/backend ${SERVER_PROJECT_DIR}/backend.bak"
scp -r backend/* "${SERVER_USER}@${SERVER_IP}:${SERVER_PROJECT_DIR}/backend/"

# 前端静态文件（用 frontend/* 避免在服务器上嵌套成 frontend/frontend/）
echo "  → frontend/"
scp -r frontend/css frontend/js frontend/index.html "${SERVER_USER}@${SERVER_IP}:${SERVER_PROJECT_DIR}/frontend/"

# 配置文件
echo "  → 配置文件"
scp docker-compose.yml Dockerfile nginx.conf "${SERVER_USER}@${SERVER_IP}:${SERVER_PROJECT_DIR}/"

# secrets/ 密钥目录（SECRET_KEY / API Key / DB 密码等）
# 注意：会覆盖服务器上的同名文件，部署前请确认本地 secrets/ 中为真实值
if [ -d secrets ]; then
  echo "  → secrets/ 密钥目录"
  scp -r secrets "${SERVER_USER}@${SERVER_IP}:${SERVER_PROJECT_DIR}/"
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
