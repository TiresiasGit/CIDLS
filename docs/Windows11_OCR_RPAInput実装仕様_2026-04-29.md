# Windows11 OCR RPAInput 実装仕様 2026-04-29

## 0. 多重人格会議

| 役割 | 判断 |
|---|---|
| Architect | `pyautogui -> Snipping Tool -> OCR -> RPAInput` は `capture_orchestrator` を中心に、GUI操作、解析、変換、証跡、CIDLS保守ループを分離する。 |
| Analyzer | 根本制約は Snipping Tool OCR の公式Python APIを前提にできない点であり、GUI検出、待機、再試行、PowerToys代替経路で吸収する。 |
| Security | OCR結果に個人情報が含まれるため、`secure_mode` でメール、電話、郵便番号を証跡上マスクする。 |
| Performance | OCRはI/O待機が支配的なため、待機間隔、タイムアウト、画像保存回数を制御し、証跡は冪等キー配下へ上書きする。 |
| QA | 純粋関数、アダプタ、Web画面、GUI準E2E、グローバル配線監査、kanban更新を分けてTDDする。 |
| Backend | CLIは `cidls-ocr-pipeline` と `cidls-codex-maintenance` に分け、Python内部でスケジューラ登録をしない。 |
| Refactorer | 既存 `src/cidls/ocr_pipeline` と `src/cidls/codex_global_loop` をSoT実装とし、重複実装を作らない。 |

目的は、Windows 11画面または指定画像からOCR文字列を取得し、RPAInputが読める `cidls.rpainput.v1` 構造へ変換することである。完了条件は、Web代表ケース、実Windows画面1ケース、代替OCR経路、原因追跡ログ、CIDLS CLI呼出、冪等再実行、保守ループ、グローバル配線監査、kanban更新、devrag探索証跡がそろうことである。

## 1. 要求構造化

| 項目 | 内容 |
|---|---|
| ターゲット | Windows 11 OCR/RPAInputパイプラインとCIDLSグローバル保守ループ。 |
| As-Is | Snipping Tool OCRはGUI機能として存在するが、Python公式APIとして固定できない。CIDLS配線は `%CODEX_HOME%`、hooks、mcp、skills、AGENTS、kanbanに分散する。 |
| To-Be | `src/cidls/ocr_pipeline` から画面OCRを実行し、`reports/ocr_pipeline/<idempotency_key>` に証跡を残し、RPAInput JSON/CSV/DTOを得る。 |
| なぜ必要か | RPAInput投入前に画面情報を構造化し、手作業の転記・検証漏れを減らすため。 |
| 完了条件 | OCR代表ケース変換、GUI準E2E実行手順、PowerToys代替、保守ループ監査、kanban更新、devrag探索が動作する。 |
| 非機能要件 | 冪等出力、タイムアウト、リトライ、失敗スクリーンショット、PIIマスク、Windows DPI差対策、SoT差分検知。 |
| 失敗条件 | OCR空文字、クリップボード未更新、Snipping Toolボタン検出失敗、グローバル配線差分、kanban書込失敗。 |
| 範囲内 | Python実装、CLI、Web検証画面、pytest、global hook/sync/audit/devrag/kanban補助。 |
| 範囲外 | Python内部からのWindowsスケジューラ登録、自己増殖タスク生成、Snipping Tool非公開API呼出。 |

## 2. 原因追跡

Snipping Tool OCRを直接Pythonから呼びにくい原因は、OCRのText actionsがWindowsアプリの画面操作として公開され、安定したPython API境界がないためである。壊れやすい層は、Snipping Tool起動、通知・ウィンドウ遷移、Text actionsボタン、Copy all textボタン、クリップボード更新、DPIスケーリングである。吸収層は `snipping_tool_adapter` と `gui_common` であり、座標固定ではなくウィンドウタイトル、テンプレート画像、フォーカス待機、タイムアウト、リトライで扱う。

画面TDDで保証するものは、Webターゲットが固定文字列を描画し、取得テキストがParser/Converterを通ることである。モック対象はSnipping Toolボタン検出、クリップボード、pyautogui、pygetwindowである。実画面でのみ保証するものは、Win+Shift+S、Snipping Toolの実ボタン配置、Windows OCR品質である。

グローバルCodex配線でズレやすい箇所は `%CODEX_HOME%\AGENTS.md`、`hooks\run-cidls-hook.cmd`、`mcp\cidls_global\runtime-devrag-config.json`、`mcp\cidls_global\build-runtime-config.py`、`skills\cidls-*` である。`project_kanban.html` をSoTにした同期失敗点は、チケット配列の構造変更、AGENTS同期ブロックの更新漏れ、`project.md` / `TODO.md` / docs / QA / scenario の水平展開漏れである。

