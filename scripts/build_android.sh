#!/usr/bin/env bash
# Run on a supported Linux build host; Buildozer downloads SDK/NDK.
set -euo pipefail
cd "$(dirname "$0")/../mobile"
command -v buildozer >/dev/null || { echo "Install the Android build requirements first." >&2; exit 1; }
export PYTHONFORANDROID_PREREQUISITES_INSTALL_INTERACTIVE=0
buildozer -v android debug
python ../scripts/verify_android_apk.py bin
