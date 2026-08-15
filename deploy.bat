@echo off
rem 部署包装器：显式使用 Git Bash 执行 deploy.sh
rem （系统 bash.exe 指向 WSL，但本机未安装 Linux 发行版，只有 docker-desktop 内部后端，无法运行 /bin/bash）
rem 用法：deploy.bat [rollback]
"D:\Git\Git\bin\bash.exe" deploy.sh %*
