---
description: 'CAPDkAサイクルのC(Check)フェーズを開始: As-Is現状把握とWhy5根本原因分析'
agent: capdka-checker
tools: ['search', 'web', 'codebase']
---

# CAPDkA Check フェーズ開始

以下の問題についてCAPDkAサイクルのC(Check)フェーズを実行してください。

## 対象問題
${input:problem:解決したい問題・エラー・課題を記述してください}

## 実施事項
1. インターネット検索で既知の解決策を調査
2. コードベースで関連ファイルを特定
3. Why×5で根本原因まで掘り下げ (L0〜L5の全層)
4. 多人格会議で現状分析を評価

## 出力形式
```yaml
AsIs分析:
  L0.現象: <>
  L1.症状: <>
  L2.直接原因: <>
  L3.中間原因: <>
  L4.根本原因: <>
  L5.メタ原因: <>
根拠: <>
次ステップ: ActionPlanフェーズへ
```
