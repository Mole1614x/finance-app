#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 scripts/init_demo_env.py
docker compose up --build -d
docker compose ps
echo 'Local demo API: http://127.0.0.1:8000/docs'
