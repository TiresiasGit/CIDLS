"""Unit tests for compute_use.evolution_runner."""

import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import duckdb
import pytest

from cidls.compute_use.evolution_runner import (
    DAILY_GOAL,
    _build_counterfactual_challenge,
    _build_skill_eval_spec,
    _collect_web_research,
    _distill_lessons_from_log,
    _ensure_evolve_log_table,
    _log_evolution,
    _next_cycle_n,
    _verify_prior_predictions,
    build_evolution_description,
)


class TestEnsureEvolveLogTable:
    def test_creates_table(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        rows = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name='evolve_log'"
        ).fetchall()
        assert len(rows) == 1
        con.close()

    def test_idempotent(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        # should not raise on second call
        _ensure_evolve_log_table(con)
        con.close()


class TestNextCycleN:
    def test_empty_table(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        assert _next_cycle_n(con) == 1
        con.close()

    def test_increments(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        _log_evolution(con, 1, "h", "e", "d")
        assert _next_cycle_n(con) == 2
        _log_evolution(con, 2, "h2", "e2", None)
        assert _next_cycle_n(con) == 3
        con.close()


class TestLogEvolution:
    def test_inserts_row(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        _log_evolution(con, 1, "hyp1", "evidence1", "delta1")
        rows = con.execute("SELECT cycle_n, hypothesis FROM evolve_log").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == 1
        assert rows[0][1] == "hyp1"
        con.close()

    def test_null_delta(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        _log_evolution(con, 5, "h", "e", None)
        row = con.execute("SELECT delta_desc FROM evolve_log WHERE cycle_n=5").fetchone()
        assert row is not None
        # delta_desc should be "" (runner converts None to "")
        assert row[0] == ""
        con.close()

    def test_multiple_rows_unique_ids(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        _log_evolution(con, 1, "h1", "e1", "d1")
        _log_evolution(con, 2, "h2", "e2", "d2")
        rows = con.execute("SELECT log_id FROM evolve_log").fetchall()
        ids = [r[0] for r in rows]
        assert len(ids) == 2
        assert ids[0] != ids[1]
        con.close()


class TestDailyGoal:
    def test_goal_contains_web_collection(self) -> None:
        assert "Web" in DAILY_GOAL
        assert "反証" in DAILY_GOAL

    def test_goal_contains_png_reference(self) -> None:
        assert "CIDLSパイプラインコンセプトイメージ.png" in DAILY_GOAL

    def test_goal_contains_harness_engineering(self) -> None:
        assert "ハーネスエンジニアリング" in DAILY_GOAL


class TestCollectWebResearch:
    """_collect_web_research() のテスト (urllib をモック)."""

    def _make_ddg_response(self, abstract: str, url: str = "") -> bytes:
        import json as _json
        return _json.dumps({
            "AbstractText": abstract,
            "AbstractURL": url,
        }).encode("utf-8")

    def test_returns_snippet_on_success(self) -> None:
        fake_resp = MagicMock()
        fake_resp.read.return_value = self._make_ddg_response(
            "Claude AI can use computers autonomously.",
            "https://example.com/claude",
        )
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=fake_resp):
            result = _collect_web_research(queries=["test query"])

        assert "Claude AI can use computers" in result
        assert "https://example.com/claude" in result

    def test_empty_abstract_excluded(self) -> None:
        fake_resp = MagicMock()
        fake_resp.read.return_value = self._make_ddg_response("", "")
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=fake_resp):
            result = _collect_web_research(queries=["nothing query"])

        assert result == ""

    def test_network_failure_returns_empty(self) -> None:
        with patch("urllib.request.urlopen", side_effect=OSError("network down")):
            result = _collect_web_research(queries=["fail query"])
        assert result == ""

    def test_multiple_queries_joined(self) -> None:
        def fake_urlopen(req, timeout=10):
            m = MagicMock()
            import json as _json
            m.read.return_value = _json.dumps({
                "AbstractText": "result for query",
                "AbstractURL": "https://ex.com",
            }).encode()
            m.__enter__ = lambda s: s
            m.__exit__ = MagicMock(return_value=False)
            return m

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = _collect_web_research(queries=["q1", "q2"])

        assert result.count("result for query") == 2


class TestBuildEvolutionDescription:
    def test_contains_goal_text(self) -> None:
        desc = build_evolution_description(None)
        assert "CIDLSパイプライン" in desc
        assert "Web" in desc

    def test_with_concept_image_note(self) -> None:
        desc = build_evolution_description("base64data==")
        assert "concept_image" in desc.lower() or "vision" in desc.lower()

    def test_without_concept_image(self) -> None:
        desc = build_evolution_description(None)
        assert isinstance(desc, str)
        assert len(desc) > 50

    def test_web_research_injected(self) -> None:
        desc = build_evolution_description(None, web_research="AI pipeline insight here.")
        assert "AI pipeline insight here." in desc
        assert "Web収集情報" in desc

    def test_no_web_research_no_section(self) -> None:
        desc = build_evolution_description(None, web_research="")
        assert "Web収集情報" not in desc


class TestDistillLessonsFromLog:
    """_distill_lessons_from_log() - EvolveR offline distillation tests."""

    def test_empty_table_returns_empty_string(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        result = _distill_lessons_from_log(con)
        assert result == ""
        con.close()

    def test_single_entry_contains_cycle_n_and_hypothesis(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        _log_evolution(con, 1, "仮説テスト", "evidence", "改善内容テスト")
        result = _distill_lessons_from_log(con)
        assert "cycle_n=1" in result
        assert "仮説テスト" in result
        assert "改善内容テスト" in result
        con.close()

    def test_limits_to_max_entries(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        for i in range(1, 8):
            _log_evolution(con, i, f"hyp{i}", f"ev{i}", f"delta{i}")
        result = _distill_lessons_from_log(con, max_entries=3)
        # should contain the 3 most recent (7, 6, 5), not older ones
        assert "cycle_n=7" in result
        assert "cycle_n=6" in result
        assert "cycle_n=5" in result
        assert "cycle_n=1" not in result
        con.close()

    def test_null_delta_desc_excluded_gracefully(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        _log_evolution(con, 1, "hyp_no_delta", "ev", None)
        result = _distill_lessons_from_log(con)
        assert "hyp_no_delta" in result
        con.close()

    def test_returns_str_type(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        assert isinstance(_distill_lessons_from_log(con), str)
        con.close()


class TestBuildEvolutionDescriptionWithLessons:
    """build_evolution_description() lessons parameter tests."""

    def test_lessons_section_injected_when_provided(self) -> None:
        desc = build_evolution_description(None, lessons="cycle_n=1: 仮説=テスト / 改善=実施済み")
        assert "過去サイクルからの知見" in desc
        assert "cycle_n=1" in desc
        assert "EvolveR" in desc

    def test_no_lessons_section_when_empty(self) -> None:
        desc = build_evolution_description(None, lessons="")
        assert "過去サイクルからの知見" not in desc

    def test_lessons_appears_before_web_research(self) -> None:
        desc = build_evolution_description(
            None,
            web_research="web snippet here",
            lessons="past lesson here",
        )
        lessons_pos = desc.index("過去サイクルからの知見")
        web_pos = desc.index("Web収集情報")
        assert lessons_pos < web_pos


class TestLogEvolutionWithPredictions:
    """_log_evolution() の predicted_fixes / predicted_regressions パラメータのテスト."""

    def test_stores_predicted_fixes(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        _log_evolution(con, 1, "h", "e", "d", predicted_fixes="fix_A, fix_B")
        row = con.execute("SELECT predicted_fixes FROM evolve_log WHERE cycle_n=1").fetchone()
        assert row is not None
        assert "fix_A" in row[0]
        con.close()

    def test_stores_predicted_regressions(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        _log_evolution(con, 2, "h", "e", "d", predicted_regressions="module_X might break")
        row = con.execute(
            "SELECT predicted_regressions FROM evolve_log WHERE cycle_n=2"
        ).fetchone()
        assert row is not None
        assert "module_X" in row[0]
        con.close()

    def test_defaults_to_empty_string_when_none(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        _log_evolution(con, 3, "h", "e", "d")
        row = con.execute(
            "SELECT predicted_fixes, predicted_regressions FROM evolve_log WHERE cycle_n=3"
        ).fetchone()
        assert row is not None
        assert row[0] == ""
        assert row[1] == ""
        con.close()


class TestVerifyPriorPredictions:
    """_verify_prior_predictions() - AHE Decision Observability tests."""

    def test_returns_empty_when_no_prediction_recorded(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        _log_evolution(con, 1, "h", "e", "d")  # no predicted_fixes
        result = _verify_prior_predictions(con, 1)
        assert result == ""
        con.close()

    def test_returns_summary_with_fixes_prediction(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        _log_evolution(con, 1, "h", "e", "d", predicted_fixes="test_foo will pass")
        _log_evolution(con, 2, "h2", "e2", "delta with test_foo confirmed")
        result = _verify_prior_predictions(con, 1)
        assert "予測Fix" in result
        assert "test_foo will pass" in result
        assert "Cycle 1" in result
        con.close()

    def test_shows_outcome_from_next_cycle(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        _log_evolution(con, 5, "h5", "e5", "d5", predicted_fixes="F1", predicted_regressions="R1")
        _log_evolution(con, 6, "h6", "e6", "actual outcome text")
        result = _verify_prior_predictions(con, 5)
        assert "actual outcome text" in result
        assert "予測Regression" in result
        assert "R1" in result
        con.close()

    def test_missing_next_cycle_shows_not_recorded(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        _log_evolution(con, 9, "h9", "e9", "d9", predicted_fixes="some fix")
        result = _verify_prior_predictions(con, 9)
        assert "未記録" in result
        con.close()

    def test_returns_empty_for_nonexistent_cycle(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        result = _verify_prior_predictions(con, 99)
        assert result == ""
        con.close()

    def test_distill_includes_prediction_accuracy(self, tmp_path: Path) -> None:
        db = tmp_path / "test.duckdb"
        con = duckdb.connect(str(db))
        _ensure_evolve_log_table(con)
        _log_evolution(con, 1, "initial hyp", "ev1", "delta1", predicted_fixes="fix_X")
        _log_evolution(con, 2, "second hyp", "ev2", "delta2 includes fix_X outcome")
        distilled = _distill_lessons_from_log(con)
        assert "Decision Observability" in distilled
        assert "fix_X" in distilled
        con.close()


class TestBuildEvolutionDescriptionDecisionObservability:
    """build_evolution_description() に AHE Decision Observability 指示が含まれることを確認."""

    def test_contains_decision_observability_section(self) -> None:
        desc = build_evolution_description(None)
        assert "Decision Observability" in desc
        assert "predicted_fixes" in desc
        assert "predicted_regressions" in desc

    def test_contains_ahe_reference(self) -> None:
        desc = build_evolution_description(None)
        assert "2604.25850" in desc


class TestBuildCounterfactualChallenge:
    """_build_counterfactual_challenge() - 2026 Harness optimism-asymmetry countermeasure tests."""

    def test_returns_str(self) -> None:
        result = _build_counterfactual_challenge()
        assert isinstance(result, str)

    def test_contains_falsification_markers(self) -> None:
        result = _build_counterfactual_challenge()
        assert "CF-1" in result
        assert "CF-2" in result
        assert "CF-3" in result

    def test_contains_2026_harness_attribution(self) -> None:
        result = _build_counterfactual_challenge()
        assert "2026" in result

    def test_contains_adoption_prohibition(self) -> None:
        result = _build_counterfactual_challenge()
        assert "採用禁止" in result

    def test_with_lessons_adds_cf4(self) -> None:
        result = _build_counterfactual_challenge(lessons="cycle_n=1: some lesson")
        assert "CF-4" in result

    def test_without_lessons_no_cf4(self) -> None:
        result = _build_counterfactual_challenge(lessons="")
        assert "CF-4" not in result

    def test_with_web_research_adds_cf5(self) -> None:
        result = _build_counterfactual_challenge(web_research="some article")
        assert "CF-5" in result

    def test_without_web_research_no_cf5(self) -> None:
        result = _build_counterfactual_challenge(web_research="")
        assert "CF-5" not in result

    def test_description_includes_counterfactual_block(self) -> None:
        desc = build_evolution_description(None, web_research="w", lessons="l")
        assert "反証的自己批判" in desc

    def test_counterfactual_block_between_plan_and_do(self) -> None:
        desc = build_evolution_description(None)
        plan_pos = desc.index("A(Plan):")
        challenge_pos = desc.index("反証的自己批判")
        do_pos = desc.index("D(Do):")
        assert plan_pos < challenge_pos < do_pos


class TestBuildSkillEvalSpec:
    """_build_skill_eval_spec() - Waza式3段階grader + Ralph Loop V(erify)ゲートのテスト."""

    def test_returns_str(self) -> None:
        result = _build_skill_eval_spec()
        assert isinstance(result, str)

    def test_contains_three_grader_types(self) -> None:
        result = _build_skill_eval_spec()
        assert "GRADER-1" in result
        assert "GRADER-2" in result
        assert "GRADER-3" in result

    def test_grader1_is_deterministic_text(self) -> None:
        result = _build_skill_eval_spec()
        assert "passed" in result
        assert "weight:2.0" in result

    def test_contains_hold_out_task_directive(self) -> None:
        result = _build_skill_eval_spec()
        assert "HOLD-OUT" in result

    def test_contains_ralph_complete_condition(self) -> None:
        result = _build_skill_eval_spec()
        assert "COMPLETE" in result

    def test_contains_waza_attribution_2026(self) -> None:
        result = _build_skill_eval_spec()
        assert "2026" in result
        assert "zenn.dev" in result

    def test_with_hypothesis_included_in_output(self) -> None:
        result = _build_skill_eval_spec(hypothesis="テスト仮説テキスト")
        assert "テスト仮説テキスト" in result

    def test_without_hypothesis_no_hypothesis_line(self) -> None:
        result = _build_skill_eval_spec(hypothesis="")
        assert "対象仮説:" not in result

    def test_description_contains_verify_gate(self) -> None:
        desc = build_evolution_description(None)
        assert "V(erify)" in desc
        assert "Waza" in desc

    def test_verify_gate_between_do_and_ka(self) -> None:
        desc = build_evolution_description(None)
        do_pos = desc.index("D(Do):")
        verify_pos = desc.index("V(erify)")
        ka_pos = desc.index("kA(Log):")
        assert do_pos < verify_pos < ka_pos


class TestRunDailyEvolution:
    def test_returns_none_when_no_api_key(self, tmp_path: Path) -> None:
        from cidls.compute_use.evolution_runner import run_daily_evolution

        with patch("cidls.compute_use.evolution_runner.DB_PATH", tmp_path / "cidls.duckdb"), \
             patch("cidls.compute_use.evolution_runner.SCREENSHOT_DIR", tmp_path), \
             patch.dict("os.environ", {}, clear=False):
            # remove any ANTHROPIC_API_KEY from environment
            import os
            os.environ.pop("ANTHROPIC_API_KEY", None)
            result = run_daily_evolution(api_key=None, dry_run=True)

        assert result is None

    def test_logs_stub_when_no_key(self, tmp_path: Path) -> None:
        db_path = tmp_path / "cidls.duckdb"
        from cidls.compute_use.evolution_runner import run_daily_evolution
        import os

        with patch("cidls.compute_use.evolution_runner.DB_PATH", db_path), \
             patch("cidls.compute_use.evolution_runner.SCREENSHOT_DIR", tmp_path):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            run_daily_evolution(api_key=None, dry_run=True)

        con = duckdb.connect(str(db_path))
        rows = con.execute("SELECT * FROM evolve_log").fetchall()
        con.close()
        assert len(rows) == 1  # stub entry written
