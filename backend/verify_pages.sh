#!/bin/bash
# 验证独立页部署（跟随重定向 + 忽略证书）
for p in image settings achievement; do
  code=$(curl -skL -o /dev/null -w '%{http_code}' "https://127.0.0.1/$p")
  echo "/$p:$code"
done
code=$(curl -skL -o /dev/null -w '%{http_code}' "https://127.0.0.1/")
echo "/:$code"
echo "index-page-settings-残留:$(curl -skL https://127.0.0.1/ | grep -c page-settings)"
echo "index-page-achievement-残留:$(curl -skL https://127.0.0.1/ | grep -c page-achievement)"
echo "image-js引用:$(curl -skL https://127.0.0.1/image | grep -c 'js/image.js')"
echo "settings-js引用:$(curl -skL https://127.0.0.1/settings | grep -c 'js/settings.js')"
echo "achievement-js引用:$(curl -skL https://127.0.0.1/achievement | grep -c 'js/achievement.js')"
