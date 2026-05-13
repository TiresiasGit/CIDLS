---
name: devrag-rag
description: 'devrag MCPを使ってAGENTS.md知識ベースをRAG検索する。AGENTS.mdのルール・禁止事項・実装パターンを高速・低トークンで参照するときに使う'
---

# devrag RAG知識ベース スキル

このスキルを使うと、devrag MCPサーバー経由でAGENTS.mdの知識ベースをセマンティック検索できます。
ファイル全体を読み込むより**40倍少ないトークン**で必要な情報だけ取得します。

## セットアップ要件

1. devragバイナリをダウンロード: https://github.com/tomohiro-owada/devrag/releases
2. `C:\Program Files\devrag\devrag.exe` に配置
3. `.mcp.json` でMCPサーバーとして登録済み
4. `devrag-config.json` でドキュメントパスを設定済み

## 使用方法

### 基本検索
```
// AGENTS.mdのルールを検索
search(query: "フォールバック禁止ルール")
search(query: "水平展開同期の7箇所")
search(query: "uv仮想環境セットアップ")
search(query: "Why5根本原因分析の手順")
```

### フィルター検索
```
// セキュリティ関連のみ
search(query: "SQLインジェクション", directory: "documents")

// 品質関連のみ
search(query: "TDDカバレッジ", file_pattern: "quality-*.md")
```

## 知識ベース構成

| ファイル | 検索クエリ例 |
|----------|-------------|
| `documents/capdka-cycle.md` | "CAPDkAサイクル" "Why5分析" "ECRS" |
| `documents/guard-rules.md` | "フォールバック禁止" "絶対禁止" "決断主義" |
| `documents/tech-stack.md` | "uv仮想環境" "DuckDB" "cp932エラー" |
| `documents/quality-standards.md` | "TDD" "MO必須出力" "カバレッジ" |
| `documents/horizontal-sync.md` | "水平展開" "7箇所同期" "grep" |
| `documents/multi-persona-council.md` | "多人格会議" "ぽんぽんねこ" "reward hacking" |
| `documents/security-rules.md` | "OWASP" "SQLインジェクション" "認証認可" |
| `.github/**/*.md` | エージェント定義・スキル・プロンプト |

## トークン効率

```
従来 (Read tool):   3,000+ トークン/ファイル × 7ファイル = 21,000+ トークン
devrag RAG検索:     ~200 トークン/クエリ
削減率:             99%以上
```

## devrag CLI コマンド (手動操作時)

```powershell
# ドキュメントをインデックス化
devrag index ./documents/capdka-cycle.md

# 全ドキュメント一覧
devrag list

# 検索 (CLIから)
devrag search "フォールバック禁止" --output text

# 再インデックス (ドキュメント更新後)
devrag reindex ./documents/guard-rules.md
```

## 差分切り割な知識検索 [DIFF]

差分切り分けに関わるRAG検索例:

```
// 差分切り分けの変更報告フォーマット
search(query: "差分報告フォーマット Before After")

// 副作用チェック手順
search(query: "副作用チェック grep 水平展開")

// バイナリサーチデバッグ
search(query: "バイナリサーチ デバッグ 差分切り分け")

// 水平展開と差分の連携
search(query: "水平展開7箇所 差分 負荷")
```

| ファイル | 差分切り分け関連検索クエリ |
|----------|---------------------|
| `documents/diff-isolation.md` | "差分切り分け" "Before After" "DIFF" |
| `documents/horizontal-sync.md` | "水平展開" "7箇所" "差分波及" |
