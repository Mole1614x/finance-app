#!/usr/bin/env bash
# Run on a supported Linux build host; Buildozer downloads SDK/NDK.
set -euo pipefail
cd "$(dirname "$0")/../mobile"
command -v buildozer >/dev/null || { echo "Install the Android build requirements first." >&2; exit 1; }
export PYTHONFORANDROID_PREREQUISITES_INSTALL_INTERACTIVE=0
# Dual-ABI native builds plus final APK packaging need substantial scratch space.
# Reclaim only unrelated preinstalled toolchains on disposable GitHub-hosted Linux.
# Never remove the Android SDK, Java, Python, or any files on a developer machine.
if [ "${GITHUB_ACTIONS:-}" = true ] && [ "${RUNNER_ENVIRONMENT:-}" = github-hosted ] && [ "${RUNNER_OS:-}" = Linux ]; then
  df -h "$PWD" "$HOME"
  sudo rm -rf /usr/share/dotnet /opt/ghc /usr/local/.ghcup /usr/local/share/boost
  df -h "$PWD" "$HOME"
  # Keep Gradle settings isolated to this CI job; cap concurrent packaging work.
  export GRADLE_USER_HOME="${RUNNER_TEMP:?}/arth-gradle"
  mkdir -p "$GRADLE_USER_HOME"
  cat > "$GRADLE_USER_HOME/gradle.properties" <<'EOF'
org.gradle.logging.stacktrace=all
org.gradle.workers.max=2
org.gradle.parallel=false
EOF
fi
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
# Prepare pinned upstream source with an auditable, narrow pip isolation fix.
p4a_source="$PWD/.buildozer/arth-p4a-source"
mkdir -p "$(dirname "$p4a_source")"
if [ ! -d "$p4a_source/.git" ]; then
  git clone --depth 1 --branch v2026.05.09 https://github.com/kivy/python-for-android.git "$p4a_source"
fi
test "$(git -C "$p4a_source" describe --tags --exact-match HEAD)" = v2026.05.09
python ../scripts/patch_p4a.py "$p4a_source/pythonforandroid/build.py"
export APP_P4A_SOURCE_DIR="$p4a_source"
if ! buildozer -v android debug; then
  echo "Android build failed; remaining disk space and memory:" >&2
  df -h "$PWD" "$HOME" >&2 || true
  free -h >&2 || true
  exit 1
fi
python ../scripts/verify_android_apk.py bin
