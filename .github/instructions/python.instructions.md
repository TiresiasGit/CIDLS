---
name: 'Python コーディング規約 (AGENTS.md準拠)'
description: 'Pythonファイル向けのコーディング規約'
applyTo: '**/*.py'
---

# Python コーディング規約

## 環境制約 [T1.1]
- Python 3.11.x 固定
- パッケージ管理: **uv専用** (pip, conda, poetry 禁止)
- UI: **Reflex** (Streamlit 禁止)
- OS: Windows 10/11 (WSL禁止)
- DB: DuckDB (SQLite/PostgreSQL/MySQL 非推奨)
- データ形式: Parquet (CSV は一時的な入出力のみ)

## uv仮想環境必須フロー [T1.2]
```python
from pathlib import Path
import subprocess

def ensure_uv_environment():
    """Python実行前に必ず実行"""
    if not Path(".venv").exists():
        subprocess.run(["uv", "venv"], check=True)
    # Windows: .venv/Scripts/python.exe
```

## コーディングスタイル [T1.3]
- PEP8準拠 (**typing モジュール使用禁止**)
- インデント: スペース4個
- エンコード: UTF-8 (バッチファイルのみ Shift-JIS)
- Unicode絵文字: **完全禁止** (cp932環境でUnicodeEncodeError発生)
  - 代替: `[OK]`, `[ERROR]`, `[WARNING]`, `[INFO]`, `[ANALYSIS]`
- 完全形ファイル単位で提示 (省略・省略コメント禁止)

## 実行順序 [T1.4]
```
READ → DELETE → CREATE → READ → UPDATE
```

## 禁止パターン [G1]
```python
# 禁止: フォールバック処理
def get_data():
    try:
        return fetch_real_data()
    except Exception:
        return generate_dummy_data()  # 絶対禁止

# 禁止: エラー握り潰し
try:
    process()
except Exception:
    pass  # 絶対禁止

# 禁止: else/defaultによる分類放棄
def classify(item):
    if item == "A":
        return "type_a"
    else:
        return "unknown"  # 絶対禁止 → ValueError を raise せよ
```

## 正しいパターン
```python
# OK: 明示的エラー
def get_data():
    return fetch_real_data()  # 失敗時はそのまま例外を伝播

# OK: 全分岐を明示列挙
VALID_CATEGORIES = {"finance", "engineering", "marketing"}
def classify(item):
    category = determine_category(item)
    if category not in VALID_CATEGORIES:
        raise ValueError(f"未知カテゴリ '{category}' を検出。分類設計を見直せ")
    return category
```

## パフォーマンス [T3.1]
- I/O集約: `ThreadPoolExecutor`
- CPU集約: `ProcessPoolExecutor`
- 最大並列: 32 (動的調整)
- キャッシュ: 期限管理 + 自動クリーンアップ必須

## ログ [K1.1]
```python
# 必須タグ
# [PROCESS_START] / [PROCESS_END]: 全体開始/終了
# [PROCESSING]: 各アイテム処理開始
# [STEP]: 処理内各ステップ
# [SUCCESS] / [FAILED]: 処理結果
# [PROGRESS]: 進捗(X/Y形式)
# [WARNING] / [ERROR]: 警告/エラー
```

## TDD必須 [Q1.2]
- カバレッジ: ユニット≥90%, 統合=全API/DB/モジュール
- Red(失敗テスト作成) → Green(最小実装) → Refactor(品質向上)
- モックデータ検証完了: **禁止** (ユーザー実行が最終検証)

## 差分切り分け原則 [DIFF]
コード変更・バグ修正・リファクタリングのすべてで適用必須:
```python
# Step1: Before記録
# grep -n "対象パターン" ファイル名 を実行してスナップショット

# Step2: 変更箇所を最小単位で特定
# [DIFF] 変更: 理由 というコメントで明示

# Step3: After記録 (同条件でgrep)

# Step4: 差分報告フォーマットで明示
# [DIFF] 変更ファイル:ファイルパス:行番号 | Before:<旧値> | After:<新値> | 理由:<Why1>

# Step5: 副作用チェック
# grep -rn "変更した概念" . --include="*.py" で波及を確認
```

禁止:
- 「全体的に修正した」という曖昧な変更理由
- Before確認なしの修正着手
- 差分報告なしの「修正完了」宣言

## ポータビリティ設計 [PORT]

```python
import os
from pathlib import Path
import json

# --- ポータビリティ必須パターン ---

# OK: 環境変数 + デフォルト値でポータブルに
DB_PATH = Path(os.environ.get("DB_PATH", "data/local.duckdb"))

# OK: Path()でOS非依存
config_path = Path("data") / "config.json"

# OK: スキーマ+メタデータ付きエクスポート
def export_with_meta(df, out_path, schema_version="1.0"):
    """Parquet出力と同時にschema_versionを保存"""
    out = Path(out_path)
    backup = out.with_suffix(".bak.parquet")
    if out.exists():
        out.rename(backup)  # READ -> BACKUP必須
    df.to_parquet(out, compression="snappy", index=False)
    meta = {
        "schema_version": schema_version,
        "record_count": len(df),
        "exported_at": __import__("datetime").datetime.now().isoformat(),
    }
    out.with_suffix(".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8"
    )

# OK: import時にスキーマ検証
def import_with_validate(path, required_cols):
    """import前に必須列と型をサーバーサイドで検証"""
    import duckdb
    conn = duckdb.connect()
    df = conn.execute(f"SELECT * FROM parquet_scan('{path}')").df()
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"[PORT] スキーマ不一致: 必須列なし {missing}")
    return df

# --- 禁止パターン ---
# DB_PATH = "C:/Users/specific_user/data.duckdb"  # 禁止: 絶対パス
# config = "data\\config.json"                    # 禁止: OS依存パス
# df.to_parquet("output.parquet")                  # 禁止: メタデータなし
```

禁止:
- 絶対パスのハードコード (Path() / os.environ で解決)
- OS固有パス区切り文字のハードコード (Path()で統一)
- スキーマ未定義のデータ出力 (受け取り側が型推測=禁止)
- import不能なexport (round-trip test必須)
- バックアップなしの上書き保存 (READ→BACKUP→UPDATE→VERIFYフロー)
