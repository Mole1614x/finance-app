#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 scripts/init_demo_env.py
docker compose up --build -d --wait --wait-timeout 180
docker compose ps
curl --fail --silent --show-error http://127.0.0.1:8000/ready
printf '\\n'
echo 'Local demo API: http://127.0.0.1:8000/docs'
