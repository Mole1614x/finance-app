import pytest
from scripts.patch_p4a import patch

def test_p4a_patch_is_idempotent(tmp_path):
    path = tmp_path / "build.py"
    path.write_text("def install():\n    shprint(host_python, '-m', 'venv', 'venv')\n    base_env[\"PYTHONPATH\"] = ctx.get_site_packages_dir(arch)\n")
    patch(path)
    first = path.read_text()
    assert "'--clear'" in first
    assert 'base_env["PYTHONPATH"] = ""' in first
    patch(path)
    assert path.read_text() == first

def test_patch_rejects_unknown_upstream(tmp_path):
    path = tmp_path / "build.py"
    path.write_text("pass\n")
    with pytest.raises(SystemExit):
        patch(path)
    assert path.read_text() == "pass\n"
