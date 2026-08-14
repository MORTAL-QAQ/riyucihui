#!/bin/bash
cd /opt/riyucihui
echo "== URL 直达（nginx try_files 回退）=="
for p in community wordbank study; do
  code=$(curl -sk -m 10 -o /dev/null -w "%{http_code}" https://127.0.0.1/$p)
  echo "$p -> $code"
done
echo "== 静态资源 =="
echo "css/desktop.css -> $(curl -sk -m 10 -o /dev/null -w '%{http_code}' https://127.0.0.1/css/desktop.css)"
echo "== 未匹配 API 404 =="
echo "api/nonexistent -> $(curl -sk -m 10 -o /dev/null -w '%{http_code}' https://127.0.0.1/api/nonexistent)"
echo "== 前端版本号 =="
grep -o 'app.js?v=[0-9a-f]*' frontend/index.html
H=$(md5sum frontend/js/app.js | cut -c1-8)
echo "文件哈希前缀: $H"
