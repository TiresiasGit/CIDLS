from pathlib import Path


COMPRESSION = """記号:⊥禁|→流|↺循|★致|∞永|⟷双|⊘反証|△複利進化|祈=自然言語願望入力|A5=A5:SQL Mk-2
MISSION:祈るだけ→注文票→CAPDkA→商用アプリ+全成果物|全日本トップITエンジニア違和感∅|AGENTS.md=SoT|⊘→△↺∞
QWEN_THINKING_MAX_PROGRAMMER:Qwen3.6ThinkingMax=Programmer|Codex=Director/Integrator|Claude=Converger|pytest/audit/devrag=Verifier|Qwen案そのまま採用⊥
AGENTIC_CONTROL_STACK:LangChain=Chain/Memory/Retrieval/Agent/Tool|LangGraph=State/Node/Edge/Checkpoint|CrewAI=Role/Goal/Task/Crew/Process|ClaudeWorld=Director/Agents/Skills/Hooks/MCP/Memory/Production
COMMERCIAL_AUTONOMOUS_EVOLUTION:企画/開発/運用/保守/販売/LP/改善/生成物欠落|40年SI温故知新|現行機能維持|低負荷運用|有用性|SEC/Compliance|反証→△
PRAY_APP_FACTORY:祈∋目的/痛み/理想/制約/参考画像/URL→P1注文票24項目→AI-DLC→TDD→Excel/HTML/PNG/exe/SaaS|不足時=最小質問|わかったふり⊥
CIDLS_PIPELINE:概念入力→ChatGPT構造化→v0相当生成→SaaS/exe→納品文書→Excel二次活用|cidls_platform_overview.html|[CIDLS_PLATFORM_RESTORE]
RAG_EVOLUTION:Adaptive RAG/Speculative RAG/GraphRAG/階層RAG|検索不足⊘|関係推論不足⊘|候補比較不足⊘|devrag連携
COMPUTE_USE:ComputeUse/Computer Use=GUI実測|見る/クリック/入力/スクリーンショット/E2E/exe/インストーラ|代替=BrowserUse/Playwright/手動証跡|DISTSEC境界★
CU_EVOLVE:GUI実測→証跡→失敗仮説→修正→再検証→kanban_project.html→kA記録|自律進化で活用|秘密/PII/課金/管理画面⊥
HARNESS:Skill/Waza/APM|ralph loop|NLAH|Sentry→原因→修正PR|可観測性|bash自動化退化⊥
A5M2_TABLE:テーブル系=A5形式|データ/カラム/インデックス/外部キー/FK(PK側)/RDBMS固有/SQLソース/Excel出力
DESTRUCTIVE_CHANGE_PREFERENCE:破壊的変更選好|互換性固執⊥|条件=品質/安全/保守/UX改善|必須=影響範囲+移行+ロールバック+TDD+水平展開
PROJECT_MD_DEPRECATION:project.md廃止|内容→kanban_project.html吸収|project_kanban.html=互換ミラー|再作成⊥
TIMEOUT_PARAMETER_DESIGN:事前設計|対象=LLM/API/HTTP/E2E/GUI/IO/DB/並列/長時間batch|timeout/retry/backoff/concurrency/batch/chunk/progress/heartbeat/cancel=調整可能|無期限待機/例外握りつぶし/任意定数=禁止
SCHEDULE:日次10:00→「CIDLSパイプラインコンセプトイメージ.pngを実現するようにパイプラインコンセプトイメージに基づき複利的自己進化させて」実行
VERIFY:TDD|pytest対象→全体|AGENTS同期|devrag再索引|kanban_project更新|残ブロッカー明示
"""


def main():
    root = Path(__file__).resolve().parents[1]
    target = root / "AGENTS直交圧縮.md"
    source = root / "AGENTS要点まとめ.md"
    source_text = source.read_text(encoding="utf-8") if source.exists() else ""
    body = (
        "# AGENTS直交圧縮\n\n"
        "AGENTS要点まとめ.mdの記号体系に従い、CIDLS復元・商用アプリ生成・"
        "Qwen制御・Agentic制御スタック・project.md廃止を直交軸へ圧縮した運用索引。\n\n"
        "## 追加圧縮\n\n"
        f"{COMPRESSION}\n"
        "## 既存要点まとめ参照\n\n"
        f"{source_text}\n"
    )
    target.write_text(body, encoding="utf-8", newline="\n")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
