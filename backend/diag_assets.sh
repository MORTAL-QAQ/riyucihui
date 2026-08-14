#!/bin/bash
# 检查生产页面引用的 css/js 资源是否可加载
for p in generate study wordbank essay cloze grammar community image settings achievement admin saved; do
  html=$(curl -skL "https://127.0.0.1/$p")
  urls=$(echo "$html" | grep -oE '(src|href)="(/[^"]+\.(js|css)[^"]*)"' | sed -E 's/(src|href)="//; s/"$//')
  for u in $urls; do
    ct=$(curl -skL -o /dev/null -w '%{http_code}:%{content_type}' "https://127.0.0.1$u")
    echo "/$p -> $u [$ct]"
  done
done
