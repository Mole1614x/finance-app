#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
if [ ! -d .venv-mobile ]; then
  python3 -m venv .venv-mobile
fi
. .venv-mobile/bin/activate
python -m pip install -r mobile/requirements.txt
curl --fail --silent --show-error http://127.0.0.1:8000/ready >/dev/null || { echo "Start the local demo backend first: sh scripts/start-demo.sh" >&2; exit 1; }
exec python -m mobile.main
