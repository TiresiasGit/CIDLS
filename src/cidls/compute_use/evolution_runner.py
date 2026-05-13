"""
compute_use.evolution_runner - CIDLS daily self-evolution via ComputeUse.

Entry point for the daily 10:00 scheduled task:
  「CIDLSパイプラインコンセプトイメージ.pngをさらに
    CIDLSパイプラインコンセプトイメージ.pngの実現に向けCIDLS観点でWebからも
    関連情報収集しこれをさらに反証的複利自己進化させよ」

Pipeline:
  1. Read CIDLSパイプラインコンセプトイメージ.png (vision context).
  2. Collect web research from CIDLS-aligned search queries (urllib, no extra deps).
  3. Check current state vs concept image + web findings (⊘反証).
  4. Build evolution task description from gaps found.
  5. Run ComputeUse agentic loop (if ANTHROPIC_API_KEY set).
  6. Log results to evolve_log table (DuckDB) with web evidence URLs.
  7. Update kanban_project.html (MO-2).
"""

import base64
import json
import logging
import os
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

import duckdb

from .agent import ComputeUseAgent, ComputeUseUnavailableError, make_evolution_task
from .models import AgentResult, EvolutionTask

logger = logging.getLogger(__name__)

CONCEPT_IMAGE_PATH = Path(__file__).resolve().parents[4] / "CIDLSパイプラインコンセプトイメージ.png"
DB_PATH = Path(__file__).resolve().parents[4] / "data" / "cidls.duckdb"
SCREENSHOT_DIR = Path(__file__).resolve().parents[4] / "reports" / "compute_use"
EVOLVE_STATE_PATH = Path(__file__).resolve().parents[4] / "data" / "cidls_evolve_state.md"

DAILY_GOAL = (
    "CIDLSパイプラインコンセプトイメージ.pngをさらに"
    "CIDLS観点でCIDLSパイプラインコンセプトイメージ.pngの実現に向け"
    "Webから最新のハーネスエンジニアリングを取り込み"
    "さらに反証的複利自己進化させよ"
)

# CIDLS観点 Web検索クエリ群 (ハーネスエンジニアリング重点 + Zenn日本語記事)
_WEB_RESEARCH_QUERIES: list[str] = [
    "AI agent evaluation harness framework 2026",
    "LLM test harness agentic loop scaffolding engineering 2026",
    "Anthropic Claude agent SDK harness evaluation pipeline",
    "AI compound self-improvement harness driven development lifecycle",
    "ハーネスエンジニアリング AIエージェント 自己進化 2026 site:zenn.dev",
    "ralph loop claude code 自律コーディング ハーネス site:zenn.dev",
    "Waza APM agent skill evaluation CI pipeline 2026",
]


def _collect_web_research(
    queries: list[str] | None = None,
    timeout: int = 10,
    max_abstract_len: int = 500,
) -> str:
    """CIDLS観点でWebから関連情報を収集する (urllib stdlib, 追加依存なし).

    DuckDuckGo Instant Answer API (無料・API Key不要) を使用。
    取得できなかった場合は空文字列を返す (失敗しても進化サイクルは継続)。

    Returns:
        収集した情報スニペットを改行区切りで連結した文字列。
    """
    queries = queries if queries is not None else _WEB_RESEARCH_QUERIES
    snippets: list[str] = []

    for term in queries:
        try:
            params = urllib.parse.urlencode({
                "q": term,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1",
            })
            url = f"https://api.duckduckgo.com/?{params}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CIDLS-EvolutionRunner/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data: dict = json.loads(resp.read().decode("utf-8", errors="replace"))

            abstract = (data.get("AbstractText") or "").strip()
            source_url = (data.get("AbstractURL") or "").strip()

            if abstract:
                entry = f"[{term}]\n{abstract[:max_abstract_len]}"
                if source_url:
                    entry += f"\n出典: {source_url}"
                snippets.append(entry)
                logger.debug("[INFO] web_research OK: %s", term)
            else:
                logger.debug("[INFO] web_research no_abstract: %s", term)

        except Exception as exc:
            logger.warning("[WARN] web_research failed for '%s': %s", term, exc)

    result = "\n\n".join(snippets)
    logger.info("[INFO] web_research collected %d/%d snippets", len(snippets), len(queries))
    return result


