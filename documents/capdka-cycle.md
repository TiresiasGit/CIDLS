# AGENTS.md - CAPDkAサイクル定義 [P2.1, CY]

> **SoT参照**: 定義のSource of Truthは `AGENTS.md [P2.1, CY]`。
> このファイルはdevrag RAG用実装ステップ・コード例を収録。

## CAPDkAサイクルとは (定義: AGENTS.md [P2.1])

PDCAではなくC(Check)から開始する永久循環型の開発サイクル。
kA完了→即C(Check)開始 (永久停止なし)

```
C(Check/評価)      → As-Is現状把握 + Why×5根本原因特定
A(ActionPlan/計画) → MECE発散 → ECRS収束 → ToBe定義
P(Plan/設計)       → アーキテクチャ + DFD + 依存関係
D(Do/実装)         → TDD(Red→Green→Refactor) + 段階的修正
kA(Knowledge蓄積)  → kanban_project.htmlへ蓄積 → 即C回帰
```

## S1. C(Check): As-Is現状把握

### 実行アクション
- [SEARCH] インターネット検索必須(エラー, 技術課題, 既知解決策)
- [VERIFY] 証拠優先因果検証(コメント!=現実 | grep→因果確認→証拠収集)
- [COUNCIL] 多人格会議: 現状分析
- [PRIMARY] ROOT_CAUSE特定(症状観察→Why5→構造理解)
- [EMOTION_CTRL] 感情自己チェック(焦り/絶望/過信検出→calm誘導)

### Why×5フォーマット
```
L0.現象: ユーザーが観測している表層事象
L1.症状: 頻度・影響範囲・再現条件
L2.直接原因: Why1 (症状を直接引き起こす要素)
L3.中間原因: Why2-Why4 (構造的要因の連鎖)
L4.根本原因: Why5 (これを除去すれば現象が消える)
L5.メタ原因: なぜ根本原因が放置されていたか
```

## S2-S3. A(ActionPlan): 発散→収束

### MECE発散 (S2)
- 問題空間を漏れなく洗い出す
- SCAMPER: S代替/C組合/A適応/M修正/P転用/E除去/R逆転

### ECRS収束 (S3)
```
E(Eliminate/排除): 既存類似機能確認 → 重複排除
C(Combine/統合):   類似機能の統合可能性評価
R(Rearrange/再配置): 処理順序最適化
S(Simplify/簡素化): 複雑処理の分解・単純化
```
新規作成前チェック: `grep -r "機能名" .` 必須
- 重複≥50% → 統合必須
- 重複<30% + 技術的必要性 → 新規作成許可

## S4. ToBe定義

```yaml
ToBe:
  T0.ビジョン: 究極理想(3-5年)|定性的価値
  T1.目的:    ビジョン実現方向性
  T2.目標:    目的達成具体状態|半定量
  T3.KPI:     目標達成度数値指標
  T4.達成条件: KPI到達+副作用ゼロ+持続性確認
  T5.検証手段: 達成判定の具体的測定方法
```

## S8-S10. D(Do): 実装→検証

### TDD必須 [Q1.2]
```
Red   → 失敗テスト作成
Green → 最小限実装
Refactor → 品質向上
```
カバレッジ: ユニット≥90%

### 実行順序 [T1.4]
```
READ → DELETE → CREATE → READ → UPDATE
```

## kA. Knowledge蓄積

1. kanban_project.htmlをupsert
2. MO必須出力チェック (4成果物)
3. 即座にC(Check)へ回帰 (永久停止なし)
4. [PORT.5] 知識ベースのポータビリティ保証:
   - kanban_project.htmlを単一HTMLで保存しメール添付で共有可能な状態を維持
   - devrag vectors.dbは再構築可能な設計を保つ (setup_devrag.ps1 1コマンド)
   - 全成果物をgitリポジトリで管理しオフライン環境でも再現可能にする

---

## 注文票フォーマット変換フロー [SUPRA.2]

> **SoT参照**: 定義のSource of Truthは `AGENTS.md [SUPRA.2, P1.2]`。
> CAPDkAサイクルの「入口」として、ユーザーの話し言葉を注文票に変換してからC(Check)を開始する。

```
ユーザーのフリーライト入力
  |
  v
[SUPRA.2] 注文票フォーマット変換
  - 変換: 話し言葉 → [P1.2] 注文票の専門用語
  - 因果整理: 7要素を埋める
    (誰が/何の/何に困り/根拠はこれで/いつまでで/理想はこうだから/解はこれ)
  - 記入チェック: [P1.3] Phase1-記入チェック通過
  - 実行準備: [P1.4] Phase2-実行チェック完了
  |
  v
C(Check): As-Is現状把握（変換済み注文票を元に）
  |
  v
A(ActionPlan): MECE発散 → ECRS収束 → ToBe定義
  |
  v
D(Do): TDD実装
  |
  v
kA(Knowledge蓄積): kanban_project.htmlへ → 即C回帰
```

### 注文票7要素フォーマット (抜粋)

```
[00] アウトライン: 誰が/何の/何に困り/根拠はこれで/いつまでで/理想はこうだから/解はこれ
[01] 対象者: 役職・業務・頻度
[02] As-Is: ツール・手順・件数・時間
[03] ペイン: 数値で定量化
[10] Why-原因: Why5最深層の根本原因・レバレッジポイント
[13] To-Be: 数値目標必須
[18] Must: 抽象語ゼロ・定量基準
```

詳細フォーマット → [P1.2] 参照 (SoT: [00]〜[24] 全25項目)