## 3. アーキテクチャ設計

| 責務 | 実装 |
|---|---|
| capture_orchestrator | `src/cidls/ocr_pipeline/capture_orchestrator.py`: 画面領域決定、adapter順序制御、再試行、証跡保存、Parser/Converter連結。 |
| snipping_tool_adapter | `src/cidls/ocr_pipeline/adapters/snipping_tool_adapter.py`: Win+Shift+S、領域ドラッグ、Snipping Toolウィンドウ待機、Text actions検出、Copy all text検出、クリップボード取得。 |
| ocr_result_parser | `src/cidls/ocr_pipeline/ocr_result_parser.py`: NFKC正規化、改行正規化、キー値抽出、表行抽出、警告付与。 |
| rpainput_converter | `src/cidls/ocr_pipeline/rpainput_converter.py`: `cidls.rpainput.v1` payload、行、キー値、OCRブロック、JSON/CSV/DTO向け構造生成。 |
| fallback_ocr_adapter | `src/cidls/ocr_pipeline/adapters/fallback_ocr_adapter.py`: PowerToys Text Extractor hotkey、領域ドラッグ、クリップボード取得。 |
| evidence_logger | `src/cidls/ocr_pipeline/evidence_logger.py`: manifest、raw text、structured JSON/CSV、failure screenshot、retry/error履歴、PIIマスク。 |
| web_test_target | `fixtures/web/ocr_test_target.html`, `src/cidls/ocr_pipeline/web_test_target.py`: フォーム、表、カード、ラベル群を固定表示するWeb検証画面。 |
| cidls_sync_orchestrator | `src/cidls/codex_global_loop/maintenance.py`: `pre_prompt_cycle.bat`、条件付き `installer.bat`、`sync_agents_cidls_policy.py`、kanban更新。 |
| codex_global_wiring_auditor | `src/cidls/codex_global_loop/wiring_audit.py`, `scripts/audit_global_cidls_wiring.py`: global AGENTS/hooks/mcp/skills監査。 |
| devrag_bridge | `src/cidls/codex_global_loop/devrag_bridge.py`: CIDLS devrag CLI探索をJSON証跡化。 |

## 4. ディレクトリ構成

```text
src/cidls/ocr_pipeline/
src/cidls/ocr_pipeline/adapters/
src/cidls/codex_global_loop/
fixtures/web/
fixtures/templates/snipping_tool/
tests/ocr_pipeline/unit/
tests/ocr_pipeline/integration/
tests/ocr_pipeline/e2e/
tests/codex_global_loop/
docs/
reports/ocr_pipeline/
logs/
```

## 5. インターフェース設計

| 抽象 | 責務 / 失敗仕様 |
|---|---|
| `OCRAdapter` | `supports(request)` と `extract(request, evidence_run)` を実装する。操作不能時は `AdapterActionError`。 |
| `CaptureRequest` | `source_mode`, `region`, `image_path`, `output_format`, `language_hint`, `idempotency_key`, adapter名、secure設定、retry/timeoutを保持する。不正値は `ConversionError`。 |
| `OCRRawResult` | adapter名、生OCR、capture画像、clipboard文字列、座標ブロック、metadataを保持する。 |
| `StructuredInput` | RPAInput payloadを保持し `to_dict()` で返す。 |
| `ConversionReport` | 構造化結果、正規化テキスト、キー値、行、警告、metadataを返す。 |
| `GlobalWiringAuditResult` | global wiring監査payloadを保持し、issuesが空ならOK。 |
| `KanbanTicketUpdate` | `CIDLS-*` チケットのtitle/status/priority/evidence/traceを保持する。 |
| `DevragSearchResult` | query、command、returncode、results、stdout/stderrを保存する。 |
| `HookExecutionResult` | hook/installer実行結果、returncode、stdout/stderr、installer実行有無を保存する。 |

## 6. 実装コード

完全コードは以下のファイルをSoTとする。

- `src/cidls/ocr_pipeline/cli.py`
- `src/cidls/ocr_pipeline/capture_orchestrator.py`
- `src/cidls/ocr_pipeline/adapters/snipping_tool_adapter.py`
- `src/cidls/ocr_pipeline/adapters/fallback_ocr_adapter.py`
- `src/cidls/ocr_pipeline/adapters/winocr_adapter.py`
- `src/cidls/ocr_pipeline/adapters/gui_common.py`
- `src/cidls/ocr_pipeline/ocr_result_parser.py`
- `src/cidls/ocr_pipeline/rpainput_converter.py`
- `src/cidls/ocr_pipeline/evidence_logger.py`
- `src/cidls/codex_global_loop/maintenance.py`
- `src/cidls/codex_global_loop/wiring_audit.py`
- `src/cidls/codex_global_loop/kanban_ticket_store.py`
- `src/cidls/codex_global_loop/devrag_bridge.py`
- `scripts/audit_global_cidls_wiring.py`
- `scripts/refresh_global_cidls_devrag.py`

