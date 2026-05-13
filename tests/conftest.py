import shutil
import sys
import uuid
from pathlib import Path

import pytest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture
def tmp_path():
    root_dir = Path(__file__).resolve().parents[1] / "reports" / "pytest_tmp"
    root_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = root_dir / f"pytest_local_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_png(tmp_path):
    png_path = tmp_path / "sample.png"
    png_path.write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
            "0000000c4944415408d763f8ffff3f0005fe02fea73581e40000000049454e44ae426082"
        )
    )
    return png_path


@pytest.fixture
def browser_path():
    candidates = [
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None