def _read_concept_image_b64() -> str | None:
    """Load concept PNG as base64 string for vision context."""
    if not CONCEPT_IMAGE_PATH.exists():
        logger.warning("[WARN] concept image not found: %s", CONCEPT_IMAGE_PATH)
        return None
    data = CONCEPT_IMAGE_PATH.read_bytes()
    return base64.standard_b64encode(data).decode()


def _ensure_evolve_log_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS evolve_log (
            log_id               VARCHAR NOT NULL PRIMARY KEY,
            cycle_n              INTEGER NOT NULL,
            hypothesis           TEXT NOT NULL,
            evidence             TEXT NOT NULL,
            delta_desc           TEXT,
            predicted_fixes      TEXT,
            predicted_regressions TEXT,
            timestamp            TIMESTAMP NOT NULL
        )
    """)
    # Idempotent migration: add AHE Decision Observability columns if absent.
    existing = {
        row[1]
        for row in con.execute("PRAGMA table_info(evolve_log)").fetchall()
    }
    for col, typedef in (
        ("predicted_fixes", "TEXT DEFAULT ''"),
        ("predicted_regressions", "TEXT DEFAULT ''"),
    ):
        if col not in existing:
            con.execute(f"ALTER TABLE evolve_log ADD COLUMN {col} {typedef}")


def _next_cycle_n(con: duckdb.DuckDBPyConnection) -> int:
    result = con.execute("SELECT COALESCE(MAX(cycle_n), 0) + 1 FROM evolve_log").fetchone()
    return int(result[0]) if result else 1


def _log_evolution(
    con: duckdb.DuckDBPyConnection,
    cycle_n: int,
    hypothesis: str,
    evidence: str,
    delta_desc: str | None,
    predicted_fixes: str | None = None,
    predicted_regressions: str | None = None,
) -> None:
    _ensure_evolve_log_table(con)
    con.execute(
        """
        INSERT INTO evolve_log
            (log_id, cycle_n, hypothesis, evidence, delta_desc,
             predicted_fixes, predicted_regressions, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            uuid.uuid4().hex,
            cycle_n,
            hypothesis,
            evidence,
            delta_desc or "",
            predicted_fixes or "",
            predicted_regressions or "",
            datetime.now(),
        ],
    )


def _distill_lessons_from_log(
    con: duckdb.DuckDBPyConnection,
    max_entries: int = 5,
) -> str:
    """過去の evolve_log エントリから戦略的原則を蒸留して返す (EvolveR offline distillation).

    EvolveR (OpenReview 2025) の offline self-distillation + Anthropic Agent SDK の
    session-review pattern に基づく。過去サイクルの仮説・改善内容を次サイクルの
    タスク記述に注入することで複利型自己進化を実現する。

    Args:
        con: 既に evolve_log テーブルが存在する DuckDB 接続。
        max_entries: 読み込む最大エントリ数 (直近N件)。

    Returns:
        整形済みの過去知見ブロック文字列。エントリなしは空文字列。
    """
    try:
        rows = con.execute(
            """
            SELECT cycle_n, hypothesis, delta_desc
            FROM evolve_log
            ORDER BY cycle_n DESC
            LIMIT ?
            """,
            [max_entries],
        ).fetchall()
    except Exception as exc:
        logger.warning("[WARN] _distill_lessons_from_log failed: %s", exc)
        return ""

    if not rows:
        return ""

    parts: list[str] = []
    for cycle_n, hypothesis, delta_desc in rows:
        entry = f"  cycle_n={cycle_n}: 仮説={hypothesis}"
        if delta_desc:
            entry += f" / 改善={delta_desc[:300]}"
        # AHE Decision Observability: append prediction accuracy for each past cycle
        verification = _verify_prior_predictions(con, cycle_n)
        if verification:
            entry += f"\n{verification}"
        parts.append(entry)

    return "\n".join(parts)


