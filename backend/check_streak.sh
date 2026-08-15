#!/bin/bash
cd /opt/riyucihui
docker compose exec -T postgres psql -U jpvocab -d jpvocab -c "SELECT key, count(*) FROM achievements WHERE key LIKE 'streak%' GROUP BY key ORDER BY key;"
