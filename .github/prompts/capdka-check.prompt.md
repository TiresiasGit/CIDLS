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

RECEゲート [HCAPDKA]:  # kA移行前に必須チェック
  R(根源的): L4以深に届いているか → <Yes/No>
  C(具体的): 抽象語ゼロ・数値/コード/手順で表現済みか → <Yes/No>
  Cl(明確): TBD/要確認/不明ゼロ・全分岐明示済みか → <Yes/No>
  E(要素的): MDL原理で最小分解済みか → <Yes/No>
  判定: 全Yes→kAへ | いずれかNo→展開Levelと展開フェーズを明示

次ステップ: RECE全Yes → ActionPlanフェーズへ / いずれかNo → 下位Level CAPDkA展開
```
