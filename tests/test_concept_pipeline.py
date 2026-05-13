import json

from cidls.concept_pipeline.generator import build_default_spec, materialize_pipeline


def test_default_spec_uses_codex_builder():
    spec = build_default_spec()
    payload = json.dumps(spec.to_dict(), ensure_ascii=False)
    blocked_builder_label = "v" + "0"

    assert "Codexビルダー" in payload
    assert "外部Webビルダー" in payload
    assert blocked_builder_label not in payload
    assert "繝" not in payload
    assert "縺" not in payload


def test_default_spec_has_required_deliverables():
    spec = build_default_spec()

    assert set(spec.deliverable_keys()) == {
        "app_blueprint",
        "system_da_table",
        "project_graph_mindmap",
        "screen_overview",
        "screen_state_design",
        "concept_slide",
        "subscription_story",
        "delivery_docs_pack",
    }


def test_materialize_pipeline_writes_local_outputs(tmp_path):
    report = materialize_pipeline(
        output_dir=tmp_path,
        concept_title="受入検証プロジェクト",
    )

    expected_files = [
        "cidls_pipeline_spec.md",
        "app_blueprint.html",
        "system_da_table.html",
        "graph_project_mindmap.html",
        "screen_overview.svg",
        "screen_state_design.html",
        "concept_slide.html",
        "STORY.html",
        "delivery_docs/requirements_definition.md",
        "delivery_docs/basic_design.md",
        "delivery_docs/detailed_design.md",
        "delivery_docs/test_specification.md",
        "delivery_docs/operations_runbook.md",
        "delivery_docs/acceptance_checklist.md",
        "cidls_pipeline_report.json",
    ]
    for filename in expected_files:
        assert (tmp_path / filename).exists()

    assert report["ok"] is True
    assert report["deployment_performed"] is False
    assert report["deliverable_count"] == 8

    spec_text = (tmp_path / "cidls_pipeline_spec.md").read_text(encoding="utf-8")
    story_text = (tmp_path / "STORY.html").read_text(encoding="utf-8")
    assert "Stripe Billing" in story_text
    assert "Stripe Secret" in story_text
    assert "Webhook" in story_text
    assert "画像内容の日本語変換" in spec_text
    assert "Codexは外部Webビルダーの代替" in spec_text
    assert "繝" not in spec_text
    assert "縺" not in spec_text
