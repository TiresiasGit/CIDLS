from pathlib import Path

from cidls.ocr_pipeline.web_test_target import OCRWebTargetSession


def test_web_target_session_builds_query_url():
    session = OCRWebTargetSession(
        scene="table",
        dataset="table_noise",
        browser_path=r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        target_html="fixtures/web/ocr_test_target.html",
    )

    url = session.build_url()

    assert "scene=table" in url
    assert "dataset=table_noise" in url
    assert Path("fixtures/web/ocr_test_target.html").resolve().as_uri().split("?")[0] in url


def test_web_target_session_calculates_stable_capture_region():
    session = OCRWebTargetSession(
        browser_path=r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        window_position={"left": 40, "top": 50},
        window_size={"width": 1440, "height": 900},
    )

    region = session.default_capture_region()

    assert region == {"left": 96, "top": 246, "width": 1328, "height": 632}
