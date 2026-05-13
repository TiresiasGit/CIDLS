---
name: 'テスト規約 (TDD準拠)'
description: 'テストコードのコーディング規約'
applyTo: '**/test_*.py,**/*_test.py,**/*.test.ts,**/*.spec.ts'
---

# テスト規約 (TDD必須)

## TDDサイクル [Q1.2]
```
Red   (失敗テスト作成)
  -> Green   (最小限実装でパス)
    -> Refactor (品質向上)
      -> 次のRedへ
```

## カバレッジ基準 [Q1.2]
- ユニットテスト: **≥90%**
- 統合テスト: 全API / 全DB操作 / 全モジュール境界

## テスト構造 (Given-When-Then) [Q3.2]
```python
def test_機能名_条件_期待結果():
    # Given: 前提条件
    input_data = {...}

    # When: 操作
    result = target_function(input_data)

    # Then: 期待結果
    assert result == expected_value
```

## 禁止パターン [G1, VF.3]
```python
# 禁止: モックデータで完了宣言
def test_something():
    assert mock_function() == "expected"  # 実際の動作を検証していない

# 禁止: テスト通過 = 問題解決 の断定
# テスト合格 ≠ 問題解決 (reward hacking検出)
```

## 必須テストシナリオ [Q3.3]
- 正常系: 期待通りの入力と結果
- 異常系: 不正入力・エラー条件
- 境界値: 最小・最大・境界値
- 否定パターン: 禁止操作が拒否されること
- エッジケース: 空配列・None・ゼロ

## フレームワーク
```
Python: pytest + pytest-xdist (並列実行)
カバレッジ: pytest-cov
```
