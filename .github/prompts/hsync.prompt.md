---
description: '水平展開同期: 1概念変更後にgrep全検索→7箇所完全同期'
agent: agent
tools: ['codebase', 'editFiles', 'runCommand', 'search']
---

# 水平展開同期 (HSYNC) [HS]

AGENTS.mdの[HS]原則に基づき、変更した概念を全箇所に同期します。

## 同期対象の概念
${input:concept:同期したい概念・関数名・変数名・定義を入力してください}
${input:oldValue:変更前の値・名前（省略可）}
${input:newValue:変更後の値・名前}

## 実行手順

### Step 1: grep全検索
```bash
grep -r "${concept}" . --include="*.py" --include="*.md" --include="*.json" --include="*.yaml" -n
```

### Step 2: 7箇所の同期確認 [HS]
以下の全箇所に変更を適用:
1. **定義**: クラス・関数・定数の定義箇所
2. **辞書**: dict・設定値での参照箇所
3. **設定**: config・settings・ini での参照箇所
4. **分岐**: if/elif/match/case での参照箇所
5. **import**: import文・from import での参照箇所
6. **ドキュメント**: docstring・コメント・README での参照箇所
7. **テスト**: test_*.py での参照箇所

### Step 3: 旧名残存ゼロ確認
```bash
grep -r "${oldValue}" . --include="*.py" -n
# 結果がゼロであること
```

### Step 4: 整合性検証
- 変更前後で同一入力 → 同一出力であること
- テストが全てパスすること

## 禁止事項 [HS]
- 部分適用: 一部だけ変更して他を放置 → 禁止
- 観点ズレ: 関連するが微妙に違う概念の片側だけ修正 → 禁止
