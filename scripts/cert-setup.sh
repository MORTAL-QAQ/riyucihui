#!/bin/bash
# AIGC多模态日语词汇学习 — TLS 证书设置
#
#   bash cert-setup.sh self-signed       开发/测试用自签名证书
#   bash cert-setup.sh production         Let's Encrypt 正式证书（需域名）
#
# 生产环境首次运行前请修改下方 DOMAIN 和 EMAIL 变量。

set -e
cd "$(dirname "$0")"

DOMAIN="${DOMAIN:-example.com}"
EMAIL="${EMAIL:-admin@example.com}"

mkdir -p certs
mkdir -p certbot-webroot/.well-known/acme-challenge

case "${1:-}" in

self-signed)
    echo "=== 生成自签名证书（仅测试用） ==="
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout certs/privkey.pem \
        -out certs/fullchain.pem \
        -subj "/CN=${DOMAIN}"
    echo ""
    echo "已生成 certs/privkey.pem 和 certs/fullchain.pem"
    echo "现在可以运行: docker compose up -d"
    echo "浏览器访问 https://${DOMAIN} 时会提示不安全，点击「高级」→「继续访问」即可。"
    ;;

production)
    echo "=== 获取 Let's Encrypt 正式证书 ==="
    echo "域名: ${DOMAIN}"
    echo "邮箱: ${EMAIL}"
    echo ""

    # 确保 80 端口可达（nginx 用于 ACME 验证）
    if ! docker compose ps nginx 2>/dev/null | grep -q Up; then
        echo "正在启动 nginx（用于 ACME 验证）..."
        docker compose up -d nginx
        sleep 2
    fi

    docker compose run --rm certbot \
        certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "${EMAIL}" \
        --agree-tos \
        --no-eff-email \
        --force-renewal \
        -d "${DOMAIN}"

    # certbot 将证书存入 certs/live/${DOMAIN}/，复制到 nginx 期望的位置
    if [ -d "certs/live/${DOMAIN}" ]; then
        cp "certs/live/${DOMAIN}/fullchain.pem" certs/fullchain.pem
        cp "certs/live/${DOMAIN}/privkey.pem" certs/privkey.pem
        echo ""
        echo "证书已就位。重启 nginx 生效:"
        echo "  docker compose restart nginx"
        echo ""
        echo "设置自动续期（添加到 crontab）:"
        echo "  0 3 * * * cd $(pwd) && docker compose run --rm certbot renew --quiet && docker compose restart nginx"
    else
        echo "错误: 证书获取失败，请检查域名 DNS 是否正确指向本服务器。"
        exit 1
    fi
    ;;

*)
    echo "用法: bash cert-setup.sh <mode>"
    echo "  self-signed   自签名证书（测试用）"
    echo "  production    Let's Encrypt 正式证书（需域名 + 公网可达）"
    exit 1
    ;;

esac
