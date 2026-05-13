import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from cidls.commercial_delivery.generator import render_story_html

from .models import ConceptPipelineSpec, Deliverable, PipelineStage


DEFAULT_CONCEPT_TITLE = "新規業務システム構築プロジェクト"


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_default_spec(concept_title=DEFAULT_CONCEPT_TITLE):
    stages = (
        PipelineStage(
            order=1,
            key="human_idea",
            title="人のアイデア整理",
            actor="利用者",
            responsibility="初期アイデア、業務上の困りごと、As-Is、To-Beを注文票へ整理する。",
            inputs=("実現したいソリューション", "業務上の困りごと", "理想状態"),
            outputs=("注文票", "As-Is / To-Be", "完了判定"),
            quality_gate="抽象語だけで終えず、対象者、数値、制約、完了判定を1文で説明できる。",
        ),
        PipelineStage(
            order=2,
            key="concept_image_generation",
            title="概念画像から仕様へ変換",
            actor="ChatGPT / 画像生成LLM",
            responsibility="構想画像や手書き案を、業務・画面・成果物の関係が分かる構造へ変換する。",
            inputs=("初期アイデア", "参考画像", "CIDLS注文票"),
            outputs=("コンセプト画像", "画面構成案", "成果物仮説"),
            quality_gate="見た目だけで終わらず、後続の設計成果物へ分解できる。",
        ),
        PipelineStage(
            order=3,
            key="agents_standard_outputs",
            title="AGENTS標準成果物生成",
            actor="Codex",
            responsibility="AGENTS.mdのCAPDkA、品質ゲート、水平展開原則に従い、標準成果物へ分解する。",
            inputs=("コンセプト画像", "AGENTS.md", "project_kanban.html"),
            outputs=("アプリ設計", "DA表", "PJグラフ", "画面設計", "納品文書"),
            quality_gate="目的、根本原因、実行順序、リスク、完了条件が成果物ごとに明示されている。",
        ),
        PipelineStage(
            order=4,
            key="codex_builder",
            title="Codexビルダー",
            actor="Codexローカル実装",
            responsibility="外部Webビルダーの代替として、アプリ本体と文書をローカルで生成し、テストで検証する。",
            inputs=("標準成果物", "既存コード", "テスト"),
            outputs=("アプリケーション本体", "設計文書", "検証レポート"),
            quality_gate="勝手なデプロイを行わず、生成物をローカルファイルとテスト結果として残す。",
        ),
        PipelineStage(
            order=5,
            key="delivery_package",
            title="納品パッケージ化",
            actor="CIDLS",
            responsibility="要求、設計、DB、テスト、運用、検収を商用請負レベルの成果物へ束ねる。",
            inputs=("Codex生成物", "QA結果", "運用条件"),
            outputs=("納品パッケージ", "受入確認表", "運用保守手順"),
            quality_gate="要求からテストまで追跡でき、発注者が検収できる粒度になっている。",
        ),
    )
    deliverables = (
        Deliverable(
            key="app_blueprint",
            title="アプリケーション本体設計",
            filename="app_blueprint.html",
            purpose="実装対象の画面、データ、処理、品質ゲートを1画面で確認する。",
            acceptance_criteria=("主要導線が3クリック以内", "状態と成果物の関係が画面上で追える"),
        ),
        Deliverable(
            key="system_da_table",
            title="システムDA表",
            filename="system_da_table.html",
            purpose="データ名、説明、主要項目、関連テーブルを整理する設計表。",
            acceptance_criteria=("主要エンティティを網羅", "画面、タスク、レポートとの関係を明示"),
        ),
        Deliverable(
            key="project_graph_mindmap",
            title="PJグラフマインドマップ",
            filename="graph_project_mindmap.html",
            purpose="注文票、カンバン、レポート、設計成果物の因果関係を可視化する。",
            acceptance_criteria=("注文票とタスクが接続されている", "孤立した成果物ノードがない"),
        ),
        Deliverable(
            key="screen_overview",
            title="全画面設計図",
            filename="screen_overview.svg",
            purpose="主要画面の一覧と画面間のまとまりを静的図として残す。",
            acceptance_criteria=("ダッシュボード、注文票、カンバン、レポートを含む", "横長レイアウトで読める"),
        ),
        Deliverable(
            key="screen_state_design",
            title="画面状態遷移図および画面設計書",
            filename="screen_state_design.html",
            purpose="状態遷移、画面責務、入力、出力、検証観点を対応づける。",
            acceptance_criteria=("各状態の遷移条件を明示", "各画面の主な責務を明記"),
        ),
        Deliverable(
            key="concept_slide",
            title="コンセプトスライド",
            filename="concept_slide.html",
            purpose="業務価値、画面像、カンバン、レポートを説明可能なスライドにする。",
            acceptance_criteria=("非技術者に目的が伝わる", "As-Is / To-Be / 解決策が同一資料内にある"),
        ),
        Deliverable(
            key="subscription_story",
            title="STORY.html",
            filename="STORY.html",
            purpose="Stripe subscriptionの契約、決済、Webhook、キャンセル、入金、検収を1画面で追う業務ストーリー。",
            acceptance_criteria=("6登場人物を含む", "Secretはサーバー専用と明記", "Webhookと入金照合の責務を分離"),
        ),
        Deliverable(
            key="delivery_docs_pack",
            title="商用請負納品ドキュメント一式",
            filename="delivery_docs/",
            purpose="要求、基本設計、詳細設計、テスト、運用、受入確認を文書化する。",
            acceptance_criteria=("要求からテストまで追跡できる", "運用保守手順が独立して読める"),
        ),
    )
    return ConceptPipelineSpec(
        concept_title=concept_title,
        source_image_summary=(
            "人のアイデアを起点に、概念画像、AGENTS標準成果物、Codexローカル実装、"
            "商用請負納品文書へ順番に変換する一気通貫フロー。"
        ),
        stages=stages,
        deliverables=deliverables,
        delivery_documents=(
            "requirements_definition.md",
            "basic_design.md",
            "detailed_design.md",
            "test_specification.md",
            "operations_runbook.md",
            "acceptance_checklist.md",
        ),
    )


