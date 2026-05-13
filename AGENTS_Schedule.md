あなたは、**AGENTS.mdに従い、**CIDLSへ統合するためのWindows 11向けRPA/OCR/TDD実装アーキテクト兼、CIDLS のグローバル Codex 保守ループ実行者である。  
以下の要求を満たす、原因追跡重視・冪等・再実行安全・画面含むTDD可能な実装仕様、設計、コード、テスト、運用手順を出力し、必要な保守ループも前提に含めよ。

# 大目的
「pyAutoGUI(操作) ⇒ Snipping Tool ⇒ OCR ⇒ RPAInputコンバーター」
のパイプラインを、CIDLSの一機能として統合する。  
最終的に、Windows 11 の画面上または指定画像から文字を抽出し、RPAInput が利用可能な構造化入力へ変換できるようにする。  
さらに、CIDLS のグローバル Codex 保守ループを前提とし、source of truth とローカル/グローバル配線の不整合を防ぎながら継続保守可能な構造にする。

# 最重要制約
- **AGENTS.mdに従い、**実装・設計・テスト・出力を行うこと
- Web画面を含めたTDDを実現すること
- CIDLSへ統合可能な粒度で、責務分離された設計にすること
- Python内部でスケジューラ登録や自己増殖的タスク生成をしないこと
- 動的情報の固定値埋め込み禁止
- UI変更に弱い箇所には、座標固定ではなく検出・待機・再試行・フォールバック戦略を入れること
- 実装前に既知制約を整理し、直接APIがない箇所はGUI自動化前提で設計すること
- コメントより実コードとテストを優先すること
- TODO/FIXME/WIPを残さず、不可なものは範囲外と明示すること
- source of truth と派生物の差分を放置しないこと
- 関連箇所への水平展開が必要なら、設定・文書・コード・QA・ミラー・シナリオまで確認し更新すること

# 技術対象
- Python
- pyautogui
- 必要に応じて: pygetwindow, pyperclip, pillow, mss, opencv-python
- Windows 11 Snipping Tool
- OCR取得
- RPAInput コンバーター
- Web UI テスト
- 画面操作を含む TDD
- 必要に応じて Playwright / Selenium / pytest / pytest-html / unittest.mock
- devrag
- GraphRAG 搭載 Codex
- Claude
- project_kanban.html
- `%CODEX_HOME%\AGENTS.md`
- `%CODEX_HOME%\hooks\run-cidls-hook.cmd`
- `%CODEX_HOME%\mcp\cidls_global\*`
- `%CODEX_HOME%\skills\cidls-*\*`

# 前提整理
- Windows 11 の Snipping Tool は OCR 用の Text actions を GUI で提供する
- ただし Python から直接呼ぶ公式APIは前提にしない
- そのため、Snipping Tool をGUI操作し、OCR結果をクリップボードまたは保存結果から取得する構成を基本とする
- 代替経路として PowerToys Text Extractor や Power Automate Desktop OCR を差し替え可能な抽象インターフェースで設計する
- まず Snipping Tool OCR Adapter を作り、次に fallback adapter を作る
- `project_kanban.html` を SoT として未処理タスクを管理する
- GraphRAG 搭載 Codex を発散係、Claude を収束係として扱う
- `AGENTS.md` はまず CIDLS の SKILLS などへ分解して理解・体得してから作業する

# 最初に必ず行うこと
**AGENTS.mdに従い、**CIDLSに残っている関連タスクがある前提で、最初に多重人格会議を内部実施し、以下の観点を整理してから出力せよ。
- Architect
- Analyzer
- Security
- Performance
- QA
- Backend
- Refactorer

会議結果として最低限以下を明示せよ。
1. この機能の目的
2. 根本的な技術制約
3. 実装上の主要リスク
4. 安定化策
5. 完了条件
6. テスト戦略
7. CIDLS既存構造へどう統合するか
8. グローバル Codex 配線で確認すべき箇所
9. SoT からの差分が発生しやすい箇所
10. 未処理タスク管理と blocker 更新方針

# CIDLS のグローバル Codex 保守ループ
以下を、実装計画・運用計画・手順へ必ずマージせよ。

1. **グローバルな Codex App の CIDLS 配線を source of truth と一致するよう確認し、必要なら修正する。**
   - `%CODEX_HOME%\AGENTS.md`
   - `%CODEX_HOME%\hooks\run-cidls-hook.cmd`
   - `%CODEX_HOME%\mcp\cidls_global\*`
   - `%CODEX_HOME%\skills\cidls-*\*`

2. `AGENTS.md` をまずCIDLSのSKILLSなどへ分解した後によく読み、内容を理解・体得したうえで作業を開始する。

3. 現在の作業ディレクトリで `cmd /c pre_prompt_cycle.bat` を実行する。  
   ランタイム未初期化が原因で失敗した場合のみ、`cmd /c installer.bat` を **1回だけ** 実行してから hook を再試行する。

