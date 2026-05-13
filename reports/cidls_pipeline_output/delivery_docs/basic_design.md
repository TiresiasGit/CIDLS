# 基本設計書

対象: CIDLS商用請負納品パッケージ

## 位置づけ
この文書は、CIDLSコンセプトパイプラインを日本語仕様とローカル生成物へ変換した成果物である。

## 共通方針
- 人のアイデアを起点に、概念画像、標準成果物、Codexローカル実装、納品出力へ順番に変換する。
- Codexは外部Webビルダーの代替として、ローカルファイル生成と検証だけを行う。
- 勝手なデプロイ、外部公開、追加スケジューラ登録は行わない。

## 対応成果物
- アプリケーション本体設計: `app_blueprint.html`
- システムDA表: `system_da_table.html`
- PJグラフマインドマップ: `graph_project_mindmap.html`
- 全画面設計図: `screen_overview.svg`
- 画面状態遷移図および画面設計書: `screen_state_design.html`
- コンセプトスライド: `concept_slide.html`
- STORY.html: `STORY.html`
- 商用請負納品ドキュメント一式: `delivery_docs/`

## 合格条件
- 要求、設計、テスト、運用の対応が切れない。
- `cidls_pipeline_report.json` に生成結果が残る。
- 生成ファイルがローカルで再実行可能である。
