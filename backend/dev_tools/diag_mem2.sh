#!/bin/bash
echo "=== postgres 连接数 ==="
docker exec jp-vocab-db psql -U jpvocab -d jpvocab -t -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;" 2>/dev/null
echo ""
echo "=== voicevox 容器内缓存/数据目录 ==="
docker exec jp-vocab-voicevox sh -c 'du -sh /tmp/* 2>/dev/null | sort -rh | head -5; ls -la /opt/voicevox_core 2>/dev/null | head -5' 2>/dev/null
echo ""
echo "=== backend 容器内存明细（RSS 各进程） ==="
docker exec jp-vocab-backend sh -c 'ps aux --sort=-%mem | head -6' 2>/dev/null
echo ""
echo "=== voicevox 音频缓存（本地镜像对应目录） ==="
docker exec jp-vocab-backend ls -la /app/data/voice_cache 2>/dev/null | head -5
echo ""
echo "=== 5秒后再次采样（观察增长趋势） ==="
free -m | head -2
sleep 5
free -m | head -2
