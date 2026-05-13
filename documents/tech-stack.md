# AGENTS.md - 技術スタック仕様 [T1, T3, ENV]

> **SoT参照**: 定義のSource of Truthは `AGENTS.md [T1, T3]`。
> このファイルはdevrag RAG用実装パターン・補足コード例を収録。

## 基本環境制約 (定義: AGENTS.md [T1.1])

```yaml
OS:      Windows 10/11 ネイティブ (WSL禁止)
Shell:   CMD / PowerShell
Python:  3.11.x
Pkg:     uv専用 (pip禁止, conda禁止, poetry禁止)
DB:      DuckDB
Format:  Parquet (中間保存)
Encode:  UTF-8 (65001)
Batch:   Shift-JIS (chcp 932)
```

## uv仮想環境必須フロー [T1.2, ENV]

```python
from pathlib import Path
import subprocess

def ensure_uv_environment():
    """Python実行前に必ず呼び出す"""
    if not Path(".venv").exists():
        subprocess.run(["uv", "venv"], check=True)
    # Windows: .venv/Scripts/python.exe
    # Unix:    .venv/bin/python
```

起動スクリプト例 (`installer.bat`):
```batch
@echo off
chcp 65001 > nul
uv venv
call .venv\Scripts\activate
uv pip install -r requirements.txt
```

## コードスタイル [T1.3]

- PEP8準拠
- **typing モジュール使用禁止**
- インデント: スペース4個
- 完全形ファイル単位で提示 (省略コメント禁止)
- Unicode絵文字完全禁止 → `[OK]` `[ERROR]` `[WARNING]` `[INFO]` を使う

## 実行順序 [T1.4]

```
READ → DELETE → CREATE → READ → UPDATE
```
この順序を守ること。特にDELETE前にREADで現状確認。

## パフォーマンス設計 [T3, PERF]

```yaml
DB:        DuckDB (標準)
Format:    Parquet (中間保存)
Cache:     期限管理 + 自動クリーンアップ
大量データ: メモリマップファイル
並列:
  I/O集約: ThreadPoolExecutor (max=32)
  CPU集約: ProcessPoolExecutor (max=32)
  結果収集: as_completed
```

## ログ実装 [K1.1]

```python
# 必須タグ
print("[PROCESS_START] 処理名 開始")
print(f"[PROCESSING] {item_id} 処理中")
print(f"[STEP] ステップ名 実行")
print(f"[PROGRESS] {current}/{total}")
print(f"[SUCCESS] 完了 ({elapsed:.2f}秒)")
print(f"[FAILED] エラー: {error}")
print(f"[WARNING] 警告: {message}")
```

## DB排他制御 [DB_EXCL]

```yaml
原則:
  - プロセス単位DB接続分離
  - ポート番号ベースDBファイル分離
  - ファイルロック (fcntl.flock LOCK_EX|LOCK_NB)
  - 段階的フォールバック (設定のみ、データ補完禁止)
```

## Unicode/cp932 問題対策 [TS.1]

```yaml
症状: UnicodeEncodeError: 'cp932' codec can't encode character
解決:
  - 絵文字禁止
  - ASCII文字列のみ使用
  - ログ出力はASCIIタグのみ
代替表記: [OK] [ERROR] [WARNING] [INFO] [ANALYSIS]
```

---

## [PORT] 実装パターン (定義: AGENTS.md [PORT])

### Parquetエクスポートパターン (round-trip保証付き)
```python
import duckdb
import json
from pathlib import Path
from datetime import datetime, timezone

def export_to_parquet(conn: duckdb.DuckDBPyConnection, table: str, out_path: str) -> dict:
    """
    [PORT.2] round-trip保証付きParquetエクスポート
    メタデータ同梱: schema_version / exported_at / source_system / record_count
    """
    out = Path(out_path)
    row_count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.execute(f"COPY {table} TO '{out}' (FORMAT PARQUET, COMPRESSION SNAPPY)")
    meta = {
        "schema_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_system": table,
        "record_count": row_count,
        "format": "parquet",
        "compression": "snappy"
    }
    out.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SUCCESS] エクスポート完了: {out} ({row_count}件)")
    return meta

def import_from_parquet(conn: duckdb.DuckDBPyConnection, parquet_path: str, target_table: str) -> None:
    """
    [PORT.3] スキーマ検証 + 冪等性保証付きインポート
    冪等性: 同一データを2回実行しても副作用なし
    """
    path = Path(parquet_path)
    if not path.exists():
        raise FileNotFoundError(f"Parquetファイルが見つかりません: {path}")
    meta_path = path.with_suffix(".meta.json")
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        print(f"[INFO] schema_version={meta['schema_version']} record_count={meta['record_count']}")
    # 冪等性: INSERT OR IGNORE パターン
    conn.execute(f"""
        INSERT OR IGNORE INTO {target_table}
        SELECT * FROM read_parquet('{path}')
    """)
    print(f"[SUCCESS] インポート完了: {path} -> {target_table}")
```

### 設定ポータビリティパターン (.env + pyproject.toml)
```python
import os
from pathlib import Path

# [PORT.4] 環境変数で解決→絶対パスハードコード禁止
DB_PATH    = Path(os.environ.get("DB_PATH",    "data/local.duckdb"))
LOG_DIR    = Path(os.environ.get("LOG_DIR",    "logs"))
EXPORT_DIR = Path(os.environ.get("EXPORT_DIR", "exports"))

# 起動時に必須ディレクトリを作成
for d in (DB_PATH.parent, LOG_DIR, EXPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)
```

