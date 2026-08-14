#!/bin/bash
# 全量独立页回归 + 统一顶栏验证
for p in community wordbank study generate essay cloze grammar image settings achievement admin saved; do
  code=$(curl -skL -o /dev/null -w '%{http_code}' "https://127.0.0.1/$p")
  js=$(curl -skL "https://127.0.0.1/$p" | grep -c "js/$p.js")
  nav=$(curl -skL "https://127.0.0.1/$p" | grep -o "border-radius:999px" | wc -l)
  echo "/$p:$code js=$js nav=$nav"
done
echo "index-saved-残留:$(curl -skL https://127.0.0.1/ | grep -c page-saved)"
echo "index-home-正常:$(curl -skL https://127.0.0.1/ | grep -c 'page-home')"
