#!/bin/bash
# 全量独立页回归验证
for p in community wordbank study generate essay cloze grammar image settings achievement admin saved; do
  code=$(curl -skL -o /dev/null -w '%{http_code}' "https://127.0.0.1/$p")
  js=$(curl -skL "https://127.0.0.1/$p" | grep -c "js/$p.js")
  echo "/$p:$code js=$js"
done
echo "index-saved-残留:$(curl -skL https://127.0.0.1/ | grep -c page-saved)"
echo "index-modal-残留:$(curl -skL https://127.0.0.1/ | grep -c modal-body)"
echo "index-home-正常:$(curl -skL https://127.0.0.1/ | grep -c 'page-home')"
