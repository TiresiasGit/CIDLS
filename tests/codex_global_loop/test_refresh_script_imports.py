import importlib.util
import sys
from pathlib import Path


def _load_script(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_refresh_script_loads_audit_constants():
    repo_root = Path(__file__).resolve().parents[2]
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    refresh_script = repo_root / "scripts" / "refresh_global_cidls_devrag.py"

    module = _load_script(refresh_script)

    assert module.GLOBAL_GENERATOR_PATH.name == "build-runtime-config.py"
    assert module.GLOBAL_RUNTIME_CONFIG_PATH.name == "runtime-devrag-config.json"