### round-tripテストパターン (PORT.2+PORT.3の自動検証)
```python
def test_parquet_round_trip(conn, table):
    """[PORT] export → import → 同一結果であることを自動検証"""
    original = conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchdf()
    meta = export_to_parquet(conn, table, "test_export.parquet")
    conn.execute(f"CREATE TABLE {table}_reimport AS SELECT * FROM read_parquet('test_export.parquet')")
    reimported = conn.execute(f"SELECT * FROM {table}_reimport ORDER BY 1").fetchdf()
    assert original.equals(reimported), "[FAILED] round-trip検証失敗: export/importで差分あり"
    assert meta["record_count"] == len(original), "[FAILED] レコード件数不一致"
    print("[SUCCESS] round-trip検証: 完全一致確認")
```

---

## 実行シェル方針 [SUPRA.1]

> **SoT参照**: 定義のSource of Truthは `AGENTS.md [SUPRA.1]`。

```yaml
基本方針:
  シェル:      Git Bash (全コマンド実行の標準)
  PowerShell:  最小限の補助用途のみ許可
               (Git Bash 起動確認 / 権限確認 / Windows固有設定のみ)
  WSL:         禁止 ([T1.1]より)

Git Bash が優先される理由:
  - Unix系コマンドとの互換性 (grep / find / sed 等)
  - パス区切り文字の統一 (/ のみ)
  - CAPDkAサイクルのスクリプト実行環境の統一

禁止:
  - WSL環境でのコマンド実行
  - OS固有パス区切り文字のハードコード (Path()で統一)
  - PowerShellのみで完結するスクリプト設計 (Git Bash互換性を保つ)
```

### Git Bash 確認パターン

```python
import subprocess

def verify_shell_environment():
    """Git Bash環境での実行を確認する [SUPRA.1]"""
    result = subprocess.run(
        ["bash", "--version"],
        capture_output=True, text=True
    )
    if "GNU bash" not in result.stdout:
        raise RuntimeError(
            "[ERROR] Git Bash環境が必要です。"
            "SUPRA.1: すべてのコマンド実行は Git Bash を使用すること。"
        )
    print("[OK] Git Bash環境確認済み")
```

## Mermaid活用マッピング [WBS.4] (定義: AGENTS.md [WBS.4])

```yaml
WBSデータ → flowchart LR:
  # タスク依存関係とクリティカルパス
  # style criticalNode fill:#ef4444 でクリティカルパス強調

機能関係 → graph TD:
  # ユーザーストーリーの階層構造

API/処理順 → sequenceDiagram:
  # サービス間通信フロー (フロントエンド-バックエンド-DB)

データ構造 → erDiagram:
  # エンティティ間リレーション

システム構成 → architecture-beta:
  # C4モデル相当のブロック図
  # サービス間依存関係を矢印で明示

人間検証必須:
  - クリティカルパスが正しいか
  - 依存関係に漏れはないか
  - AIが生成したMermaid図をそのまま採用禁止
```

---

## 外部発報オーケストレーター [N8N] (定義: AGENTS.md [N8N])

> **SoT参照**: 定義のSource of Truthは `AGENTS.md [N8N]`。

```yaml
原則: 外部発報系は特段の指定がない限り n8n を基本オーケストレーターとして使用する

n8n 基本情報:
  ライセンス: Apache 2.0 (商用利用OK / コピーレフトなし)
  展開方式:   セルフホスト推奨 (Docker / オンプレ)
  標準ポート: 5678
  ノード数:   400+ (Slack/Teams/LINE/SMTP/HTTP/S3 等)

外部発報系の定義:
  - メール送信 (SMTP / SendGrid / SES)
  - チャット通知 (Slack / Teams / Discord / LINE / Chatwork)
  - HTTP Webhook 送信 (外部システム連携)
  - スケジュール定期レポート配信
  - アラート・監視通知 (障害 / 閾値超過 / バッチ完了)

Secret管理:
  禁止: API Key / SMTP認証情報 / Webhook Secret をアプリコードに混入
  必須: n8n Credentials に集約し、ワークフロー内でのみ参照
```

### n8n 呼び出しパターン (アプリ側)

```python
import os
import httpx
import uuid

N8N_WEBHOOK_URL = os.environ["N8N_WEBHOOK_URL"]  # .env から取得、ハードコード禁止

def notify_via_n8n(event: str, payload: dict) -> None:
    """
    [N8N.3] n8n Webhook エンドポイントへイベントを POST する
    X-Idempotency-Key で重複送信を防止
    """
    run_id = str(uuid.uuid4())
    try:
        resp = httpx.post(
            N8N_WEBHOOK_URL,
            json={"event": event, **payload},
            headers={"X-Idempotency-Key": run_id},
            timeout=10,
        )
        resp.raise_for_status()
        print(f"[SUCCESS] n8n 発報完了: event={event} run_id={run_id}")
    except httpx.HTTPError as exc:
        # フェイルクローズ: 発報失敗はログに残し処理は継続
        print(f"[WARNING] n8n 発報失敗 (処理継続): {exc}")
```

### ワークフロー管理

```yaml
配置場所: n8n_workflows/ (gitignore に Credentials を含む .env は除外)
命名規約: <業務名>_<発報種別>_v<バージョン>.json
例:
  CIDLS_日次レポート_v1.json
  CIDLS_エラーアラート_v2.json
  CIDLS_バッチ完了通知_v1.json

git管理対象:   ワークフロー定義 .json (Secret除く)
git管理対象外: .env / n8n Credentials エクスポートファイル
```

### 品質ゲート [N8N.5]

```
リリース前必須確認:
  [ ] N8N_WEBHOOK_URL が環境変数から取得されている
  [ ] SMTP/API Key が n8n Credentials に格納済み
  [ ] n8n_workflows/ に .json 定義が保存済み
  [ ] X-Idempotency-Key 実装済み
  [ ] n8n 停止時の挙動が明示されている
```