def _verify_prior_predictions(
    con: duckdb.DuckDBPyConnection,
    target_cycle_n: int,
) -> str:
    """AHE Decision Observability: verify cycle N predictions against cycle N+1 delta_desc.

    Implements the AHE "attribute" phase (arxiv 2604.25850): each edit's prediction
    manifest is verified against observed outcomes in the following cycle. Returns a
    human-readable accuracy summary for injection into the next distillation pass.

    Args:
        con: DuckDB connection with evolve_log table.
        target_cycle_n: The cycle whose predictions we verify (N). Outcomes are
            read from cycle N+1's delta_desc.

    Returns:
        Formatted prediction-accuracy report string, empty if data unavailable.
    """
    try:
        pred_row = con.execute(
            """
            SELECT predicted_fixes, predicted_regressions
            FROM evolve_log
            WHERE cycle_n = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            [target_cycle_n],
        ).fetchone()
    except Exception as exc:
        logger.warning("[WARN] _verify_prior_predictions fetch failed: %s", exc)
        return ""

    if pred_row is None:
        return ""

    predicted_fixes_text = (pred_row[0] or "").strip()
    predicted_regressions_text = (pred_row[1] or "").strip()

    if not predicted_fixes_text and not predicted_regressions_text:
        return ""

    try:
        outcome_row = con.execute(
            """
            SELECT delta_desc
            FROM evolve_log
            WHERE cycle_n = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            [target_cycle_n + 1],
        ).fetchone()
    except Exception as exc:
        logger.warning("[WARN] _verify_prior_predictions outcome fetch failed: %s", exc)
        return ""

    outcome_text = (outcome_row[0] or "").strip() if outcome_row else ""

    lines = [f"=== Decision Observability: Cycle {target_cycle_n} 予測検証 ==="]

    if predicted_fixes_text:
        lines.append(f"  予測Fix: {predicted_fixes_text[:300]}")
    if predicted_regressions_text:
        lines.append(f"  予測Regression: {predicted_regressions_text[:300]}")

    if outcome_text:
        lines.append(f"  実績(cycle {target_cycle_n + 1}): {outcome_text[:300]}")
        lines.append("  [AHE: 予測vs実績を照合し次サイクルの仮説精度を高めよ]")
    else:
        lines.append(f"  実績(cycle {target_cycle_n + 1}): 未記録 (次サイクル実行後に検証可能)")

    return "\n".join(lines)


def _read_evolve_state(state_path: Path | None = None) -> str:
    """サイクル間継続性ファイル (cidls_evolve_state.md) を読み込む (MVH Continuity パターン).

    Minimum Viable Harness の Continuity 要素 (zenn.dev/japan/articles/a7c6d33c0a24c0)
    + opencode STATE.md パターン (zenn.dev/azumag/articles/9f7b59f2c3cfb0) の実装。

    AIの記憶に頼らず外部ファイルで継続性を保証することで、セッション跨ぎの文脈喪失を防ぐ。

    Args:
        state_path: 状態ファイルパス。None の場合は EVOLVE_STATE_PATH を使用。

    Returns:
        状態ファイルの内容文字列。存在しない場合は空文字列。
    """
    path = state_path or EVOLVE_STATE_PATH
    try:
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            logger.info("[INFO] evolve_state loaded: %s (%d chars)", path, len(content))
            return content
    except Exception as exc:
        logger.warning("[WARN] _read_evolve_state failed: %s", exc)
    return ""


