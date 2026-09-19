#!/usr/bin/env bash
# 切换生产「AI 配图」通道（ark=方舟 Seedream / visual=视觉智能平台通用3.0-文生图），
# 并在容器内实测出图；实测失败自动回滚到原通道，避免线上配图失效。
#
# 用法（本机需用 Git Bash）：
#   bash backend/dev_tools/set_image_provider.sh visual
#   bash backend/dev_tools/set_image_provider.sh ark
#   bash backend/dev_tools/set_image_provider.sh visual --ak AKLT... --sk WW1G...
#   bash backend/dev_tools/set_image_provider.sh --show        # 只看当前通道与凭证状态（不打印密钥）
#
# 注意：凭证只写入服务器 secrets/（644，供非 root 容器读取），绝不落到仓库。

set -euo pipefail

SERVER="root@101.37.204.74"
DIR="/opt/riyucihui"
ENV_FILE="${DIR}/.env"
SEC_DIR="${DIR}/secrets"

PROVIDER=""
AK=""
SK=""

while [ $# -gt 0 ]; do
  case "$1" in
    --ak) AK="$2"; shift 2 ;;
    --sk) SK="$2"; shift 2 ;;
    --show) PROVIDER="--show"; shift ;;
    ark|visual) PROVIDER="$1"; shift ;;
    *) echo "未知参数: $1" >&2; exit 1 ;;
  esac
done

mask() { [ -n "$1" ] && echo "${1:0:8}…${1: -4}（长度 ${#1}）" || echo "（未设置）"; }

if [ "$PROVIDER" = "--show" ]; then
  echo "→ 服务器当前配图相关状态"
  ssh "$SERVER" "
    echo -n '  .env IMAGE_PROVIDER : '; grep -E '^IMAGE_PROVIDER=' $ENV_FILE 2>/dev/null || echo '（未设置 → 默认 ark）'
    echo -n '  容器内生效值        : '
    cd $DIR && docker compose exec -T -e PYTHONPATH=/app -w /app backend python -c \"from app import config; print(config.IMAGE_PROVIDER)\" 2>/dev/null || echo '（容器未运行）'
    echo -n '  VOLCANO_ACCESS_KEY  : '; [ -s $SEC_DIR/VOLCANO_ACCESS_KEY ] && cut -c1-8 $SEC_DIR/VOLCANO_ACCESS_KEY || echo '（缺失）'
    echo -n '  VOLCANO_SECRET_KEY  : '; [ -s $SEC_DIR/VOLCANO_SECRET_KEY ] && echo \"已存在（\$(wc -c < $SEC_DIR/VOLCANO_SECRET_KEY) 字节）\" || echo '（缺失）'
    echo -n '  VOLCANO_API_KEY     : '; [ -s $SEC_DIR/VOLCANO_API_KEY ] && cut -c1-8 $SEC_DIR/VOLCANO_API_KEY || echo '（缺失）'
  "
  exit 0
fi

[ -n "$PROVIDER" ] || { echo "用法: $0 <ark|visual> [--ak AK --sk SK]  |  $0 --show" >&2; exit 1; }

# ── 1. 写入 AK/SK（如提供）──
if [ -n "$AK" ] || [ -n "$SK" ]; then
  [ -n "$AK" ] && [ -n "$SK" ] || { echo "❌ --ak 与 --sk 必须同时提供" >&2; exit 1; }
  echo "→ 写入视觉平台凭证 AK=$(mask "$AK")"
  printf '%s' "$AK" | ssh "$SERVER" "cat > $SEC_DIR/VOLCANO_ACCESS_KEY"
  printf '%s' "$SK" | ssh "$SERVER" "cat > $SEC_DIR/VOLCANO_SECRET_KEY"
  ssh "$SERVER" "chmod 644 $SEC_DIR/VOLCANO_ACCESS_KEY $SEC_DIR/VOLCANO_SECRET_KEY && ls -l $SEC_DIR/VOLCANO_ACCESS_KEY $SEC_DIR/VOLCANO_SECRET_KEY"
fi

# ── 2. 前置检查：切 visual 前必须有 AK/SK ──
if [ "$PROVIDER" = "visual" ]; then
  if ! ssh "$SERVER" "[ -s $SEC_DIR/VOLCANO_ACCESS_KEY ] && [ -s $SEC_DIR/VOLCANO_SECRET_KEY ]"; then
    echo "❌ 服务器缺少 VOLCANO_ACCESS_KEY / VOLCANO_SECRET_KEY，无法切到 visual。" >&2
    echo "   请加 --ak <AKLT...> --sk <Secret> 重新执行。" >&2
    exit 1
  fi
fi

OLD=$(ssh "$SERVER" "grep -E '^IMAGE_PROVIDER=' $ENV_FILE 2>/dev/null | cut -d= -f2" || true)
OLD=${OLD:-ark}
echo "→ 通道切换：${OLD} → ${PROVIDER}"

# ── 3. 写 .env ──
ssh "$SERVER" "
  touch $ENV_FILE
  if grep -qE '^IMAGE_PROVIDER=' $ENV_FILE; then
    sed -i 's|^IMAGE_PROVIDER=.*|IMAGE_PROVIDER=$PROVIDER|' $ENV_FILE
  else
    echo 'IMAGE_PROVIDER=$PROVIDER' >> $ENV_FILE
  fi
  grep -E '^IMAGE_PROVIDER=' $ENV_FILE
"

# ── 4. 重建 backend ──
echo "→ 重建 backend 使配置生效"
ssh "$SERVER" "cd $DIR && docker compose up -d --force-recreate backend" >/dev/null 2>&1
sleep 8

# ── 5. 容器内实测出图，失败则自动回滚 ──
echo "→ 容器内实测出图（真实调用一次）"
if ssh "$SERVER" "cd $DIR && docker compose exec -T -e PYTHONPATH=/app -w /app backend python - <<'PY'
import sys
from app import config
from app.services import image_service
print('  provider :', config.IMAGE_PROVIDER)
try:
    res = image_service.generate_word_image('林檎', '苹果', 'りんご', '林檎を食べます。', '吃苹果。')
    print('  结果     : OK，data URI 长度', len(res), '| 前缀', res[:30])
except Exception as exc:
    print('  结果     : 失败 ->', exc)
    sys.exit(1)
PY"; then
  echo "✅ 通道已切换到 ${PROVIDER} 并实测出图成功"
else
  echo "❌ ${PROVIDER} 通道实测失败，正在自动回滚到 ${OLD} …" >&2
  ssh "$SERVER" "sed -i 's|^IMAGE_PROVIDER=.*|IMAGE_PROVIDER=$OLD|' $ENV_FILE"
  ssh "$SERVER" "cd $DIR && docker compose up -d --force-recreate backend" >/dev/null 2>&1
  sleep 8
  echo "已回滚到 ${OLD}，请检查凭证/配额后重试。" >&2
  exit 1
fi
