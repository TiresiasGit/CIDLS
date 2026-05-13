# CIDLS Agentic Autonomy Commercial Assessment

## 目的

CIDLSを、企画・開発・運用・保守・販売・LP・改善・生成物欠落までを反証しながら自律進化する商用アプリ製造ラインとして扱う。

## 外部知見の統合

| 知見 | CIDLSへの取り込み | 反証観点 |
|---|---|---|
| Qwen3.6ThinkingMax | Programmerとして実装候補・テスト案・影響範囲を出させる | Codex検証なし採用、架空API、Secret露出 |
| LangChain | Chain、Memory、Retrieval、Agent、Toolを注文票・記憶・devrag・外部ツールへ割当 | 単なるプロンプト列、検索固定化 |
| LangGraph | State、Node、Edge、CheckpointをCAPDkA状態遷移へ割当 | 状態欠落、失敗時継続、再開不能 |
| CrewAI | Role、Goal、Task、Crew、Processを多役割分掌へ割当 | 役割衝突、責任境界曖昧 |
| Claude World | Director Mode、Agents、Skills、Hooks、MCP、Memory、Production Readinessを運用統制へ割当 | Director不在、Hooks形骸化 |
| Zenn選定20本 | Skill評価、APM、ralph loop、可観測性、Sentry修正PR、GraphRAG、階層RAG、Skillセキュリティスキャンへ分類 | bash自動化退化、品質評価欠落 |

## CIDLS商用アセスメント

| 領域 | 現状リスク | 将来リスク | 段階的改善 | 今すぐの具体アクション |
|---|---|---|---|---|
| 企画 | 誰の痛みか曖昧なまま生成が進む | LPと機能が乖離し販売不能 | 注文票で対象者・痛み・証拠・価格仮説を固定 | 企画カードをkanban_project.htmlへ集約 |
| 開発 | 実装Agentが責任境界を越える | 保守不能な自律生成コードが増える | QwenをProgrammerに限定しCodexが統合 | QWEN_THINKING_MAX_PROGRAMMERをAGENTSへ追加 |
| 運用 | 監視・ログ・修正PR導線が薄い | 障害時に自己修復できない | 可観測性、Sentry相当、修正PRハーネスを追加 | COMMERCIAL_AUTONOMOUS_EVOLUTIONをAGENTSへ追加 |
| 保守 | knowledgeが分散する | 同じ調査と修正を反復する | project.mdを廃止しkanban_project.htmlへ集約 | project.mdを削除しHTMLへ全内容移行 |
| 販売/LP | 成果物価値が伝わりにくい | 課金意思・継続率を検証できない | LP、価格、解約、導入証跡を成果物化 | パイプラインHTMLに商用自律進化セクション追加 |
| セキュリティ | Agent/SkillにSecretや危険操作が混入する | 公開配布時に漏洩・権限事故が起きる | DISTSEC、Skillスキャン、秘密境界をGate化 | テストで禁止再発を検査 |

## 完了条件

- AGENTS.mdにQwen制御、Agentic制御スタック、商用自律進化、project.md廃止がある。
- project.mdが存在しない。
- kanban_project.htmlとproject_kanban.htmlに旧project.md内容のアーカイブがある。
- cidls_platform_overview.htmlとgraph_project_mindmap.htmlにQwen、LangChain、LangGraph、CrewAI、Claude World、商用自律進化がある。
- pytestで上記を検査する。
