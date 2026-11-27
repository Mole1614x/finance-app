# PR 15 — Android debug build and emulator verification

Build configuration: Buildozer 1.6.0, Python-for-Android v2026.05.09, Android API 35, minimum API 24, NDK r28c, ARM64 and x86-64. The previous 32-bit ARM target is removed for this initial two-ABI demo build. OpenCV is a native cross-compiled dependency and must actually decode a generated QR on the emulator before CI passes. The backend stays on the host; no backend secrets, database or models are packaged in the APK. No release signing keys or Play Store publication.

GitHub Actions builds a debug APK, verifies its archive/native ABIs and uploads it with SHA-256. A separate emulator job installs the same artifact, starts a disposable SQLite backend on host loopback, uses adb reverse tcp:8000 tcp:8000, starts the Python activity with an explicit diagnostic intent and checks the UI, generated QR decoding and actual backend /health request. Logs and screenshot are uploaded. These are required CI jobs, not optional pass-through. The diagnostic is not invoked by ordinary launches. Emulator cameras are disabled; no real camera, login or payment flow is tested on Android by this smoke test.

## Build locally (Linux)
Use Ubuntu 24.04 with Python 3.11, Java 17, git, zip, unzip, autoconf, libtool, libtool-bin, libltdl-dev, pkg-config, zlib1g-dev, libncurses-dev, libtinfo6, cmake, ninja-build, libffi-dev, libssl-dev, automake, autopoint and gettext. Follow https://buildozer.readthedocs.io/en/1.6.0/installation/ and https://python-for-android.readthedocs.io/en/v2026.05.09/quickstart.html for toolchain prerequisites. From repo root:

    python3 -m venv .venv-android
    source .venv-android/bin/activate
    pip install -r mobile/android-build-requirements.txt
    bash scripts/build_android.sh

Use an empty mobile/bin for a new build; archive old APKs elsewhere. Build outputs go to mobile/bin. On macOS, use CI's Linux artifact or a Linux build host rather than assuming local toolchain compatibility.

## Install on a test device
Download the arth-android-debug artifact from a successful CI run and verify its checksum. Unzip the artifact. Start the existing local backend (sh scripts/start-demo.sh or local Uvicorn with separate environment). Connect your own USB-debug-enabled device and confirm the ADB authorization:

    adb devices
    adb reverse tcp:8000 tcp:8000
    adb install -r path/to/arth-debug.apk

Use fictional @example.com credentials and demo OTP only. The app's default API remains 127.0.0.1:8000; ADB reverse keeps the server local. No public port or arbitrary cleartext LAN URL is introduced. Disconnect the reverse tunnel after testing with adb reverse --remove tcp:8000.

## Manual physical-device checklist (not executed)
- Install and launch, sign up/sign in with demo OTP, initialize checking/savings.
- Scan a second demo user's QR, deny then grant camera permission, check pause/resume and stop.
- Review and confirm a simulated send; confirm receipt and ledger balances.
- Interrupt a peer payment, force-stop/relaunch, sign in again, recover using original reference; check duplicate protection and cancellation.
- Verify bill purchases, savings, insights and logout.
- Record device model, Android version, APK hash, logs and actual pass/fail evidence.

No real-device test, store compliance, signed production APK, iOS build, or exact Figma parity is claimed. Debug package is for isolated demo use only.

## Build troubleshooting
The first PR 15 build failed during libffi 3.4.2 autogen with `possibly undefined macro: LT_SYS_SYMBOL_USCORE`. Install `libltdl-dev` (and `libtool-bin`) in the Ubuntu build environment. The build script now runs an isolated Autoconf macro preflight before invoking Buildozer. If a previous local native build failed, clean the generated Buildozer build directory before retrying. This change does not disable or bypass any APK or emulator checks. See https://github.com/kivy/python-for-android/issues/1728 for the matching missing-macro dependency report.
