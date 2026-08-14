#!/bin/bash
for p in achievement admin; do
  code=$(curl -skL -o /dev/null -w '%{http_code}' "https://127.0.0.1/$p")
  js=$(curl -skL "https://127.0.0.1/$p" | grep -c "js/$p.js")
  echo "/$p:$code js=$js"
done
echo "index-achievement-残留:$(curl -skL https://127.0.0.1/ | grep -c page-achievement)"
echo "index-admin-残留:$(curl -skL https://127.0.0.1/ | grep -c page-admin)"