def materialize_pipeline(output_dir, concept_title=DEFAULT_CONCEPT_TITLE):
    output_path = Path(output_dir).resolve()
    spec = build_default_spec(concept_title=concept_title)
    output_path.mkdir(parents=True, exist_ok=True)

    generated_files = []
    planned_files = [
        ("cidls_pipeline_spec.md", render_spec_markdown(spec)),
        ("app_blueprint.html", render_app_blueprint(spec)),
        ("system_da_table.html", render_system_da_table(spec)),
        ("graph_project_mindmap.html", render_graph_mindmap(spec)),
        ("screen_overview.svg", render_screen_overview_svg(spec)),
        ("screen_state_design.html", render_screen_state_design(spec)),
        ("concept_slide.html", render_concept_slide(spec)),
        ("STORY.html", render_subscription_story(spec)),
    ]
    for filename, content in planned_files:
        path = output_path / filename
        action = write_text_if_changed(path, content)
        generated_files.append(file_record(path, action))

    docs_dir = output_path / "delivery_docs"
    for filename in spec.delivery_documents:
        path = docs_dir / filename
        content = render_delivery_document(spec, filename)
        action = write_text_if_changed(path, content)
        generated_files.append(file_record(path, action))

    report = {
        "ok": True,
        "generated_at_utc": utc_now_iso(),
        "concept_title": spec.concept_title,
        "source_image_summary": spec.source_image_summary,
        "deployment_performed": False,
        "output_dir": str(output_path),
        "stage_count": len(spec.stages),
        "deliverable_count": len(spec.deliverables),
        "files": generated_files,
    }
    report_path = output_path / "cidls_pipeline_report.json"
    write_text_if_changed(
        report_path,
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    )
    report["report_path"] = str(report_path)
    return report


def file_record(path, action):
    return {"path": str(path), "action": action}


