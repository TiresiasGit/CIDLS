import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from cidls.commercial_delivery.generator import (
    build_commercial_delivery_package,
    render_story_html,
)


MOJIBAKE_MARKERS = ("繝", "縺", "繧", "譛", "蜿", "逕", "髱")


def read_xlsx_parts(path):
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name).decode("utf-8") for name in archive.namelist()}


def test_story_html_is_japanese_commercial_contract_level(tmp_path):
    package = build_commercial_delivery_package(
        output_dir=tmp_path,
        project_name="CIDLS商用請負納品パッケージ",
    )
    story_text = Path(package["story_path"]).read_text(encoding="utf-8")

    assert "<html lang=\"ja\">" in story_text
    assert "商用請負レベル" in story_text
    assert "A5:SQL Mk-2" in story_text
    assert "Stripe Billing" in story_text
    assert "Webhook" in story_text
    assert "検収" in story_text
    for marker in MOJIBAKE_MARKERS:
        assert marker not in story_text

    rendered = render_story_html("CIDLS商用請負納品パッケージ")
    assert "プロダクトオーナー" in rendered
    assert "バックエンドサーバー" in rendered


def test_excel_pack_contains_required_japanese_sheets_and_a5m2_columns(tmp_path):
    package = build_commercial_delivery_package(
        output_dir=tmp_path,
        project_name="CIDLS商用請負納品パッケージ",
    )
    workbook_path = Path(package["workbook_path"])
    parts = read_xlsx_parts(workbook_path)

    workbook_xml = parts["xl/workbook.xml"]
    required_sheets = (
        "00_表紙",
        "03_要求要件定義",
        "09_DB定義_A5M2",
        "10_テーブル定義",
        "11_カラム定義",
        "21_テスト観点",
        "29_抜け漏れチェック",
        "32_調査根拠",
    )
    for sheet_name in required_sheets:
        assert sheet_name in workbook_xml

    all_xml = "\n".join(parts.values())
    required_columns = (
        "論理テーブル名",
        "物理テーブル名",
        "カラム論理名",
        "カラム物理名",
        "データ型",
        "桁数",
        "NULL",
        "主キー",
        "インデックス",
        "外部キー",
    )
    for column in required_columns:
        assert column in all_xml

    assert "A5:SQL Mk-2" in all_xml
    assert "IPA 共通フレーム" in all_xml
    assert "IPA 非機能要求グレード" in all_xml
    for marker in MOJIBAKE_MARKERS:
        assert marker not in all_xml


def test_excel_pack_has_fine_grained_checklist_and_traceability(tmp_path):
    package = build_commercial_delivery_package(
        output_dir=tmp_path,
        project_name="CIDLS商用請負納品パッケージ",
    )
    parts = read_xlsx_parts(Path(package["workbook_path"]))
    all_xml = "\n".join(parts.values())

    assert package["sheet_count"] >= 30
    assert "項番" in all_xml
    assert "判定基準" in all_xml
    assert "証跡リンク" in all_xml
    assert "SourceType" in all_xml
    assert "Given-When-Then" in all_xml
    assert "契約・決済・Webhook・キャンセル・入金" in all_xml
    assert "水平展開" in all_xml

    workbook_root = ElementTree.fromstring(parts["xl/workbook.xml"])
    namespace = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    sheet_count = len(workbook_root.findall(".//m:sheet", namespace))
    assert sheet_count == package["sheet_count"]

    worksheet_names = re.findall(r"name=\"([^\"]+)\"", parts["xl/workbook.xml"])
    assert len(set(worksheet_names)) == len(worksheet_names)
