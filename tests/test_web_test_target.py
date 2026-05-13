import subprocess
from pathlib import Path
from urllib.parse import urlencode

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
TARGET_HTML = ROOT_DIR / "fixtures" / "web" / "ocr_test_target.html"


def _dump_dom(browser_path, scene, dataset):
    url = f"{TARGET_HTML.resolve().as_uri()}?{urlencode({'scene': scene, 'dataset': dataset})}"
    completed = subprocess.run(
        [browser_path, "--headless", "--disable-gpu", "--virtual-time-budget=4000", "--dump-dom", url],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr[-1000:])
    return completed.stdout


@pytest.mark.browser
def test_web_target_renders_form_scene(browser_path):
    if not browser_path:
        pytest.skip("browser executable not found")
    html = _dump_dom(browser_path, "form", "ja")
    assert "商用 OCR / LLM / RPAInput 検証コンソール" in html
    assert "scene=form / dataset=ja" in html
    assert "LLM state: PASS" in html
    assert "申請番号" in html
    assert "AP-2026-0417" in html


@pytest.mark.browser
def test_web_target_renders_table_noise_scene(browser_path):
    if not browser_path:
        pytest.skip("browser executable not found")
    html = _dump_dom(browser_path, "table", "table_noise")
    assert "scene=table / dataset=table_noise" in html
    assert "LLM state: PARTIAL" in html
    assert "〒160-0022" in html
    assert "OCR 誤字テスト" in html
