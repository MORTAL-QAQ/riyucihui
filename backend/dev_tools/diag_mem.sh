#!/bin/bash
echo "=== 系统内存 ==="
free -h
echo ""
echo "=== 内存占用 TOP 进程 ==="
ps aux --sort=-%mem | head -12
echo ""
echo "=== Docker 容器内存 ==="
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}"
echo ""
echo "=== 容器启动时长 ==="
docker ps --format "table {{.Names}}\t{{.Status}}"
