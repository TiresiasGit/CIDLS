---
name: capdka-cycle
description: 'CAPDkAサイクル(Check→ActionPlan→Plan→Do→Knowledge蓄積)を実行する開発ワークフロー'
---

# CAPDkA開発サイクル スキル

このスキルを使うと、AGENTS.mdのCAPDkAサイクルに従った体系的な開発プロセスを実行できます。

## CAPDkAサイクルとは [P2.1]

PDCAではなくC(Check)から開始する永久循環型の開発サイクルです。

```
C(Check/評価)
  ↓ As-Is現状把握 + Why×5根本原因特定
A(ActionPlan/計画)
  ↓ MECE発散 → ECRS収束 → ToBe定義
P(Plan/設計)
  ↓ アーキテクチャ + DFD + 依存関係
D(Do/実装)
  ↓ TDD(Red→Green→Refactor) + 段階的修正
kA(Knowledge蓄積)
  ↓ kanban_project.htmlへ蓄積
  ↓ 即座にC(Check)へ回帰 ← 永久停止なし
```

## 使用方法

チャットで `/capdka-cycle` とタイプするか、このスキルを呼び出してください。

## Step-by-Step手順

### S1. C(Check): As-Is現状把握
```
1. インターネット検索で既知解を調査
2. コードベースを調査
3. Why×5根本原因分析 (L0〜L5全層)
4. 多人格会議で分析を評価
```

**[CIDLSパイプライン Cフェーズ必須出力]**
```
① システムDA表.xlsx
   内容: 業務機能一覧 + 対象ユーザー + 主要機能 + 非機能要件
   タイミング: S1.AsIs完了時
```
```
S2. MECE + SCAMPER で問題空間を洗い出す
S3. ECRS で解決策を絞り込む
    E(排除) → C(統合) → R(再配置) → S(簡素化)
```

**[CIDLSパイプライン Aフェーズ必須出力]**
```
② PJグラフマインドマップ.html
   内容: 全体構造 + 関係性図
   タイミング: S4.ToBe完了時(S6.コンセプトイメージ化)

⑥ コンセプトスライド.html
   内容: [SLIDE]準拠のコンセプト資料
   タイミング: S6.コンセプトイメージ化完了時
```
```yaml
ToBe:
  T0.ビジョン: <>
  T1.目的: <>
  T2.目標: <>
  T3.KPI: <>
  T4.達成条件: <>
  T5.検証手段: <>
```

### S7. A(ActionPlan): 要求要件整理
```yaml
Must:   [必須]
Should: [推奨]
Want:   [検討]
```

### ⚠️ D(Do)進入前の必須チェック [Phi1.6 / P2.4]

> **即実装禁止**: C(Check)とA(ActionPlan)が完了していない状態でD(Do)に入ることを禁止する。
> 新規開発も修正も同様。「とりあえず書いてみる」はバイブコーディングの入口。

```
進入条件 (全て満たすこと):
  [ ] S1: As-Is把握 + Why5根本原因 → 文書化済み
  [ ] S2-S3: MECE発散 + ECRS収束 → 解決策が絞られている
  [ ] S4: ToBe (T0-T5) → 定義済み
  [ ] S7: Must/Should/Want → 優先度が決定済み
  [ ] アーキテクチャ設計 → ファイル構成・依存関係が決定済み

1つでも未完了 → C/Aフェーズに戻る (実装開始しない)
```

### S8-S9. D(Do): 設計→実装
```
1. アーキテクチャ設計
2. TDD: Red → Green → Refactor
3. grep水平展開同期 (7箇所)
4. ログ充実化
```

**[CIDLSパイプライン Dフェーズ必須出力]**
```
⑤ 画面状態遷移図および画面設計書.html
   内容: 遷移図 + 画面仕様 + ワイヤーフレーム ([UI.5][UI.6]準拠)
   タイミング: S8.設計完了時

除外 ④ 画面設計図.png → 手動/映像のためAI自動出力対象外
```
```
1. ユーザー実行で最終検証
2. テスト通過 ≠ 問題解決 (reward hacking注意)
3. 実動作確認完了まで「完了」と言わない
```

### kA. Knowledge蓄積
```
1. kanban_project.htmlを更新
2. MO必須出力チェック (4成果物)
3. 即座にC(Check)へ回帰
4. [PORT.5] 知識ベースポータビリティ保証:
   - kanban_project.html単体で開ける状態を維持
   - devrag vectors.dbは再構築可能設計を保つ
   - 全成果物をgit管理しオフラインでも再現可能に
```

## 矛盾解決パターン [Phi1.6 / TH.1]

開発中に「要件が矛盾する」「設計が行き詰まる」状況は必ず起こる。
細部レベルで格闘し続けることは禁止。以下の手順で脱出する。

```
矛盾発生時の手順:

  1. 「矛盾している」と認識 → 細部での解決を試みるのをやめる

  2. 抽象度を1段上げる
     例: 関数レベルの矛盾 → モジュール設計レベルで再考
         データ構造の矛盾 → アーキテクチャレベルで再考
         要件の矛盾 → 目的(ToBe T1)レベルで再考

  3. 上位層で再推論
     - 細部の制約を「いったん忘却」して抽象層で整合解を求める
     - Why5を1層上から再起動する

  4. 整合解を下降展開
     - 上位で合意した方針を細部へ具体化する
     - 元の矛盾箇所が自然に解消されているか確認

  5. 解消されない場合 → CAPDkA A(ActionPlan)フェーズへ戻る
```

### 適用トリガー [Phi1.6]
| 状況 | 対処 |
|------|------|
| 要件が矛盾する / ステークホルダー間で認識齟齬 | 粒度を上げて再推論 |
| 修正が同じ箇所に3回以上集中 | 真因未到達の兆候 → C(Check)へ |
| 複雑性スコア ≥ 0.7 | 多人格会議 [CN] を開催 |
| 「なぜ」に即答できない | A(ActionPlan)未完了の疑い |

## 差分切り分け観点 [DIFF]

**全フェーズで差分切り分けを必須適用する:**

| CAPDkAフェーズ | 差分アクション |
|---|---|
| C(Check) | 現状(Before)をgrepでスナップショット記録 |
| A(ActionPlan) | 変更箇所を最小単位で特定し影響範囲をリスト化 |
| D(Do) | 各実装ステップで差分報告フォーマットを適用 |
| kA(Knowledge) | 差分報告をkanban_project.htmlに蓄積 |

```
[DIFF] 差分報告
  変更ファイル: <ファイルパス:行番号>
  Before:       <変更前のコード/状態>
  After:        <変更後のコード/状態>
  変更理由:   <Why1回答 - 根本原因との接続>
  副作用:     なし (grep確認済み) | あり → <具体的影響先>
```

## 関連ファイル
- [capdka-checker.agent.md](../agents/capdka-checker.agent.md)
- [capdka-planner.agent.md](../agents/capdka-planner.agent.md)
- [implementer.agent.md](../agents/implementer.agent.md)
- [diff-isolation SKILL.md](../skills/diff-isolation/SKILL.md)