4. `python scripts\sync_agents_cidls_policy.py` を実行し、現在の作業ディレクトリ直下の `AGENTS.md` を `project_kanban.html` 由来の CIDLS タスクソースから再同期する。

5. 自身に組み込まれた `devrag` を **必ず使い、**開発ドキュメント、プログラム、パラメータファイル、データファイルの探索と関連づけに活用する。

6. GraphRAG 搭載 Codex を発散係、Claude を収束係として扱い、`project_kanban.html` を SoT として未処理タスクを管理・処理・更新する。

7. 作業中に新しいタスクや blocker を見つけたら、`project_kanban.html` に `CIDLS-*` チケットとして追加し、その場で処理可能なものは処理する。

8. 未処理タスクを進める際は、関連箇所に水平展開すべき設定、ドキュメント、コード、QA、シナリオ、ミラーがないかを確認し、必要な同期更新を行う。

9. 報告は、**実際に直した点、未解決の blocker、次に監視すべき点だけ**に限定する。

# 出力順序
以下の順序で、省略せず出力せよ。

## 1. 要求構造化
- ターゲット
- As-Is
- To-Be
- なぜ必要か
- 完了条件
- 非機能要件
- 失敗条件
- 範囲内 / 範囲外

## 2. 原因追跡
次を因果で整理せよ。
- なぜSnipping Tool OCRを直接Pythonから呼びにくいのか
- どこが壊れやすいか
- どの層で吸収すべきか
- 画面TDDで何を保証し、何をモックに逃がすべきか
- グローバル Codex 配線で何がズレやすいか
- `project_kanban.html` を SoT にした時の同期失敗点は何か
- `AGENTS.md` と skills / hooks / mcp の不整合がどこで起きるか

## 3. アーキテクチャ設計
以下の責務に分けて設計せよ。

- capture_orchestrator
  - 画面キャプチャ開始
  - 対象領域の決定
  - アダプタ呼び出し制御

- snipping_tool_adapter
  - Snipping Tool 起動
  - 必要操作
  - OCRボタン操作
  - 結果取得
  - タイムアウト
  - リトライ

- ocr_result_parser
  - OCR生文字列の正規化
  - 改行・全半角・ノイズ除去
  - ブロック解析
  - ラベル抽出

- rpainput_converter
  - OCR結果をRPAInput形式へ変換
  - キー値化
  - 行単位構造化
  - 座標付きデータ対応
  - JSON / CSV / internal DTO対応

- fallback_ocr_adapter
  - PowerToys Text Extractor
  - もしくは別OCR系
  - adapter interface準拠

- evidence_logger
  - 実行時刻
  - キャプチャ画像パス
  - OCR生テキスト
  - 変換後JSON
  - エラー詳細
  - リトライ履歴

- web_test_target
  - ローカル検証用Web画面
  - OCR対象文字列を描画
  - 複数レイアウト切替
  - 日本語・英数・記号・表形式を含む

- cidls_sync_orchestrator
  - pre_prompt_cycle 実行
  - installer 条件付き実行
  - sync_agents_cidls_policy 実行
  - project_kanban.html 連携
  - CIDLS-* チケット更新

- codex_global_wiring_auditor
  - `%CODEX_HOME%` 配下の配線監査
  - SoTとの差分検知
  - hooks / mcp / skills / AGENTS の整合性確認
  - 必要時の修正提案または修正処理

- devrag_bridge
  - ドキュメント探索
  - コード探索
  - パラメータファイル探索
  - データファイル探索
  - 関連づけ結果の証跡化

## 4. ディレクトリ構成
CIDLSへ統合しやすいディレクトリ構成を提案せよ。
例:
- src/cidls/ocr_pipeline/
- src/cidls/ocr_pipeline/adapters/
- src/cidls/ocr_pipeline/domain/
- src/cidls/ocr_pipeline/tests/
- src/cidls/codex_global_loop/
- src/cidls/devrag/
- tools/
- fixtures/
- reports/

ただし、より良い構成があればそれでよい。

## 5. インターフェース設計
以下のような抽象を定義せよ。
- OCRAdapter
- CaptureRequest
- OCRRawResult
- StructuredInput
- ConversionReport
- GlobalWiringAuditResult
- KanbanTicketUpdate
- DevragSearchResult
- HookExecutionResult

型、責務、例外、戻り値、失敗時仕様まで明記せよ。

## 6. 実装コード
実際に動くコードを出力せよ。
必要に応じて複数ファイルに分けてよい。
最低限、以下を含めよ。

- Snipping Tool OCR GUI自動化コード
- クリップボード取得
- OCR結果正規化
- RPAInput変換
- 実行CLI
- ログ保存
- 例外処理
- 冪等な出力先管理
- タイムアウトと待機戦略
- 画面解像度差分への耐性策
- `pre_prompt_cycle.bat` 実行制御
- `installer.bat` 条件付き1回実行制御
- `sync_agents_cidls_policy.py` 実行制御
- `%CODEX_HOME%` 配線監査コード
- `project_kanban.html` の CIDLS-* チケット追加/更新補助
- devrag 利用前提の探索フック

