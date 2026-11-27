"""Narrow build-environment fix for pinned p4a v2026.05.09.

Upstream issue #3339: mixed pip files in reused build/venv.
The initial pip/Cython install must also not import target site-packages.
No change to the actual target package install or any verification.
"""
from pathlib import Path
import sys

def patch(path):
    path = Path(path)
    text = path.read_text()
    replacements = (
        ("shprint(host_python, '-m', 'venv', 'venv')",
         "shprint(host_python, '-m', 'venv', '--clear', 'venv')"),
        ('base_env["PYTHONPATH"] = ctx.get_site_packages_dir(arch)',
         'base_env["PYTHONPATH"] = ""'),
    )
    for old, new in replacements:
        if text.count(old) == 1:
            text = text.replace(old, new, 1)
        elif text.count(old) == 0 and text.count(new) == 1:
            continue
        else:
            raise SystemExit("Unexpected upstream source; inspect before updating the patch")
    compile(text, str(path), "exec")
    path.write_text(text)
    print("Verified p4a build environment isolation patch")

if __name__ == "__main__":
    patch(sys.argv[1])
