#!/usr/bin/env bash
# 生产实测：容器内真实调用一次 AI 配图，验证当前部署的密钥能否出图。
#
# 用法（本机需用 Git Bash）：
#   & "D:\Git\Git\bin\bash.exe" backend/dev_tools/verify_image_gen.sh
#
# 退出码：0=出图成功，非 0=失败（失败原因直接打印在下面）

set -euo pipefail

SERVER="root@101.37.204.74"
DIR="/opt/riyucihui"

echo "→ 当前生效密钥前缀（脱敏）"
ssh "$SERVER" "cut -c1-8 $DIR/secrets/VOLCANO_API_KEY; echo; wc -c < $DIR/secrets/VOLCANO_API_KEY"

echo "→ 容器内实测出图"
ssh "$SERVER" "cd $DIR && docker compose exec -T -e PYTHONPATH=/app -w /app backend python - <<'PY'
from app.services import image_service
from app import config

print('provider :', getattr(config, 'IMAGE_PROVIDER', 'ark（旧版无该配置）'))
print('model    :', config.VOLCANO_IMAGE_MODEL)
try:
    res = image_service.generate_word_image('林檎', '苹果', 'りんご', '林檎を食べます。', '吃苹果。')
    print('结果     : OK，图片 data URI 长度', len(res))
except Exception as exc:
    print('结果     : 失败 ->', exc)
    raise SystemExit(1)
PY"

echo "✅ 生产出图正常"