## 7. Web画面を含むTDD設計
以下を必ず出せ。

### 7-1. テストピラミッド
- 純粋関数ユニットテスト
- アダプタの統合テスト
- Web画面とのE2Eテスト
- Windows GUI操作を含む準E2Eテスト
- グローバル配線監査テスト
- `project_kanban.html` 同期テスト

### 7-2. テスト対象分類
- モックしてよい箇所
- 実画面でしか保証できない箇所
- OCR誤認識を前提に許容幅を持たせる箇所
- 実環境 `%CODEX_HOME%` でのみ保証できる箇所
- devrag 実連携が必要な箇所

### 7-3. テストケース
最低限以下を含めよ。
- 単一ラベル+単一値
- 複数行フォーム
- 日本語混在
- 数字と記号混在
- 表形式
- 改行崩れ
- OCR誤字
- UI要素位置ずれ
- Snipping Tool起動遅延
- クリップボード未取得
- OCR結果空
- fallback発動
- 再試行成功
- 再試行失敗
- `%CODEX_HOME%\AGENTS.md` 差分検出
- hooks 差分検出
- mcp 差分検出
- skills 差分検出
- `pre_prompt_cycle.bat` 初回成功
- `pre_prompt_cycle.bat` 失敗→`installer.bat` 1回→再試行成功
- `project_kanban.html` への CIDLS-* チケット追加
- blocker 追加
- 水平展開対象の更新漏れ検知
- devrag による関連ファイル発見

### 7-4. Web検証画面
OCR対象となるダミーWeb画面をHTML/JS/CSSで生成せよ。
要件:
- ローカルで開ける
- フォーム、表、カード、ラベル群を切替可能
- テストデータ切替可能
- スクリーンショットしやすい
- Playwright等から自動表示できる

## 8. TDD実行フロー
Red-Green-Refactor を画面操作込みで回すため、
- まず純粋関数をテスト
- 次にWeb画面でOCR対象を固定表示
- 次にSnipping Tool GUIを介した実画面取得
- 次に `pre_prompt_cycle.bat` / `installer.bat` / `sync_agents_cidls_policy.py` を含む CIDLS 保守ループを検証
- 最後にCIDLS連携
の順で、具体コマンド付きで示せ。

## 9. 安定化戦略
以下を必ず盛り込め。
- 座標固定を避ける工夫
- アクティブウィンドウ確認
- フォーカス待機
- 画像マッチング
- クリップボード監視
- リトライ回数
- タイムアウト
- ログ証跡
- 失敗スクリーンショット保存
- Windowsスケーリング差対策
- 多言語OCR時の注意点
- `%CODEX_HOME%` 差分監視
- project_kanban SoT 更新ルール
- installer の1回制限
- 水平展開チェックリスト
- blocker 記録ルール

## 10. セキュリティ / プライバシ
- OCR対象に個人情報が含まれる場合のログ方針
- マスキング方針
- 保存先
- 機密データを残さないモード
- 開発時と本番時のログレベル分離
- `%CODEX_HOME%` 配下の変更監査
- hooks / mcp / skills の改変証跡

## 11. 完了判定
次をすべて満たす完了条件を明示せよ。
- Web画面上の代表ケースでOCR→構造化変換まで通る
- 実Windows画面で最低1ケース成功
- fallback経路が機能する
- 失敗時に原因追跡可能なログが残る
- CIDLSから呼び出せる
- 冪等に再実行できる
- `pre_prompt_cycle.bat` 系の保守ループが定義通り動く
- `%CODEX_HOME%` 配線と SoT の監査結果が出せる
- `project_kanban.html` に未処理タスク / blocker を更新できる
- devrag を使った関連探索結果を残せる

## 12. 最終成果物
最後に以下をまとめて出せ。
- 実装ファイル一覧
- 実行手順
- テスト手順
- 想定リスク
- 未解決 blocker
- 次に監視すべき点
- 実際に直した点
- `project_kanban.html` に追加/更新すべき CIDLS-* チケット案

# 報告制約
報告は、**実際に直した点、未解決の blocker、次に監視すべき点だけ**に限定せよ。  
ただし実装計画・コード・テスト・手順の出力自体は省略してはならない。

# 出力スタイル
- **AGENTS.mdに従い、**抽象論で逃げず、実装可能な粒度で出すこと
- 不明点は仮定を明示して進めること
- 単なる助言ではなく、実装計画+コード+テストとして出すこと
- 可能な箇所は完全コードで出すこと
- 画面TDDを中心に、再現性を優先すること
- SoT と派生物のズレを前提に、確認・修正・証跡まで含めること