def _write_evolve_state(
    cycle_n: int,
    phase: str,
    findings: str,
    next_priority: str,
    state_path: Path | None = None,
) -> None:
    """サイクル完了後に継続性ファイルを更新する (STATE.md パターン).

    opencode の STATE.md パターン: ファイルに現在フェーズ・知見・次優先項目を書き込み
    次サイクルで確実に文脈復帰できる Single Source of Truth を維持する。

    Args:
        cycle_n: 完了したサイクル番号。
        phase: 完了フェーズ (例: "kA完了", "D中断", "テスト失敗").
        findings: 今サイクルの主要知見 (次サイクルへの引き継ぎ事項)。
        next_priority: 次サイクルの優先改善項目 (Computational Guide象限チェック等)。
        state_path: 書き込み先パス。None の場合は EVOLVE_STATE_PATH を使用。
    """
    path = state_path or EVOLVE_STATE_PATH
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            f"# CIDLS EvolveR State (cycle {cycle_n})\n"
            f"更新日時: {datetime.now().isoformat()}\n\n"
            f"## フェーズ\n{phase}\n\n"
            f"## 今サイクルの主要知見\n{findings}\n\n"
            f"## 次サイクル優先項目\n{next_priority}\n\n"
            "---\n"
            "このファイルはCIDLS自己進化ループが自動管理します (MVH Continuity)。\n"
            "手動編集可能ですが、次サイクル実行時に上書きされます。\n"
        )
        path.write_text(content, encoding="utf-8")
        logger.info("[INFO] evolve_state written: cycle_n=%d phase=%s", cycle_n, phase)
    except Exception as exc:
        logger.warning("[WARN] _write_evolve_state failed: %s", exc)


def _build_computational_guide_spec() -> str:
    """Computational Guide象限の実装仕様ブロックを生成する (Birgitta Böckeler 2軸マトリクス).

    r_kaga (zenn.dev/r_kaga/articles/329afdc151899f) の2軸マトリクス分析:
    「大半の開発者は Inferential Guide (AGENTS.md / Skills) のみに集中し、
     Computational Guide (決定論的事前制約) の組み込みが欠落している」

    2軸マトリクス (Birgitta Böckeler):
      [Guide/事前]  × [Computational/決定論]  = ← CIDLS未実装
      [Guide/事前]  × [Inferential/LLM判断]  = AGENTS.md, Skills ✓
      [Sensor/事後] × [Computational/決定論]  = pytest ✓
      [Sensor/事後] × [Inferential/LLM判断]  = predicted_fixes/regressions ✓

    Returns:
        Computational Guide実装チェックリスト文字列。
    """
    lines = [
        "=== Computational Guide象限チェック (Birgitta Böckeler 2軸マトリクス, zenn.dev/r_kaga) ===",
        "根拠: 大半の開発者は Inferential Guide(AGENTS.md)のみ実装し、",
        "     Computational Guide(決定論的事前制約)が欠落している。",
        "     CIDLS現状: Inferential Guide ✓ / Computational Sensor(pytest) ✓",
        "     CIDLS欠落: Computational Guide ← 今サイクルで確認・実装すること",
        "",
        "  [CG-1] src/以下のファイルに型アノテーションが欠落していないか確認せよ。",
        "          欠落があれば mypy/pyright で検知する設定または hook が存在するか確認。",
        "",
        "  [CG-2] G1禁止パターン (SimpleFallback/dummy_data/bare except) が",
        "          コミット前に自動検出される仕組みがあるか確認せよ。",
        "          なければ pytest の test_g1_violations.py を追加することを検討せよ。",
        "",
        "  [CG-3] AGENTS.md または pyproject.toml に明示的な『やらないこと』定義があるか確認せよ。",
        "          (zenn.dev/sasadango28: 『やらないこと明記』でLLMの無駄改善を劇的削減)",
        "",
        "  [CG-4] 今サイクルの改善が CG-1〜CG-3 のいずれかを前進させるか評価せよ。",
        "          前進させない場合でも、evolve_state の next_priority に記録すること。",
        "=== Computational Guide象限チェックここまで ===",
    ]
    return "\n".join(lines)


