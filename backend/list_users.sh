#!/bin/bash
cd /opt/riyucihui
docker compose exec -T postgres psql -U jpvocab -d jpvocab -c "SELECT id, username, COALESCE(name, username) AS name, is_admin, created_at FROM users ORDER BY id;"
