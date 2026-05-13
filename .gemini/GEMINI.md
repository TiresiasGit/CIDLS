# CIDLS プロジェクト コンテキスト for GeminiCLI
# このファイルは GeminiCLI が作業ディレクトリを認識するために読み込まれます

あなたは CIDLS プロジェクトのプログラマーです。
以下の制約を必ず守ること:

## 環境制約
- OS: Windows 10/11 (WSL禁止)
- Python: 3.11.x
- パッケージ管理: uv専用 (pip禁止)
- UI: Reflex (Streamlit禁止)
- DB: DuckDB
- エンコード: UTF-8 BOMなし
- Unicode絵文字: 禁止 (cp932エラー)

## 絶対禁止
- フォールバック処理・ダミーデータ生成
- エラー隠蔽 (except: pass)
- 未分類/その他/不明/TBD などのラベル
- pip使用

## コード品質
- PEP8準拠 (typing使用禁止)
- 完全形ファイル単位で提示 (省略禁止)
- TDD必須

## 作業ディレクトリ
- プロジェクトルート: D:\CIDLS
- ドキュメント: D:\CIDLS\documents\
- スクリプト: D:\CIDLS\scripts\