## 7. Web画面を含むTDD設計

| 層 | 対象 |
|---|---|
| 純粋関数ユニット | Parser、Converter、DPI、EvidenceLogger。 |
| アダプタ統合 | Snipping Tool / PowerToys / WinOCR のGUI依存をモックし、retryと失敗原因を検証。 |
| Web E2E | Playwrightで `fixtures/web/ocr_test_target.html` を表示し、固定文字列とレイアウトを検証。 |
| Windows GUI準E2E | `--run-gui -m gui` で実Snipping Toolを通す。 |
| グローバル配線監査 | `%CODEX_HOME%` のAGENTS/hooks/mcp/skills差分を検出。 |
| kanban同期 | `ProjectKanbanTicketStore` が `CIDLS-*` を作成/更新することを検証。 |

テストケースは、単一ラベル、複数行フォーム、日本語混在、数字記号、表形式、改行崩れ、OCR誤字、UI位置ずれ、Snipping Tool起動遅延、クリップボード未取得、OCR空、PowerToys代替、再試行成功、再試行失敗、global AGENTS/hooks/mcp/skills差分、hook初回成功、hook失敗後installer1回、kanbanチケット追加、blocker追加、水平展開漏れ検知、devrag関連ファイル発見を対象にする。

## 8. TDD実行フロー

```powershell
cd <CIDLS_REPO>
cmd /c %CODEX_HOME%\hooks\run-cidls-hook.cmd
python scripts\sync_agents_cidls_policy.py
python -m pytest tests\ocr_pipeline\unit -q
python -m pytest tests\ocr_pipeline\integration -q
python -m pytest tests\ocr_pipeline\e2e -q
python -m pytest tests\codex_global_loop -q
set CIDLS_GUI_CAPTURE_REGION=120,220,780,420
set CIDLS_SNIPPING_TEMPLATE_DIR=<CIDLS_REPO>\fixtures\templates\snipping_tool
python -m pytest --run-gui -m gui
python scripts\audit_global_cidls_wiring.py
python scripts\refresh_global_cidls_devrag.py
```

## 9. 安定化戦略

座標固定は領域指定のみに限定し、Snipping Tool操作はウィンドウタイトル、テンプレート画像、フォーカス待機、クリップボード監視で扱う。アクティブウィンドウは `WindowGateway.activate()` と `wait_until_active()` で確認する。リトライは `CaptureRequest.retry_count`、タイムアウトは `timeout_seconds` と `action_timeout_seconds` で分離する。失敗時は `failure.png`、`manifest.json`、`error_events`、`retry_events` を残す。DPI差は `set_dpi_aware()` と固定Webプレビュー領域で抑える。多言語OCRは `language_hint` とNFKC正規化で吸収し、OCR品質そのものは実画面準E2Eで確認する。installerは `pre_prompt_cycle.bat` がruntime未初期化を示した場合だけ1回実行する。水平展開は code/docs/QA/scenario/project.md/TODO.md/kanban を同時確認する。

## 10. セキュリティ / プライバシ

OCR対象に個人情報が含まれる場合は `--secure-mode` を使い、メール、電話、郵便番号を証跡でマスクする。保存先は `reports/ocr_pipeline/<idempotency_key>`。機密データを残さない運用では、raw text保存を避ける外部ラッパーで実行後削除し、監査manifestのみを保管する。開発時は詳細ログ、本番時はmanifest中心にする。`%CODEX_HOME%` 配下の変更は `scripts/audit_global_cidls_wiring.py` と `logs/global_cidls_wiring_report.json` で証跡化する。

## 11. 完了判定

完了判定は、Web代表ケースでOCRから構造化変換まで通る、実Windows画面で1ケース通る、PowerToys代替が動く、失敗ログが原因追跡可能、CIDLS CLIから呼べる、冪等再実行できる、保守ループが定義通り動く、global wiring監査結果が出る、`project_kanban.html` に未処理タスク/blockerを更新できる、devrag探索結果を残せる、の全件である。

## 12. 最終成果物

実装ファイルは `src/cidls/ocr_pipeline/*` と `src/cidls/codex_global_loop/*`。実行手順は `docs/ocr_pipeline_runbook.md`。テスト手順は本書8章と `docs/test_scenarios.md`。想定リスクはSnipping Tool UI変更、Windows通知挙動、DPI差、OCR誤認識、クリップボード競合、global wiring差分。未解決blockerは `CIDLS-128` のuv cache ACL denial。次に監視する点は、global wiring issuesが空の継続、devrag refreshの `already_current` 継続、uv runの復旧である。
