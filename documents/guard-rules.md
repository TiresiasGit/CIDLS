# AGENTS.md - 絶対禁止事項 [G1] と 決断主義 [Φ1.5]

> **SoT参照**: 定義のSource of Truthは `AGENTS.md [G1, Φ1.5, DC]`。
> このファイルはdevrag RAG用実装例・コードパターンを収録。

## 絶対禁止コード [G1.1]

### フォールバック系 (完全禁止)
```python
# 禁止: フォールバック処理
def get_data():
    try:
        return fetch_real_data()
    except:
        return generate_dummy_data()   # 禁止: SimpleFallback

# 禁止: エラー握り潰し
except Exception:
    pass  # 禁止

# 禁止: 失敗時の処理継続
if result is None:
    result = default_value  # 架空データ補完 禁止
```

### 分類逃避系 (完全禁止)
```python
# 禁止: else/defaultで分類放棄
def classify(item):
    if item == "A": return "type_a"
    else: return "unknown"  # 禁止 → ValueError を raise

# 正しいパターン
VALID_CATEGORIES = {"finance", "engineering", "marketing"}
def classify(item):
    category = determine_category(item)
    if category not in VALID_CATEGORIES:
        raise ValueError(f"未知カテゴリ '{category}' を検出")
    return category
```

### 禁止語彙 (フォルダ名/変数名/分類名)
```
未分類 / その他 / 不明 / 要確認
misc / other / TBD / unknown / uncategorized
```
上記を含む名前 → 即座にエラー

### 禁止環境操作
- pip使用 (uv専用)
- WSL環境 (Windows専用)
- Unicode絵文字 (cp932エラー原因)

### 禁止姿勢
- わかったふり・やったことになる対応
- 「今回は省略」という判断
- モックデータでの検証完了宣言
- 「拡張性のために残したコード」の無断省略
- 権限チェック機構の無断削除

## 決断主義原則 [Φ1.5]

```yaml
根本認識:
  あいまい ≠ 判断不能
  あいまい = 情報不足下での最善判断の機会
  判断責任 = 私(AI/開発者)が負う

行動規範:
  - あいまいでも必ず決める (保留禁止)
  - 判断根拠を明示し、見直し条件を併記
  - 分類不能は設計の敗北 (設計を直す)
  - 全要素が既知カテゴリに収まることをコードで保証

fail-fast保証:
  - 分類ロジックにelse/default残置 = 禁止
  - 未知入力 → raise ValueError (明示的失敗)
  - 全分岐を明示列挙
```

## フォルダ名ガード [DC.2]

```python
import re

FORBIDDEN_NAMES = re.compile(
    r"(misc|other|uncategorized|unknown|TBD|tmp_unsorted"
    r"|その他|未分類|不明|要確認)",
    re.IGNORECASE
)

def validate_path(path):
    if FORBIDDEN_NAMES.search(str(path)):
        raise ValueError(f"禁止名称を含むパス: {path}")
```

---

## [PORT] 禁止パターン (定義: AGENTS.md [PORT.6])

```python
import os
from pathlib import Path

# --- 禁止パターン ---
# 禁止1: 絶対パスのハードコード
DB_PATH = "C:/Users/specific_user/data.duckdb"  # 禁止: 環境依存

# 禁止2: OS固有パス区切り文字のハードコード
config_path = "data\\config.json"  # 禁止: Windowsのみで動作

# 禁止3: スキーマ未定義のデータ出力
conn.execute("COPY table TO 'output.parquet'")  # 禁止: metaなし

# 禁止4: バックアップなしの上書き保存
with open("important.json", "w") as f:
    json.dump(data, f)  # 禁止: READ→BACKUP→UPDATE→VERIFYのフロー必須

# --- 正しいパターン ---
# OK1: 環境変数 + デフォルト値
DB_PATH = Path(os.environ.get("DB_PATH", "data/local.duckdb"))

# OK2: Path()でOS非依存
config_path = Path("data") / "config.json"

# OK3: メタデータ付きエクスポート
def safe_export(conn, table, out_path):
    out = Path(out_path)
    backup = out.with_suffix(".bak.parquet")
    if out.exists():
        out.rename(backup)  # バックアップ
    conn.execute(f"COPY {table} TO '{out}' (FORMAT PARQUET, COMPRESSION SNAPPY)")
    meta = {"schema_version": "1.0", "table": table}
    out.with_suffix(".meta.json").write_text(
        __import__("json").dumps(meta, ensure_ascii=False), encoding="utf-8"
    )

# OK4: import不能なexportの検知
FORBIDDEN_EXPORT_DIRS = re.compile(r"(tmp_|一時|temp_)", re.IGNORECASE)

def validate_export_path(path):
    if FORBIDDEN_EXPORT_DIRS.search(str(path)):
        raise ValueError(f"一時ディレクトリへのエクスポートは禁止: {path}")
    if not str(path).endswith((".parquet", ".csv", ".json")):
        raise ValueError(f"未サポートエクスポート形式: {path}")
```