def _build_counterfactual_challenge(
    lessons: str = "",
    web_research: str = "",
) -> str:
    """反証的自己批判ブロックを生成する (2026 Harness Engineering: Optimism Asymmetry 対策).

    2026年ハーネスエンジニアリング研究 (Harness Design for Long-Running Application
    Development, March 2026) により、エージェントは「楽観性非対称バイアス」を持つことが
    確認された。仮説を前向きに論じることは容易だが、何が仮説を偽証するかは見えにくい。

    本関数はポッパー的反証基準を A(Plan) → D(Do) 間に強制注入し、
    事前に偽証条件を宣言させることで複利精度向上を狙う。

    Args:
        lessons: 過去サイクルからの蒸留知見。一貫性チェックに使用。
        web_research: 収集したWeb情報スニペット。根拠検証に使用。

    Returns:
        反証チャレンジブロック文字列。
    """
    lines = [
        "=== 反証的自己批判 (Counterfactual Challenge - 2026 Harness Engineering) ===",
        "根拠: エージェントは楽観性バイアスを持ち仮説の前向き論証は容易だが偽証条件は見えにくい。",
        "     (出典: Harness Design for Long-Running Application Development, March 2026)",
        "D(Do)実行前に以下の問いに必ず答えよ:",
        "",
        "  [CF-1] 今回の改善仮説が間違っている場合、どのようなテスト失敗/動作異常が観測されるか?",
        "          (具体的なファイル名・テスト名・症状を列挙すること)",
        "  [CF-2] 今回の改善を実施しないケースと比較して何が変化するか?",
        "          変化が説明できない場合は改善不要の可能性を検討せよ。",
        "  [CF-3] 今回の変更で意図せず壊れる可能性がある既存機能を列挙せよ。",
        "          (predicted_regressions に記録し pytest で検証すること)",
    ]

    if lessons:
        lines += [
            "",
            "  [CF-4] 過去サイクルの知見 (上記 lessons) と今回の仮説は矛盾しないか?",
            "          矛盾する場合: 根拠を明記し旧知見を上書きする論理を示せ。",
            "          矛盾しない場合: どのように過去知見を活用しているかを示せ。",
        ]

    if web_research:
        lines += [
            "",
            "  [CF-5] 収集したWeb知見の中でこの仮説を反証する情報はあるか?",
            "          反証情報があれば仮説を修正するか採用禁止とせよ。",
        ]

    lines += [
        "",
        "反証できない仮説・CF質問に回答できない仮説は採用禁止。",
        "kAフェーズの predicted_fixes に CF-1 で宣言した偽証条件を記録すること。",
        "=== 反証的自己批判ここまで ===",
    ]

    return "\n".join(lines)


