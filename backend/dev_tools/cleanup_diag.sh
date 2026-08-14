#!/bin/bash
cd /opt/riyucihui
docker compose exec -T postgres psql -U jpvocab -d jpvocab -c "DELETE FROM users WHERE username LIKE 'diag_%';"
