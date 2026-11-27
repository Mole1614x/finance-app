"""Verify one debug APK contains both supported ABIs."""
import hashlib
from pathlib import Path
import sys
from zipfile import ZipFile

def verify(directory):
    apks = sorted(Path(directory).glob("*.apk"))
    if len(apks) != 1:
        raise SystemExit(f"Expected exactly one APK, found {len(apks)}")
    apk = apks[0]
    with ZipFile(apk) as archive:
        if archive.testzip() is not None:
            raise SystemExit("Corrupt APK")
        names = archive.namelist()
        if "AndroidManifest.xml" not in names or "classes.dex" not in names:
            raise SystemExit("APK is missing Android app content")
        for abi in ("arm64-v8a", "x86_64"):
            if not any(name.startswith(f"lib/{abi}/") and name.endswith(".so") for name in names):
                raise SystemExit(f"Missing native libraries: {abi}")
    digest = hashlib.file_digest(apk.open("rb"), "sha256").hexdigest()
    apk.with_suffix(".apk.sha256").write_text(f"{digest}  {apk.name}\n")
    print(f"Verified APK archive and ABIs: {apk}")

if __name__ == "__main__":
    verify(sys.argv[1])