def _build_skill_eval_spec(hypothesis: str = "") -> str:
    """Waza式3段階grader評価仕様ブロックを生成する (D(Do)→kA間のV(erify)ゲート実装).

    Waza評価フレームワーク (zenn.dev/microsoft/articles/b081f3ddb93040, 2026-05-09) の
    3段階graderパターンをCIDLSの自己進化ループに注入する。

    3段階: text(確定的・安価) → behavior(ツール呼び出し数) → prompt(主観・高コスト)
    原則: 確定的graderを主軸とし、promptは人手レビュー不可の場合のみ使用。
    hold-out task: 既知テストケースへの過適応を防ぐため、未使用テストを1件以上確保。

    Ralph Loop (zenn.dev/explaza/articles/100d753df57fa7, 2026-04-04) のV(erify)ゲート:
    完了条件 <promise>COMPLETE</promise> を満たすまで TDD サイクルを反復。

    Args:
        hypothesis: 今サイクルの改善仮説 (grader重み付けの参考に使用)。

    Returns:
        評価仕様ブロック文字列。
    """
    lines = [
        "=== V(erify)ゲート: Waza式3段階grader評価仕様 (2026-05-09 zenn.dev/microsoft) ===",
        "D(Do)実施後、kA記録前に以下の評価仕様を満たすことを確認せよ:",
        "",
        "  [GRADER-1] text型 (確定的・weight:2.0) — 最優先:",
        "             pytest 全件Pass の標準出力に 'passed' が含まれること。",
        "             正規表現: r'\\d+ passed'  (失敗: exit code 1 → D(Do)へ戻る)",
        "",
        "  [GRADER-2] behavior型 (weight:1.5) — ツール効率:",
        "             今回の変更で新規追加した関数が1つ以上あること。",
        "             過剰なファイル変更 (>5ファイル) は diff-isolation 原則違反として要確認。",
        "",
        "  [GRADER-3] prompt型 (weight:1.0) — 最終手段のみ使用:",
        "             evolve_log.delta_desc が 50文字以上かつ 2000文字以内であること。",
        "             Web根拠URLが evidence フィールドに1件以上含まれること。",
        "",
        "  [HOLD-OUT] 過適応防止:",
        "             今回追加するテストのうち少なくとも1件は、",
        "             既存テストケースに存在しないエッジケースをカバーすること。",
        "",
        "  [RALPH-COMPLETE] 完了条件:",
        "             全GRADER通過かつ pytest Pass → <promise>COMPLETE</promise>",
        "             未通過の場合 → D(Do)フェーズの修正タスクとして再実行すること。",
        "=== V(erify)ゲートここまで ===",
    ]

    if hypothesis:
        lines.insert(2, f"  対象仮説: {hypothesis[:150]}")
        lines.insert(3, "")

    return "\n".join(lines)


def build_evolution_description(
    concept_b64: str | None,
    web_research: str = "",
    lessons: str = "",
    state_context: str = "",
) -> str:
    """Build the task description fed to the ComputeUse agent.

    Args:
        concept_b64: Base64-encoded concept PNG (vision context), or None.
        web_research: Pre-collected web snippets (CIDLS観点).
        lessons: Distilled lessons from past evolve_log entries.
        state_context: Inter-cycle state from cidls_evolve_state.md (MVH Continuity).
    """
    counterfactual_block = _build_counterfactual_challenge(
        lessons=lessons,
        web_research=web_research,
    )
    computational_guide_block = _build_computational_guide_spec()

    lines = [
        "CIDLS反証的複利自己進化タスク",
        "",
        "ゴール:",
        DAILY_GOAL,
        "",
        "手順 (CAPDkA):",
        "C(Check): CIDLSパイプラインコンセプトイメージ.pngを参照し、現在の実装との差分を確認する。",
        "C(Web):   CIDLS観点でWebから最新ハーネスエンジニアリング手法を収集しコンセプトイメージと照合、⊘反証箇所を特定する。",
        "A(Plan):  差分・反証・ハーネス知見から最優先改善項目を1-3つ選定し仮説+Web根拠URL+最小実装単位を明記する。",
        "",
        counterfactual_block,
        "",
        "D(Do):    最小差分(DIFF)で改善を実施し、pytest 全件Passを確認する。",
        "",
        _build_skill_eval_spec(),
        "",
        computational_guide_block,
        "",
        "kA(Log):  evolve_log にサイクル記録(仮説/Web根拠URL/変更ファイル/改善要約)を挿入する。",
        "kA(State): _write_evolve_state() で cidls_evolve_state.md を更新する。",
        "",
        "=== AHE Decision Observability (arxiv:2604.25850) ===",
        "kA実行時に _log_evolution() の以下パラメータを必ず設定せよ:",
        "  predicted_fixes:      今回の改善で修正されると予測するテスト/機能 (箇条書き)",
        "  predicted_regressions: 今回の変更で壊れるリスクがある箇所 (箇条書き、なければ空文字)",
        "根拠: 予測を事前宣言→次サイクルで検証→予測精度を複利蓄積 (AHE fix-precision 33.7%基準超えを目標)。",
        "=== Decision Observability ここまで ===",
        "",
        "完了条件:",
        "- pytest 全件Pass",
        "- evolve_log に新エントリ1件以上 (Web収集URLが evidence に含まれること)",
        "- evolve_log.predicted_fixes に今サイクルの予測を記録済み",
        "- kanban_project.html 更新済",
        "- AGENTS直交圧縮.md と矛盾なし",
        "",
        "CU_GUARD: 秘密情報入力禁止 / 破壊的操作は人間確認後 / 証跡PNG必須",
    ]

    if lessons:
        lines += [
            "",
            "=== 過去サイクルからの知見 (EvolveR複利蓄積 - 次サイクルの指針として活用せよ) ===",
            lessons,
            "=== 過去知見ここまで ===",
        ]

    if web_research:
        lines += [
            "",
            "=== CIDLS観点 Web収集情報 / 最新ハーネスエンジニアリング知見 (反証・進化の根拠として活用せよ) ===",
            web_research,
            "=== Web収集情報ここまで ===",
        ]

    if concept_b64:
        lines += ["", "[concept_image attached as vision context]"]

    return "\n".join(lines)


