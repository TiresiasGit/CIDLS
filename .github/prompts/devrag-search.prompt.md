---
description: 'devrag RAG検索: AGENTS.mdの知識ベースからセマンティック検索'
agent: agent
tools: ['mcp_devrag_search', 'mcp_devrag_list_documents', 'mcp_devrag_index_markdown']
---

# devrag RAG検索

AGENTS.mdの知識ベースからセマンティック検索を実行します。

## 検索クエリ
${input:query:検索したい概念・ルール・実装パターンを入力してください}

## 検索手順

### Step 1: devragで検索
```
search(query: "${query}", top_k: 5)
```

### Step 2: 結果の解釈
検索結果から:
- 最も関連性の高いチャンクを特定
- AGENTS.mdのセクション番号を確認
- 具体的なルール・実装パターンを抽出

### Step 3: 適用
抽出したルールを現在のタスクに適用:
- 禁止事項がないか確認
- 推奨パターンを採用
- 水平展開が必要か確認

## 検索対象ドキュメント

| ファイル | 内容 |
|----------|------|
| capdka-cycle.md | CAPDkAサイクル定義・Why5・ECRS |
| guard-rules.md | 絶対禁止事項・フォールバック禁止 |
| tech-stack.md | Python/uv/DuckDB/Parquet仕様 |
| quality-standards.md | JIS X 25010・TDD・MO必須出力 |
| horizontal-sync.md | 水平展開同期・7箇所同期手順 |
| multi-persona-council.md | 多人格会議・感情制御・reward hacking |
| security-rules.md | OWASP Top 10・セキュリティ規約 |

## トークン節約効果

devrag使用時:
- 通常のファイル読み込み: ~3,000トークン/ファイル
- devrag RAG検索:        ~200トークン/クエリ
- 節約率:                約40分の1
