#!/usr/bin/env bash
# 切换生产「AI 配图」所用的火山引擎密钥，并当场实测出图。
#
# 用法：
#   bash backend/dev_tools/switch_image_key.sh                  # 用仓库根目录 ApiKey.txt
#   bash backend/dev_tools/switch_image_key.sh <key>            # 直接给 key
#   bash backend/dev_tools/switch_image_key.sh --file <path>    # 指定密钥文件
#   bash backend/dev_tools/switch_image_key.sh --restore        # 回滚到备份的上一个密钥
#
# 支持两种文件格式：
#   1. 单行：直接是 API Key
#   2. 两行：API Key ID: ... / API Key Secret: ...（控制台导出格式，取 Secret 行）
#
# 注意：本机必须用 Git Bash 执行（不要用 WSL 的 bash）。
#   & "D:\Git\Git\bin\bash.exe" backend/dev_tools/switch_image_key.sh

set -euo pipefail

SERVER="root@101.37.204.74"
DIR="/opt/riyucihui"
SECRET_FILE="${DIR}/secrets/VOLCANO_API_KEY"
BACKUP_FILE="${DIR}/secrets/VOLCANO_API_KEY.bak"

# ── 解析参数 ──
case "${1:-}" in
  --restore)
    echo "→ 回滚密钥"
    ssh "$SERVER" "if [ -f $BACKUP_FILE ]; then cp -f $BACKUP_FILE $SECRET_FILE && echo '  已恢复备份密钥'; else echo '  无备份可恢复'; exit 1; fi"
    ssh "$SERVER" "cd $DIR && docker compose up -d --force-recreate backend" >/dev/null
    echo "  backend 已重建"
    exit 0
    ;;
  --file)
    KEY=$(python - "$2" <<'PY'
import sys
for line in open(sys.argv[1], encoding='utf-8'):
    if ':' in line and 'secret' in line.lower():
        print(line.split(':', 1)[1].strip()); break
else:
    for line in open(sys.argv[1], encoding='utf-8'):
        line = line.strip()
        if line and ':' not in line:
            print(line); break
PY
)
    ;;
  "")
    KEY=$(python - "$(dirname "$0")/../../ApiKey.txt" <<'PY'
import sys
for line in open(sys.argv[1], encoding='utf-8'):
    if ':' in line and 'secret' in line.lower():
        print(line.split(':', 1)[1].strip()); break
else:
    for line in open(sys.argv[1], encoding='utf-8'):
        line = line.strip()
        if line and ':' not in line:
            print(line); break
PY
)
    ;;
  *)
    KEY="$1"
    ;;
esac

if [ -z "${KEY:-}" ]; then
  echo "❌ 未能解析出密钥" >&2
  exit 1
fi

echo "→ 待切换密钥：${KEY:0:8}…${KEY: -4}（长度 ${#KEY}）"

# ── 先本地验证权限，没权限就不动生产 ──
LOCAL_SCRIPT="$(dirname "$0")/check_ark_key.py"
if [ -f "$LOCAL_SCRIPT" ]; then
  echo "→ 本地预检该密钥的模型权限…"
  if ! python "$LOCAL_SCRIPT" "$KEY"; then
    echo "❌ 预检未通过（该密钥无 Seedream 权限或模型未开通），已中止，生产密钥未改动。" >&2
    exit 1
  fi
fi

# ── 备份旧密钥 → 写入新密钥（secrets 文件需非 root 容器可读，644）──
echo "→ 备份并写入服务器密钥"
ssh "$SERVER" "cp -f $SECRET_FILE $BACKUP_FILE 2>/dev/null || true"
printf '%s' "$KEY" | ssh "$SERVER" "cat > $SECRET_FILE && chmod 644 $SECRET_FILE && wc -c < $SECRET_FILE"

echo "→ 重建 backend 使新密钥生效"
ssh "$SERVER" "cd $DIR && docker compose up -d --force-recreate backend" >/dev/null 2>&1
sleep 6

echo "→ 容器内实测出图（真实调用一次）"
ssh "$SERVER" "cd $DIR && docker compose exec -T -e PYTHONPATH=/app -w /app backend python - <<'PY'
from app.services import image_service
res = image_service.generate_word_image('林檎', '苹果', 'りんご', '林檎を食べます。', '吃苹果。')
print('OK 图片长度:', len(res))
PY"

echo "✅ 切换完成。如需回滚：bash backend/dev_tools/switch_image_key.sh --restore"
