#!/bin/bash
# 容器入口（#8）：以 root 启动以修正数据卷属主，随后降权为 appuser 运行主进程。
# 避免容器以 root 运行（纵深防御：即使应用被攻破也不直接获得 root）。
set -e

# 数据卷（backend_data:/app/data）可能由 root 属主，降权前修正
if [ -d /app/data ]; then
    chown -R appuser:appuser /app/data 2>/dev/null || true
fi

# 以降权用户执行 CMD（uvicorn ...）
exec su appuser -s /bin/sh -c "exec $*"
