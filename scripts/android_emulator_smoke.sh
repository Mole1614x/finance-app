#!/usr/bin/env bash
# Dedicated emulator only. No real account or payment.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p android-test-output
cleanup() {
  adb logcat -d > android-test-output/logcat.txt || true
  adb exec-out screencap -p > android-test-output/screenshot.png || true
  if [ -n "${backend_pid:-}" ]; then kill "$backend_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
export DATABASE_URL="sqlite:///$(mktemp -d)/android-demo.db"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 > android-test-output/backend.log 2>&1 &
backend_pid=$!
for i in $(seq 1 60); do
  if curl --fail --silent http://127.0.0.1:8000/ready >/dev/null; then break; fi
  sleep 1
done
curl --fail http://127.0.0.1:8000/ready
adb wait-for-device
adb reverse tcp:8000 tcp:8000
apk=$(find mobile/bin -maxdepth 1 -name '*.apk' -print -quit)
test -n "$apk"
adb install -r "$apk"
adb shell am force-stop com.arth.arth
adb logcat -c
adb shell am start -W -n com.arth.arth/org.kivy.android.PythonActivity --ez arth_smoke true
for i in $(seq 1 90); do
  adb logcat -d > android-test-output/logcat.txt
  if grep -q ARTH_ANDROID_NATIVE_FAILED android-test-output/logcat.txt || grep -q ARTH_ANDROID_UI_FAILED android-test-output/logcat.txt; then
    echo "Android diagnostic failed"; exit 1
  fi
  if grep -q ARTH_ANDROID_UI_OK android-test-output/logcat.txt &&
     grep -q ARTH_ANDROID_QR_OK android-test-output/logcat.txt &&
     grep -q ARTH_ANDROID_BACKEND_OK android-test-output/logcat.txt &&
     adb shell pidof com.arth.arth >/dev/null; then
    echo "Android startup, native QR decoder and loopback backend passed"
    exit 0
  fi
  sleep 2
done
echo "Android smoke markers were not all observed" >&2
exit 1
