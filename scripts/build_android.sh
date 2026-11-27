#!/usr/bin/env bash
# Run on a supported Linux build host; Buildozer downloads SDK/NDK.
set -euo pipefail
cd "$(dirname "$0")/../mobile"
command -v buildozer >/dev/null || { echo "Install the Android build requirements first." >&2; exit 1; }
export PYTHONFORANDROID_PREREQUISITES_INSTALL_INTERACTIVE=0
# libffi 3.4.2 uses this macro; fail early rather than after cross compilation.
probe="$(mktemp -d)"
trap 'rm -rf "$probe"' EXIT
cat > "$probe/configure.ac" <<'EOF'
AC_INIT([arth-libtool-check], [1])
AC_CONFIG_SRCDIR([configure.ac])
AC_PROG_CC
LT_INIT
LT_SYS_SYMBOL_USCORE
AC_OUTPUT
EOF
if ! (cd "$probe" && autoreconf -fi); then
  echo "Missing libtool Autoconf macros. On Ubuntu install libtool, libtool-bin and libltdl-dev." >&2
  exit 1
fi
buildozer -v android debug
python ../scripts/verify_android_apk.py bin
