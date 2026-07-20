#!/bin/bash
# Format entire project
set -e

cd "$(dirname "$0")"

echo "=== Formatting Python (ruff) ==="
cd backend
ruff format .
ruff check --fix .
cd ..

echo ""
echo "=== Formatting frontend (prettier) ==="
cd frontend
npm run format
cd ..

echo ""
echo "Done."