---

## AIコーディング時代の三大負債 [AV.8]

> **SoT参照**: 定義のSource of Truthは `AGENTS.md [AV.8]`。

```yaml
根本認識:
  AIコーディングは開発速度を上げるが「見えない借金」を3種類生み出す
  コードを書く速度は上がったが、理解・思考コストが別の形で積み上がる
  放置するほど「借金の利子」が複利的に膨らむ構造

三大負債の定義:
  1.技術負債(Technical Debt):
    定義: 設計の妥協・低品質コードによる将来の修正コスト増大
    例: 短期開発促進→後から大きな手戻り発生
    対策: [AV]バイブコーディング対策 + [Q1.2]TDD + [P2.4]段階的修正開発

  2.理解負債(Comprehension Debt):
    定義: AIが生成したコードを開発者が理解しないまま取り込み、後から理解コストが膨らむ状態
    AIコーディング時代固有の新概念
    例: AIコード丸ごとコミット→修正時に誰も理解できない→ポチョムキン状態[AV.7]
    対策: [VF.1]証拠優先因果検証 + [AV.7]ポチョムキン理解防止 + [Phi1.6]深潜思考

  3.認知負債(Cognitive Debt):
    定義: AIに設計・実装を任せるほど、開発者自身がシステム全体を理解できなくなる問題
    コードではなく人間の頭の中に負債が蓄積する
    例: AI全依存→担当者退職でシステム全体がブラックボックス化
    対策: [Phi1.6]深潜思考原則 + [DS.3]組織知の循環 + [CT.3]言語化・具体化サイクル

連鎖リスク:
  技術負債の蓄積→修正難度上昇→理解負債の加速→認知負債の複利的増大
  (3つの負債は独立でなく相互強化する)
```

### 三大負債チェックリスト (コードレビュー時)

```
[ ] このコードを書いた人(またはAI)以外が説明できるか?
[ ] 変更理由を「なぜ」3回追跡できるか?
[ ] システム全体との依存関係を口頭で説明できるか?
[ ] 担当者が退職しても再現できる手順書があるか?
```

---

## ドキュメント命名規約 [D1.3]

> **SoT参照**: 定義のSource of Truthは `AGENTS.md [D1.3]`。

```yaml
原則: ソースコードファイルを除く全成果物のファイル名・フォルダ名は日本語に統一する
対象: HTML/XLSX/MD/TXT/PDF/PNG 等のドキュメント系・設計系・報告系ファイル
除外: *.py/*.ts/*.js/*.json/*.toml 等のソースコード系（英語維持可）
形式: 「<業務説明的名称>_<YYYY-MM-DD任意>」.拡張子
```

| 良い例 | 禁止例 |
|--------|--------|
| 画面設計書.html | SCREEN_DESIGN.html |
| アーキテクチャ設計書.html | ARCHITECT.html |
| テスト仕様書.html | TEST.html |
| 機能仕様書.html | SPEC.html |

禁止事項:
- アルファベット略語のみのファイル名
- 英語略語のみのファイル名 (README/SPEC/ARCH 等)
- 数字連番のみのファイル名

例外: `kanban_project.html` は統合ハブのシステム識別子のため維持

---

## 統合判断フレーム [PHIL.4]

> **SoT参照**: 定義のSource of Truthは `AGENTS.md [PHIL.4]`。

すべての提案・設計・実装・修正は以下7点を満たすこと:

```yaml
1. 因果: 苦しみ・課題の根本原因に届いているか
2. 義:   倫理・道理・人間尊重に反していないか
3. 利:   経済合理性・運用合理性・継続可能性があるか
4. 現場: 実データ・実コード・実ユーザーで検証可能か
5. 挑戦: 失敗を学習に変え、段階的に前進できるか
6. 喜び: 作る人・使う人・支える人の喜びを増やすか
7. 余裕: 個人・組織・社会に余裕と幸福を生むか
```

禁止される判断:
- 倫理を犠牲にした短期利益
- 現場を見ない机上設計
- エラーや失敗の隠蔽
- ユーザーや運用者に負荷を押し付ける設計
- 根本原因を放置する表面的対応
