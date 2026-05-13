# CIDLSコンセプトパイプライン

## 目的

添付されたCIDLSパイプライン画像の内容を、ローカルCIDLSで実行できる日本語仕様とプログラムコードへ変換する。

この実装では、外部Webビルダーが担っていた役割をCodexが置き換える。Codexはローカル成果物の生成、検査、記録だけを行い、勝手なデプロイや外部公開は行わない。

## 変換ルール

1. 人のアイデアを、対象者・ペイン・理想・解決策へ正規化する。
2. 画像または概念メモを、AGENTS.md準拠の成果物候補へ分解する。
3. Codexが標準成果物を生成する。
4. Codexローカルビルダーが、アプリ本体の設計HTMLと納品文書一式を生成する。
5. 生成結果を `cidls_pipeline_report.json` に残す。

## 標準成果物

- `system_da_table.html`: データ名、説明、主な項目、関連テーブルを整理する。
- `graph_project_mindmap.html`: 注文票、カンバン、レポート、設計成果物の因果関係を表す。
- `screen_overview.svg`: 全画面設計図を静的図として出力する。
- `screen_state_design.html`: 画面状態遷移図と画面設計書を兼ねる。
- `concept_slide.html`: 非技術者にも説明できるコンセプトスライドを出力する。
- `STORY.html`: プロダクトオーナー、バックエンドサーバー、本アプリ、決済サービス、ユーザー端末、ユーザーを最低登場人物として、決済・契約・Webhook・キャンセル・入金の業務ストーリーを出力する。
- `app_blueprint.html`: アプリ本体のローカル試作品を出力する。
- `delivery_docs/`: 要求、基本設計、詳細設計、テスト、運用、受入確認の文書を出力する。

## 実行方法

```powershell
uv run python -m cidls.concept_pipeline.cli describe
uv run python -m cidls.concept_pipeline.cli materialize --output-dir reports/cidls_pipeline_output
```

`cidls-concept-pipeline` のコンソールエントリも登録しているが、Windowsのアプリ制御ポリシーで生成exeがブロックされる環境では上記の `python -m` 経路を使う。

## 完了条件

- `reports/cidls_pipeline_output/cidls_pipeline_report.json` が生成される。
- レポート内の `deployment_performed` が `false` である。
- 生成されたHTML、SVG、Markdownがローカルファイルとして確認できる。
- テスト `tests/test_concept_pipeline.py` が成功する。