def write_text_if_changed(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    if path.exists() and path.read_text(encoding="utf-8") == normalized:
        return "unchanged"
    existed = path.exists()
    path.write_text(normalized, encoding="utf-8", newline="\n")
    return "updated" if existed else "created"


def html_document(title, body):
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
:root {{
  --ink: #172326;
  --muted: #586669;
  --line: rgba(23, 35, 38, 0.14);
  --paper: rgba(255, 251, 245, 0.92);
  --accent: #c45c2d;
  --deep: #173f4a;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  color: var(--ink);
  font-family: "BIZ UDPGothic", "Yu Gothic UI", "Meiryo", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(196, 92, 45, 0.16), transparent 24%),
    linear-gradient(180deg, #f7f1e6 0%, #efe4d1 100%);
}}
main {{ width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 32px 0; }}
.hero, .card, .screen {{ background: var(--paper); border: 1px solid var(--line); border-radius: 24px; box-shadow: 0 18px 42px rgba(68,48,25,0.12); }}
.hero {{ padding: 28px; margin-bottom: 18px; }}
.tag {{ display: inline-block; padding: 8px 12px; border-radius: 999px; background: rgba(196,92,45,0.14); color: var(--accent); font-weight: 700; }}
.grid {{ display: grid; gap: 16px; }}
.grid.two {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
.grid.three {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
.card, .screen {{ padding: 18px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ border-bottom: 1px solid var(--line); padding: 10px; text-align: left; line-height: 1.6; }}
th {{ color: var(--deep); background: rgba(23,63,74,0.08); }}
.node {{ display: inline-block; margin: 4px; padding: 10px 12px; border-radius: 14px; background: rgba(196,92,45,0.14); }}
@media (max-width: 900px) {{ .grid.two, .grid.three {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body><main>{body}</main></body>
</html>
"""


def render_spec_markdown(spec):
    stage_lines = []
    for stage in spec.stages:
        stage_lines.append(
            "\n".join(
                [
                    f"### {stage.order}. {stage.title}",
                    f"- 担当: {stage.actor}",
                    f"- 責務: {stage.responsibility}",
                    f"- 入力: {', '.join(stage.inputs)}",
                    f"- 出力: {', '.join(stage.outputs)}",
                    f"- 品質ゲート: {stage.quality_gate}",
                ]
            )
        )
    deliverable_lines = []
    for item in spec.deliverables:
        deliverable_lines.append(
            "\n".join(
                [
                    f"### {item.title}",
                    f"- ファイル: `{item.filename}`",
                    f"- 目的: {item.purpose}",
                    f"- 合格条件: {', '.join(item.acceptance_criteria)}",
                ]
            )
        )
    return "\n\n".join(
        [
            "# CIDLSコンセプトパイプライン仕様",
            f"対象: {spec.concept_title}",
            "",
            "## 画像内容の日本語変換",
            spec.source_image_summary,
            "",
            "## 実行段階",
            "\n\n".join(stage_lines),
            "",
            "## 生成成果物",
            "\n\n".join(deliverable_lines),
            "",
            "## 運用制約",
            "- Codexは外部Webビルダーの代替としてローカル生成だけを行う。",
            "- 勝手なデプロイ、外部公開、スケジューラ追加は行わない。",
            "- 生成物はAGENTS.md、project_kanban.html、テスト結果と水平同期する。",
            "",
        ]
    )


def render_app_blueprint(spec):
    cards = "\n".join(
        f'<article class="card"><span class="tag">{escape(item.title)}</span><p>{escape(item.purpose)}</p></article>'
        for item in spec.deliverables
    )
    return html_document(
        f"{spec.concept_title} アプリ本体設計",
        f"""
<section class="hero">
  <span class="tag">Codexローカル生成</span>
  <h1>{escape(spec.concept_title)} アプリ本体設計</h1>
  <p>{escape(spec.source_image_summary)}</p>
</section>
<section class="grid three">
  <article class="screen"><h2>ダッシュボード</h2><p>案件、タスク、レポート、品質ゲートを1画面に集約する。</p></article>
  <article class="screen"><h2>カンバン</h2><p>Backlog / Todo / InProgress / Review / Done を追跡する。</p></article>
  <article class="screen"><h2>成果物</h2><p>設計表、マインドマップ、画面設計、スライド、納品文書を束ねる。</p></article>
</section>
<section class="grid two" style="margin-top:16px">{cards}</section>
""",
    )


def render_system_da_table(spec):
    rows = "".join(
        f"<tr><td>{escape(item.key)}</td><td>{escape(item.title)}</td><td>{escape(item.purpose)}</td><td>{escape(item.filename)}</td></tr>"
        for item in spec.deliverables
    )
    return html_document(
        "システムDA表",
        f"""
<section class="hero"><span class="tag">Data Architecture</span><h1>システムDA表</h1><p>成果物、データ、画面、検証証跡を対応づける。</p></section>
<section class="card"><table><thead><tr><th>キー</th><th>名称</th><th>説明</th><th>ファイル</th></tr></thead><tbody>{rows}</tbody></table></section>
""",
    )


def render_graph_mindmap(spec):
    nodes = "".join(
        f'<div class="node">{escape(stage.title)}</div>' for stage in spec.stages
    )
    return html_document(
        "PJグラフマインドマップ",
        f"""
<section class="hero"><span class="tag">GraphRAG</span><h1>PJグラフマインドマップ</h1><p>注文票から納品までの因果関係を可視化する。</p></section>
<section class="card">{nodes}</section>
""",
    )


def render_screen_overview_svg(spec):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
<rect width="1280" height="720" fill="#f7f1e6"/>
<text x="60" y="70" font-family="Meiryo" font-size="34" fill="#173f4a">{escape(spec.concept_title)} 全画面設計図</text>
<g font-family="Meiryo" font-size="22" fill="#172326">
<rect x="70" y="130" width="260" height="160" rx="22" fill="#fff8ef" stroke="#c45c2d"/><text x="105" y="215">ダッシュボード</text>
<rect x="370" y="130" width="260" height="160" rx="22" fill="#fff8ef" stroke="#c45c2d"/><text x="440" y="215">注文票</text>
<rect x="670" y="130" width="260" height="160" rx="22" fill="#fff8ef" stroke="#c45c2d"/><text x="745" y="215">カンバン</text>
<rect x="970" y="130" width="240" height="160" rx="22" fill="#fff8ef" stroke="#c45c2d"/><text x="1030" y="215">成果物</text>
<rect x="220" y="410" width="340" height="160" rx="22" fill="#ffffff" stroke="#173f4a"/><text x="285" y="500">QA / テスト証跡</text>
<rect x="710" y="410" width="340" height="160" rx="22" fill="#ffffff" stroke="#173f4a"/><text x="770" y="500">運用保守 / 検収</text>
</g>
</svg>
"""


def render_screen_state_design(spec):
    rows = "".join(
        f"<tr><td>{stage.order}</td><td>{escape(stage.title)}</td><td>{escape(stage.responsibility)}</td><td>{escape(stage.quality_gate)}</td></tr>"
        for stage in spec.stages
    )
    return html_document(
        "画面状態遷移図および画面設計書",
        f"""
<section class="hero"><span class="tag">Screen State</span><h1>画面状態遷移図および画面設計書</h1><p>状態ごとの入力、出力、検証観点を整理する。</p></section>
<section class="card"><table><thead><tr><th>#</th><th>状態</th><th>責務</th><th>品質ゲート</th></tr></thead><tbody>{rows}</tbody></table></section>
""",
    )


def render_concept_slide(spec):
    return html_document(
        "コンセプトスライド",
        f"""
<section class="hero"><span class="tag">Concept</span><h1>{escape(spec.concept_title)}</h1><p>{escape(spec.source_image_summary)}</p></section>
<section class="grid three">
  <article class="card"><h2>As-Is</h2><p>アイデア、文書、実装、検証が分断されやすい。</p></article>
  <article class="card"><h2>To-Be</h2><p>注文票から納品まで、成果物と証跡が水平展開される。</p></article>
  <article class="card"><h2>解決策</h2><p>Codexローカル生成、project_kanban、商用請負Excel成果物で統合する。</p></article>
</section>
""",
    )


def render_subscription_story(spec):
    return render_story_html(spec.concept_title)


def render_delivery_document(spec, filename):
    titles = {
        "requirements_definition.md": "要求要件定義書",
        "basic_design.md": "基本設計書",
        "detailed_design.md": "詳細設計書",
        "test_specification.md": "テスト仕様書",
        "operations_runbook.md": "運用保守手順書",
        "acceptance_checklist.md": "受入確認表",
    }
    title = titles[filename]
    deliverable_lines = "\n".join(
        f"- {item.title}: `{item.filename}`" for item in spec.deliverables
    )
    return f"""# {title}

対象: {spec.concept_title}

## 位置づけ
この文書は、CIDLSコンセプトパイプラインを日本語仕様とローカル生成物へ変換した成果物である。

## 共通方針
- 人のアイデアを起点に、概念画像、標準成果物、Codexローカル実装、納品出力へ順番に変換する。
- Codexは外部Webビルダーの代替として、ローカルファイル生成と検証だけを行う。
- 勝手なデプロイ、外部公開、追加スケジューラ登録は行わない。

## 対応成果物
{deliverable_lines}

## 合格条件
- 要求、設計、テスト、運用の対応が切れない。
- `cidls_pipeline_report.json` に生成結果が残る。
- 生成ファイルがローカルで再実行可能である。
"""