def run_daily_evolution(
    api_key: str | None = None,
    dry_run: bool = False,
    max_iterations: int = 30,
) -> AgentResult | None:
    """
    Execute the daily CIDLS self-evolution loop.

    Returns AgentResult if ComputeUse was available, else None.
    """
    logger.info("[PROCESS_START] daily_evolution date=%s dry_run=%s",
                datetime.now().date(), dry_run)

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    concept_b64 = _read_concept_image_b64()

    # CIDLS観点 Web情報収集 (⊘反証根拠として description に注入)
    web_research = _collect_web_research()

    # --- open DuckDB before building description to enable EvolveR distillation ---
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    _ensure_evolve_log_table(con)
    cycle_n = _next_cycle_n(con)

    # EvolveR offline distillation: inject past lessons into this cycle's description
    lessons = _distill_lessons_from_log(con)
    description = build_evolution_description(concept_b64, web_research=web_research, lessons=lessons)

    task = make_evolution_task(
        description=description,
        goal=DAILY_GOAL,
        max_iterations=max_iterations,
        screenshot_dir=SCREENSHOT_DIR,
    )

    result: AgentResult | None = None

    if not api_key:
        logger.warning("[WARN] ANTHROPIC_API_KEY not set - recording stub evolution entry")
        _log_evolution(
            con, cycle_n,
            hypothesis="ANTHROPIC_API_KEY未設定のため実行スキップ",
            evidence="key_missing",
            delta_desc=None,
        )
        con.close()
        return None

    try:
        agent = ComputeUseAgent(
            api_key=api_key,
            screenshot_dir=SCREENSHOT_DIR,
            dry_run=dry_run,
        )
        result = agent.run(task)

        # evidence: スクリーンショットパス + 収集WebURLを記録
        web_urls = [
            line.replace("出典: ", "")
            for line in web_research.splitlines()
            if line.startswith("出典: ")
        ]
        evidence_combined = str(result.evidence_paths + web_urls)
        _log_evolution(
            con, cycle_n,
            hypothesis=DAILY_GOAL,
            evidence=evidence_combined,
            delta_desc=result.summary[:2000] if result.summary else None,
        )
        logger.info("[SUCC] daily_evolution cycle_n=%d success=%s", cycle_n, result.success)

    except ComputeUseUnavailableError as exc:
        logger.warning("[WARN] ComputeUse unavailable: %s", exc)
        _log_evolution(
            con, cycle_n,
            hypothesis="anthropicパッケージ未インストールのためスキップ",
            evidence=str(exc),
            delta_desc=None,
        )
    except Exception as exc:
        logger.error("[ERR] daily_evolution failed: %s", exc, exc_info=True)
        _log_evolution(
            con, cycle_n,
            hypothesis=DAILY_GOAL,
            evidence=f"ERROR: {exc}",
            delta_desc=None,
        )
        raise
    finally:
        con.close()

    logger.info("[PROCESS_END] daily_evolution")
    return result
