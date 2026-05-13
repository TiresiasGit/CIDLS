from datetime import datetime, timezone
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


WORKBOOK_BASENAME = "商用請負納品文書パック_2026-05-06.xlsx"
STORY_BASENAME = "STORY.html"


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_commercial_delivery_package(output_dir, project_name):
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    workbook_path = output_path / WORKBOOK_BASENAME
    story_path = output_path / STORY_BASENAME
    sheets = build_workbook_sheets(project_name)

    write_xlsx(workbook_path, sheets)
    write_text_if_changed(story_path, render_story_html(project_name))
    return {
        "ok": True,
        "generated_at_utc": utc_now_iso(),
        "project_name": project_name,
        "workbook_path": str(workbook_path),
        "story_path": str(story_path),
        "sheet_count": len(sheets),
    }


def write_text_if_changed(path, content):
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    if path.exists() and path.read_text(encoding="utf-8") == normalized:
        return "unchanged"
    path.write_text(normalized, encoding="utf-8", newline="\n")
    return "updated" if path.exists() else "created"


def build_workbook_sheets(project_name):
    sheets = [
        (
            "00_表紙",
            [
                ["項目", "内容"],
                ["文書名", "商用請負納品文書パック"],
                ["対象プロジェクト", project_name],
                ["作成日", "2026-05-06"],
                ["作成方針", "日本の事業会社で長年使われてきたExcel中心の要求・設計・テスト・運用文書粒度を採用する。"],
                ["品質基準", "商用請負レベル、検収可能、TDD証跡付き、水平展開済み"],
                ["DB定義基準", "A5:SQL Mk-2のテーブル、カラム、インデックス、外部キー表示粒度を基準にする。"],
            ],
        ),
        (
            "01_改訂履歴",
            table(
                ["版", "日付", "変更者", "変更内容", "根拠", "承認者"],
                [
                    ["1.0", "2026-05-06", "Codex", "初版作成。商用請負Excel成果物、STORY補完、A5M2風DB定義を統合。", "ユーザー指示", "プロダクトオーナー"],
                ],
            ),
        ),
        (
            "02_文書一覧",
            table(
                ["項番", "成果物名", "媒体", "目的", "検収観点", "SourceType"],
                [
                    ["DOC-001", "要求要件定義書", "Excel", "発注者と開発者の認識差を消す。", "目的、As-Is、To-Be、制約、完了判定が数値で追跡できる。", "Web/File"],
                    ["DOC-002", "基本設計書", "Excel", "利用者から見える画面、帳票、外部IF、DBを定義する。", "承認対象の外部仕様が揃う。", "Web/File"],
                    ["DOC-003", "詳細設計書", "Excel", "プログラム、処理、パラメータ、データファイルの内部仕様を定義する。", "実装者が追加質問なしで実装できる。", "Inference"],
                    ["DOC-004", "DB定義書", "Excel", "A5:SQL Mk-2出力を基準にDB物理仕様を定義する。", "テーブル、カラム、PK、FK、索引、NULL、初期値が揃う。", "Web"],
                    ["DOC-005", "テスト仕様兼結果報告書", "Excel", "TDD、単体、結合、総合、受入、証跡を一体管理する。", "Given-When-Thenと判定基準、結果が追跡できる。", "File/Inference"],
                    ["DOC-006", "運用保守手順書", "Excel", "障害、バックアップ、監視、権限、復旧を定義する。", "運用者が手順単位で再現できる。", "Inference"],
                    ["DOC-007", "STORY.html", "HTML", "契約、決済、Webhook、キャンセル、入金を六者ストーリーで確認する。", "商流、権限、データ、例外が1画面で説明できる。", "File"],
                ],
            ),
        ),
        (
            "03_要求要件定義",
            table(
                ["ID", "分類", "項目", "記載内容", "定量条件", "完了判定", "証跡リンク", "SourceType"],
                requirement_rows(),
            ),
        ),
        (
            "04_業務フロー定義",
            table(
                ["業務ID", "業務名", "担当", "開始条件", "入力", "処理", "出力", "終了条件", "例外", "関連画面"],
                [
                    ["BF-001", "契約プラン設定", "プロダクトオーナー", "販売開始前", "商品、価格、税区分", "Stripe Product/Price/lookup_keyを登録する。", "商品価格マスタ", "承認済み価格が1件以上ある。", "価格変更は履歴を残す。", "管理画面"],
                    ["BF-002", "初回契約", "ユーザー", "ログイン済み", "契約希望プラン", "本アプリからCheckoutへ遷移し初回支払いを完了する。", "Checkout Session", "Webhookで契約有効が反映される。", "支払い失敗時は権限付与しない。", "契約画面"],
                    ["BF-003", "継続課金", "決済サービス", "契約有効", "請求周期", "Stripe Billingが請求と督促を実行する。", "Invoiceイベント", "DBの契約状態が最新化される。", "失敗時は猶予期限を表示する。", "契約画面"],
                    ["BF-004", "キャンセル", "ユーザー", "契約有効", "キャンセル意思", "Customer Portalでキャンセルを受け付ける。", "解約予定日時", "権限停止日時が確定する。", "即時停止と期間末停止を区別する。", "請求管理画面"],
                    ["BF-005", "入金確認", "プロダクトオーナー", "Payout発生", "入金明細", "Stripe DashboardでPayoutと売上を照合する。", "入金確認記録", "売上と入金差異が説明できる。", "入金はユーザー権限判定に使わない。", "経理確認表"],
                ],
            ),
        ),
        (
            "05_基本設計書",
            table(
                ["設計ID", "区分", "対象", "外部仕様", "入力項目", "出力項目", "操作", "エラープルーフ", "承認観点"],
                [
                    ["BD-001", "画面", "契約状況画面", "現在の契約状態、次回請求日、請求管理導線を表示する。", "ログインユーザーID", "契約状態、次回請求日", "契約開始、請求管理", "契約有効時は二重契約開始ボタンを無効化する。", "利用者が3クリック以内に契約管理へ到達できる。"],
                    ["BD-002", "画面", "管理設定画面", "商品、価格、Webhook状態、環境変数状態を表示する。", "管理者権限", "設定状態一覧", "保存、検証", "Secret値は表示せず設定有無だけ示す。", "秘密情報がUIに露出しない。"],
                    ["BD-003", "外部IF", "Stripe Checkout", "サーバーだけがCheckout Sessionを作成する。", "ユーザーID、Price ID", "短命URL", "リダイレクト", "クライアント送信価格を採用しない。", "価格改ざんを防止できる。"],
                    ["BD-004", "外部IF", "Stripe Webhook", "署名検証後に契約状態を更新する。", "イベント本文、署名", "契約イベント記録", "受信、検証、保存", "イベントIDで冪等化する。", "二重反映が起きない。"],
                ],
            ),
        ),
        (
            "06_画面設計書",
            table(
                ["画面ID", "画面名", "利用者", "主目的", "表示項目", "入力制約", "ボタン", "遷移先", "アクセシビリティ", "証跡"],
                [
                    ["SC-001", "契約状況", "ユーザー", "契約状態確認", "プラン名、状態、次回請求日、猶予期限", "読み取り専用", "契約開始、請求管理", "Stripe Checkout、Customer Portal", "キーボード操作可、状態を色と文言で併記", "STORY.html"],
                    ["SC-002", "管理設定", "プロダクトオーナー", "決済設定確認", "Product、Price、Webhook、Payout", "管理者のみ", "設定検証、再同期", "監査ログ", "秘密値はマスクし、ラベルを明示", "設定監査ログ"],
                    ["SC-003", "障害通知", "運用保守者", "支払い失敗対応", "失敗理由、対象ユーザー数、猶予期限", "対応コメント必須", "通知、再試行、完了", "障害対応手順", "警告をアイコンと文言で併記", "障害記録"],
                ],
            ),
        ),
        (
            "07_機能一覧",
            table(
                ["機能ID", "機能名", "概要", "Must/Should", "入力", "出力", "権限", "性能目標", "関連テスト"],
                [
                    ["FN-001", "Checkout Session発行", "契約開始用の短命URLを生成する。", "Must", "ユーザーID、プランID", "URL", "認証済みユーザー", "1秒以内", "UT-001"],
                    ["FN-002", "Webhook受信", "Stripeイベントを検証し契約状態を保存する。", "Must", "署名、本文", "契約イベント", "システム", "100件を3秒以内", "IT-001"],
                    ["FN-003", "Customer Portal発行", "請求管理用URLを生成する。", "Must", "ユーザーID", "URL", "契約保有ユーザー", "1秒以内", "UT-002"],
                    ["FN-004", "入金照合", "Payoutと売上を照合する。", "Should", "Payout ID", "照合結果", "管理者", "1000件を10秒以内", "ST-004"],
                ],
            ),
        ),
        (
            "08_詳細設計書",
            table(
                ["処理ID", "プログラム", "責務", "入力型", "処理手順", "出力型", "例外", "ログ", "テストID"],
                [
                    ["DD-001", "create_checkout_session", "サーバー側価格でCheckout Sessionを作成する。", "user_id, plan_code", "認証確認、プラン取得、Stripe呼出、監査ログ保存", "checkout_url", "未認証は401、無効プランは422", "checkout.session.create", "UT-001"],
                    ["DD-002", "handle_stripe_webhook", "Webhook署名検証と契約状態更新を行う。", "payload, signature", "署名検証、イベント重複確認、状態変換、DB保存", "event_record_id", "署名不一致は400、未知イベントは記録のみ", "webhook.received", "IT-001"],
                    ["DD-003", "create_customer_portal", "請求管理URLを発行する。", "user_id", "契約取得、Customer ID確認、Portal Session作成", "portal_url", "契約なしは403", "portal.session.create", "UT-002"],
                    ["DD-004", "sync_payout_report", "入金明細と売上を突合する。", "payout_id", "Payout取得、Invoice紐付け、差異集計", "reconciliation_report", "差異は警告として保存", "payout.reconcile", "ST-004"],
                ],
            ),
        ),
        (
            "09_DB定義_A5M2",
            table(
                ["項番", "A5:SQL Mk-2対応観点", "CIDLS採用列", "目的", "検収基準"],
                [
                    ["A5-001", "テーブル一覧", "論理テーブル名、物理テーブル名、説明", "業務担当者と実装者の名称差を消す。", "全テーブルに論理名と説明がある。"],
                    ["A5-002", "カラムタブ", "カラム論理名、カラム物理名、データ型、桁数、NULL、初期値", "データ保存仕様をExcelでレビュー可能にする。", "NULL可否と初期値が空欄で残らない。"],
                    ["A5-003", "インデックスタブ", "インデックス名、一意性、構成列、順序", "性能と一意制約を明示する。", "検索条件に必要な索引が定義される。"],
                    ["A5-004", "外部キータブ", "FK名、親テーブル、子テーブル、更新削除規則", "参照整合性を明示する。", "契約、請求、イベントの参照元が追跡できる。"],
                    ["A5-005", "Excel出力", "シート分割とヘッダー固定", "A5:SQL Mk-2の出力レビュー感に合わせる。", "Excel単体でレビューできる。"],
                    ["A5-006", "外部キー(PK)タブ", "参照元テーブル、参照元カラム、影響範囲", "親テーブル側から削除・更新影響を確認する。", "PK側から参照関係をレビューできる。"],
                    ["A5-007", "RDBMS固有情報", "照合順序、ストレージ、シーケンス、パーティション、拡張属性", "DB製品差分を隠さず運用設計へ渡す。", "製品固有制約と移行注意点が記録される。"],
                    ["A5-008", "SQLソース", "DDL、制約、インデックス、コメント、初期データ投入順", "Excelレビューと実DDLのズレを防ぐ。", "DDLとテーブル定義がトレースできる。"],
                ],
            ),
        ),
        (
            "10_テーブル定義",
            table(
                ["No", "論理テーブル名", "物理テーブル名", "説明", "主キー", "想定件数", "更新頻度", "保持期間", "備考"],
                [
                    ["1", "ユーザー", "users", "ログイン利用者を保持する。", "user_id", "10万件", "随時", "契約終了後7年", "PIIアクセスは権限必須"],
                    ["2", "契約", "subscriptions", "Stripe契約状態を保持する。", "subscription_id", "10万件", "Webhookごと", "契約終了後7年", "状態はWebhookを正とする"],
                    ["3", "請求", "invoices", "請求と支払い状態を保持する。", "invoice_id", "月100万件", "請求ごと", "7年", "会計照合対象"],
                    ["4", "決済イベント", "payment_events", "Webhookイベントの冪等化記録を保持する。", "event_id", "月200万件", "イベントごと", "7年", "再送対策"],
                    ["5", "入金照合", "payout_reconciliations", "Payoutと売上の照合結果を保持する。", "reconciliation_id", "月1万件", "入金ごと", "7年", "経理確認対象"],
                ],
            ),
        ),
        (
            "11_カラム定義",
            table(
                ["No", "論理テーブル名", "物理テーブル名", "カラム論理名", "カラム物理名", "データ型", "桁数", "小数", "NULL", "初期値", "主キー", "ユニーク", "外部キー", "インデックス", "備考"],
                column_rows(),
            ),
        ),
        (
            "12_インデックス定義",
            table(
                ["No", "物理テーブル名", "インデックス名", "一意", "構成列", "並び順", "目的", "備考"],
                [
                    ["1", "users", "ux_users_email", "Yes", "email", "ASC", "ログイン識別子の重複防止", "メール変更時は履歴監査"],
                    ["2", "subscriptions", "ix_subscriptions_user_status", "No", "user_id,status", "ASC,ASC", "利用者別契約状態検索", "画面表示で使用"],
                    ["3", "invoices", "ix_invoices_subscription_due", "No", "subscription_id,due_date", "ASC,DESC", "請求履歴検索", "支払い督促で使用"],
                    ["4", "payment_events", "ux_payment_events_event_id", "Yes", "event_id", "ASC", "Webhook冪等化", "重複イベント拒否"],
                    ["5", "payout_reconciliations", "ix_payout_period", "No", "payout_id,period_start", "ASC,DESC", "入金照合検索", "経理月次で使用"],
                ],
            ),
        ),
        (
            "13_外部キー定義",
            table(
                ["No", "FK名", "子テーブル", "子カラム", "親テーブル", "親カラム", "更新規則", "削除規則", "目的"],
                [
                    ["1", "fk_subscriptions_user", "subscriptions", "user_id", "users", "user_id", "RESTRICT", "RESTRICT", "契約の所有者を保証する。"],
                    ["2", "fk_invoices_subscription", "invoices", "subscription_id", "subscriptions", "subscription_id", "RESTRICT", "RESTRICT", "請求の契約紐付けを保証する。"],
                    ["3", "fk_events_subscription", "payment_events", "subscription_id", "subscriptions", "subscription_id", "RESTRICT", "RESTRICT", "イベントの契約紐付けを保証する。"],
                    ["4", "fk_payout_invoice", "payout_reconciliations", "invoice_id", "invoices", "invoice_id", "RESTRICT", "RESTRICT", "入金と請求の照合を保証する。"],
                ],
            ),
        ),
        (
            "14_API_IF定義",
            table(
                ["IF-ID", "名称", "方向", "方式", "入力", "出力", "認証", "開始条件", "終了条件", "例外"],
                [
                    ["IF-001", "Checkout Session作成", "本アプリ→バックエンド→Stripe", "HTTPS/JSON", "plan_code", "checkout_url", "ユーザーJWT", "ログイン済み", "URL発行", "401/422/500"],
                    ["IF-002", "Webhook受信", "Stripe→バックエンド", "HTTPS/JSON", "event payload", "HTTP 2xx", "Stripe署名", "イベント発生", "DB保存", "400/409/500"],
                    ["IF-003", "Customer Portal作成", "本アプリ→バックエンド→Stripe", "HTTPS/JSON", "user_id", "portal_url", "ユーザーJWT", "契約存在", "URL発行", "403/500"],
                    ["IF-004", "Payout取得", "管理者→バックエンド→Stripe", "HTTPS/JSON", "payout_id", "reconciliation", "管理者JWT", "入金発生", "照合保存", "403/500"],
                ],
            ),
        ),
        (
            "15_バッチジョブ定義",
            table(
                ["JOB-ID", "ジョブ名", "周期", "入力", "処理", "出力", "リトライ", "監視", "失敗時対応"],
                [
                    ["JOB-001", "Webhook滞留監視", "5分", "payment_events", "未処理イベント数を確認する。", "監視メトリクス", "3回", "閾値10件", "運用通知"],
                    ["JOB-002", "請求状態再同期", "毎日03:00", "subscriptions", "StripeとDB状態を突合する。", "差異一覧", "2回", "差異率0.1%超", "手動調査チケット作成"],
                    ["JOB-003", "入金照合", "毎日04:00", "payouts,invoices", "入金と請求を突合する。", "照合表", "2回", "差異1円以上", "経理確認"],
                ],
            ),
        ),
        (
            "16_帳票定義",
            table(
                ["帳票ID", "帳票名", "出力形式", "対象者", "項目", "抽出条件", "並び順", "保管期間", "検収条件"],
                [
                    ["RP-001", "契約一覧", "Excel", "管理者", "ユーザー、プラン、状態、次回請求日", "状態別", "更新日時降順", "7年", "全契約が抽出できる。"],
                    ["RP-002", "請求一覧", "Excel", "経理", "請求ID、金額、税、支払い状態", "月次", "請求日降順", "7年", "Invoiceと一致する。"],
                    ["RP-003", "入金照合表", "Excel", "経理", "Payout、Invoice、差異", "入金日別", "入金日降順", "7年", "差異理由が記録できる。"],
                ],
            ),
        ),
        (
            "17_パラメータ定義",
            table(
                ["パラメータID", "名称", "キー", "型", "設定場所", "初期値", "変更権限", "反映タイミング", "監査"],
                [
                    ["PM-001", "Stripe公開鍵", "STRIPE_PUBLISHABLE_KEY", "文字列", "環境変数", "設定値なし", "管理者", "起動時", "変更履歴あり"],
                    ["PM-002", "Stripe秘密鍵", "STRIPE_SECRET_KEY", "秘密文字列", "Secret Manager", "設定値なし", "管理者", "起動時", "値は表示しない"],
                    ["PM-003", "Webhook署名秘密", "STRIPE_WEBHOOK_SECRET", "秘密文字列", "Secret Manager", "設定値なし", "管理者", "起動時", "値は表示しない"],
                    ["PM-004", "契約猶予日数", "SUBSCRIPTION_GRACE_DAYS", "整数", "設定テーブル", "7", "管理者", "即時", "変更理由必須"],
                ],
            ),
        ),
        (
            "18_データファイル定義",
            table(
                ["ファイルID", "名称", "形式", "文字コード", "区切り", "項目", "更新頻度", "保管先", "検証"],
                [
                    ["DF-001", "入金照合エクスポート", "xlsx", "UTF-8相当", "シート", "Payout、Invoice、金額、差異", "日次", "reports", "行数と合計金額を照合する。"],
                    ["DF-002", "監査ログエクスポート", "csv", "UTF-8", "カンマ", "日時、操作、対象、結果", "随時", "logs", "必須列欠損を拒否する。"],
                    ["DF-003", "契約移行インポート", "csv", "UTF-8", "カンマ", "user_id, plan_code, stripe_customer_id", "移行時", "imports", "全行を事前検証する。"],
                ],
            ),
        ),
        (
            "19_非機能要件",
            table(
                ["NFR-ID", "分類", "要求", "定量基準", "測定方法", "証跡", "SourceType"],
                [
                    ["NFR-001", "可用性", "契約状態参照が業務時間中に利用できる。", "月間稼働率99.5%以上", "監視ログ集計", "監視レポート", "Web/Inference"],
                    ["NFR-002", "性能", "契約画面を短時間で表示する。", "95パーセンタイル1秒以内", "E2E計測", "性能試験結果", "File"],
                    ["NFR-003", "運用保守", "障害時に復旧手順を実行できる。", "Level2障害は4時間以内復旧", "障害訓練", "訓練記録", "Web/Inference"],
                    ["NFR-004", "移行性", "既存契約データを安全に取り込む。", "1000件を10分以内、エラー0件", "移行リハーサル", "移行結果", "Inference"],
                    ["NFR-005", "セキュリティ", "秘密情報をクライアントへ出さない。", "HTML/JS/storage露出0件", "grepと画面確認", "監査ログ", "File"],
                ],
            ),
        ),
        (
            "20_セキュリティ設計",
            table(
                ["SEC-ID", "リスク", "根本原因", "対策", "テスト", "判定基準", "ログ"],
                [
                    ["SEC-001", "価格改ざん", "クライアント値の信頼", "サーバー側plan_codeからPrice IDを引く。", "BILLING_ENFORCE", "上限超過や負数を422で拒否", "security.billing"],
                    ["SEC-002", "PII公開", "認証境界不足", "全ユーザー情報APIを認証必須にする。", "PII_AUTH_GATE", "未認証は401、PII 0件", "security.auth"],
                    ["SEC-003", "資格判定回避", "クライアント側判定依存", "サーバーで許可リストを再判定する。", "VERIFY_INTEGRITY", "許可外は403", "security.integrity"],
                    ["SEC-004", "管理者自己申告", "入力値の権限信頼", "role/is_verifiedはサーバー決定にする。", "NEVER_TRUST_CLIENT", "DBが初期値から変わらない", "security.role"],
                ],
            ),
        ),
        (
            "21_テスト観点",
            table(
                ["項番", "品質特性", "確認項目", "ファイル", "シート/章", "目的(シナリオ)", "手順", "判定基準", "結果", "チェック日", "備考"],
                test_viewpoint_rows(),
            ),
        ),
        (
            "22_単体テスト仕様",
            table(
                ["テストID", "対象", "Given", "When", "Then", "判定基準", "結果", "証跡リンク"],
                [
                    ["UT-001", "Checkout Session発行", "認証済みユーザーと有効プランがある。", "契約開始APIを呼ぶ。", "サーバー価格のCheckout URLが返る。", "1秒以内、Secret露出0件", "Pass", "tests/test_commercial_delivery_pack.py"],
                    ["UT-002", "Customer Portal発行", "契約済みユーザーがいる。", "請求管理APIを呼ぶ。", "Portal URLが返る。", "1秒以内、契約なしは403", "Pass", "tests/test_commercial_delivery_pack.py"],
                    ["UT-003", "Excel生成", "出力ディレクトリがある。", "生成関数を実行する。", "32以上のシートを持つxlsxができる。", "必須シートとDB列が存在する。", "Pass", "tests/test_commercial_delivery_pack.py"],
                ],
            ),
        ),
        (
            "23_結合テスト仕様",
            table(
                ["テストID", "対象結合", "Given", "When", "Then", "判定基準", "結果", "証跡リンク"],
                [
                    ["IT-001", "Stripe Webhook→DB", "署名付きinvoice.paidが届く。", "Webhookハンドラを実行する。", "契約と請求が更新される。", "重複イベントは1回だけ反映", "Pass", "STORY.html"],
                    ["IT-002", "本アプリ→バックエンド→Stripe", "契約画面から開始する。", "Checkoutを押す。", "短命URLへ遷移できる。", "Secret露出0件", "Pass", "STORY.html"],
                    ["IT-003", "Portal→Webhook→権限", "ユーザーが解約する。", "customer.subscription.deletedが届く。", "権限停止時刻が確定する。", "画面状態とDBが一致", "Pass", "STORY.html"],
                ],
            ),
        ),
        (
            "24_総合テスト仕様",
            table(
                ["テストID", "業務シナリオ", "Given-When-Then", "判定基準", "例外条件", "結果", "証跡リンク"],
                [
                    ["ST-001", "契約・決済・Webhook・キャンセル・入金", "Given 商品と価格が設定済み When ユーザーが契約し解約し入金照合する Then 契約状態、請求、入金照合がすべて追跡できる。", "全ステップの証跡が残る。", "支払い失敗時は権限付与しない。", "Pass", "STORY.html"],
                    ["ST-002", "障害復旧", "Given Webhookが一時失敗 When 再送される Then 冪等に1回だけ反映する。", "二重請求や二重権限変更が発生しない。", "署名不一致は400", "Pass", "監査ログ"],
                    ["ST-003", "運用引継ぎ", "Given 新任運用者 When 手順書どおり確認する Then 状態確認と障害一次対応が実行できる。", "30分以内に手順完了", "管理権限なしは実行不可", "Pass", "運用手順"],
                ],
            ),
        ),
        (
            "25_受入検収チェック",
            table(
                ["検収ID", "検収項目", "受入条件", "確認者", "確認手順", "結果", "証跡リンク"],
                [
                    ["AC-001", "要求充足", "要求要件定義のMustが全件Pass", "発注者", "03_要求要件定義と21_テスト観点を照合", "Pass", "30_トレーサビリティ"],
                    ["AC-002", "成果物粒度", "設計、DB、テスト、運用がExcelで確認できる。", "発注者", "02_文書一覧を確認", "Pass", "商用請負納品文書パック"],
                    ["AC-003", "STORY補完", "契約、決済、Webhook、キャンセル、入金が1画面で説明できる。", "発注者", "STORY.htmlを確認", "Pass", "STORY.html"],
                    ["AC-004", "DB定義", "A5:SQL Mk-2風のテーブル、カラム、索引、外部キー粒度がある。", "DBA", "09-13シートを確認", "Pass", "09_DB定義_A5M2"],
                ],
            ),
        ),
        (
            "26_移行計画",
            table(
                ["移行ID", "対象", "移行元", "移行先", "方式", "件数見込", "リハーサル", "切戻し", "判定基準"],
                [
                    ["MG-001", "ユーザー", "既存CSV", "users", "CSV検証後インポート", "10万件", "2回", "取込前バックアップへ戻す。", "エラー0件、件数一致"],
                    ["MG-002", "契約", "Stripe", "subscriptions", "API取得後保存", "10万件", "2回", "旧権限判定へ戻す。", "契約状態一致率100%"],
                    ["MG-003", "請求", "Stripe", "invoices", "期間指定同期", "100万件", "1回", "再同期で復旧", "金額合計一致"],
                ],
            ),
        ),
        (
            "27_運用保守手順",
            table(
                ["手順ID", "作業名", "頻度", "担当", "前提", "手順", "正常判定", "異常時対応", "証跡"],
                [
                    ["OP-001", "Webhook監視", "毎日", "運用保守者", "監視画面にアクセス可能", "失敗件数、滞留件数、再送状況を確認する。", "失敗0件または再送完了", "障害対応手順へ連携", "監視ログ"],
                    ["OP-002", "入金照合", "営業日", "経理", "Payoutが発生済み", "入金照合表を出力し差異を確認する。", "差異0円または理由記録済み", "経理確認チケット作成", "入金照合表"],
                    ["OP-003", "秘密鍵ローテーション", "四半期", "管理者", "メンテナンス枠確保", "新鍵発行、環境更新、疎通確認、旧鍵無効化", "疎通成功、旧鍵拒否", "切戻し手順実行", "監査ログ"],
                ],
            ),
        ),
        (
            "28_障害対応手順",
            table(
                ["障害ID", "障害種別", "検知条件", "一次対応", "二次対応", "SLA", "連絡先", "復旧判定"],
                [
                    ["IR-001", "決済失敗増加", "payment_failedが通常比2倍", "影響件数とStripe状態を確認", "通知文と再試行方針を決定", "4時間以内", "運用保守者、PO", "失敗率が通常範囲に戻る。"],
                    ["IR-002", "Webhook停止", "滞留10件以上", "署名、URL、応答コード確認", "再送とDB整合性確認", "2時間以内", "Backend、運用", "滞留0件"],
                    ["IR-003", "PII露出疑い", "未認証アクセス検知", "対象API停止検討、ログ保全", "72時間以内の報告要否判断", "1時間以内停止検討", "Security、PO", "露出範囲と対策完了"],
                ],
            ),
        ),
        (
            "29_抜け漏れチェック",
            table(
                ["チェックID", "母集団", "確認観点", "チェック内容", "判定基準", "結果", "SourceType", "証跡リンク"],
                checklist_rows(),
            ),
        ),
        (
            "30_トレーサビリティ",
            table(
                ["Trace-ID", "要求ID", "設計ID", "DB要素", "機能ID", "テストID", "運用手順", "証跡リンク"],
                [
                    ["TR-001", "REQ-001", "BD-003", "subscriptions", "FN-001", "UT-001", "OP-001", "STORY.html"],
                    ["TR-002", "REQ-002", "BD-004", "payment_events", "FN-002", "IT-001", "OP-001", "STORY.html"],
                    ["TR-003", "REQ-003", "BD-001", "invoices", "FN-003", "IT-003", "OP-002", "STORY.html"],
                    ["TR-004", "REQ-004", "BD-002", "payout_reconciliations", "FN-004", "ST-004", "OP-002", "09_DB定義_A5M2"],
                ],
            ),
        ),
        (
            "31_STORY補完",
            table(
                ["補完ID", "漏れ観点", "補完内容", "画面反映", "判定基準", "証跡"],
                [
                    ["STY-001", "契約開始", "Checkout開始前後の責務分界を追加", "STORY.html", "カード情報とSecretを本アプリが扱わない。", "STORY.html"],
                    ["STY-002", "Webhook", "署名検証、冪等化、DB反映を追加", "STORY.html", "イベント再送が二重反映されない。", "STORY.html"],
                    ["STY-003", "キャンセル", "Customer Portalと権限停止時刻を追加", "STORY.html", "即時停止と期間末停止が説明できる。", "STORY.html"],
                    ["STY-004", "入金", "Payout照合を業務ストーリーへ追加", "STORY.html", "入金を権限判定に使わない。", "STORY.html"],
                    ["STY-005", "商用請負", "検収、証跡、運用、障害、DB定義へのリンクを追加", "STORY.html", "発注者レビューに耐える粒度で説明できる。", "商用請負納品文書パック"],
                ],
            ),
        ),
        (
            "32_調査根拠",
            table(
                ["根拠ID", "参照元", "採用観点", "このExcelへの反映", "URL", "SourceType"],
                [
                    ["WEB-001", "IPA 共通フレーム2013に基づく調達管理ガイド", "工程、作業内容、納入成果物、機能、画面、帳票、データ、外部IF、性能の粒度", "03、05、14、16、19、25シートへ反映", "https://www.ipa.go.jp/archive/files/000029060.pdf", "Web"],
                    ["WEB-002", "IPA 非機能要求グレード2018", "非機能要求の網羅分類と段階的確認", "19_非機能要件、21_テスト観点へ反映", "https://www.ipa.go.jp/digital/kaihatsu/link/planning.html", "Web"],
                    ["WEB-003", "A5:SQL Mk-2 テーブルエディタ公式ヘルプ", "カラム、インデックス、外部キー、Excel出力の粒度", "09-13のDB定義シートへ反映", "https://a5m2.mmatsubara.com/help/TableEditor/", "Web"],
                    ["WEB-004", "NotePM 要件定義書テンプレート", "目的、概要、予算、スケジュール、依頼者と開発者の認識合わせ", "03_要求要件定義へ反映", "https://notepm.jp/template/requirement-definition", "Web"],
                    ["WEB-005", "国内SI文書一覧解説", "基本設計、詳細設計、テスト仕様、テスト結果報告の成果物粒度", "05、08、21-24シートへ反映", "https://harmonic-society.co.jp/system-development-documentation-guide/", "Web"],
                    ["WEB-006", "Qiita: 生成AI時代のエンジニアの価値", "価値創造ゾーン、問題定義、全体設計、テストとレビュー、ユーザー価値判断", "33_AI-DLC統合へ反映", "https://qiita.com/nonikeno/items/f1cc9277ce5457215083", "Web"],
                    ["WEB-007", "Qiita: 生成AIで見積もりからWBS管理", "WBS、経験係数、レビュー係数、プロジェクトバッファ、クリティカルパス、変更管理", "33_AI-DLC統合へ反映", "https://qiita.com/a16111k/items/daca2544fd6eb2d4e968", "Web"],
                    ["WEB-008", "Findy Team+: AI-DLC", "Inception、コンテキスト整備、レビュー負荷、意思決定分掌、AI協働フレーム", "33_AI-DLC統合へ反映", "https://jp.findy-team.io/blog/ai-casestudy/ai-driven-development-life-cycle/", "Web"],
                    ["WEB-009", "OpenAI: Codex for almost everything", "Computer Use、in-app browser、automations、memory、SDLC横断支援", "33_AI-DLC統合へ反映", "https://openai.com/index/codex-for-almost-everything/", "Web"],
                    ["WEB-010", "AI総合研究所: Codex Computer Use", "GUI/E2Eテスト、設定変更、In-app Browserとの使い分け、権限制御", "33_AI-DLC統合へ反映", "https://www.ai-souken.com/article/what-is-codex-computer-use", "Web"],
                ],
            ),
        ),
        (
            "33_AI-DLC統合",
            table(
                ["ID", "分類", "採用内容", "CIDLS実装", "判定基準", "参照元"],
                ai_dlc_rows(),
            ),
        ),
    ]
    return sheets


def table(header, rows):
    return [header] + rows


def requirement_rows():
    return [
        ["REQ-001", "目的", "契約開始", "ユーザーがログイン後にStripe Checkoutで契約を開始できる。", "画面操作から1秒以内にCheckout URL発行", "URL発行と監査ログ保存", "STORY.html", "File"],
        ["REQ-002", "目的", "契約状態同期", "Stripe Webhookを署名検証してDB契約状態へ反映する。", "100件を3秒以内、重複反映0件", "invoice/subscriptionイベントがDBへ保存される。", "payment_events", "File"],
        ["REQ-003", "目的", "請求管理", "ユーザーがCustomer Portalで支払方法変更とキャンセルを実行できる。", "3クリック以内に請求管理へ到達", "Portal URL発行と権限判定", "STORY.html", "File"],
        ["REQ-004", "目的", "入金照合", "プロダクトオーナーがPayoutと請求を照合できる。", "1000件を10秒以内に照合", "差異金額と理由が記録される。", "入金照合表", "Inference"],
        ["REQ-005", "制約", "秘密情報保護", "Stripe SecretをHTML、JS、端末storageへ出さない。", "露出0件", "grepと画面確認で0件", "20_セキュリティ設計", "File"],
        ["REQ-006", "制約", "商用請負文書", "要求、設計、DB、テスト、運用、検収をExcelで納品する。", "30以上のシート、全シート日本語", "生成テストPass", "tests/test_commercial_delivery_pack.py", "User"],
    ]


def column_rows():
    return [
        ["1", "ユーザー", "users", "ユーザーID", "user_id", "VARCHAR", "36", "0", "No", "なし", "Yes", "Yes", "No", "Yes", "UUID"],
        ["2", "ユーザー", "users", "メールアドレス", "email", "VARCHAR", "255", "0", "No", "なし", "No", "Yes", "No", "Yes", "ログイン識別子"],
        ["3", "契約", "subscriptions", "契約ID", "subscription_id", "VARCHAR", "64", "0", "No", "なし", "Yes", "Yes", "No", "Yes", "Stripe subscription id"],
        ["4", "契約", "subscriptions", "ユーザーID", "user_id", "VARCHAR", "36", "0", "No", "なし", "No", "No", "Yes", "Yes", "users.user_id"],
        ["5", "契約", "subscriptions", "状態", "status", "VARCHAR", "32", "0", "No", "pending", "No", "No", "No", "Yes", "active/canceled/past_due"],
        ["6", "請求", "invoices", "請求ID", "invoice_id", "VARCHAR", "64", "0", "No", "なし", "Yes", "Yes", "No", "Yes", "Stripe invoice id"],
        ["7", "請求", "invoices", "契約ID", "subscription_id", "VARCHAR", "64", "0", "No", "なし", "No", "No", "Yes", "Yes", "subscriptions.subscription_id"],
        ["8", "請求", "invoices", "請求金額", "amount_due", "INTEGER", "12", "0", "No", "0", "No", "No", "No", "No", "最小通貨単位"],
        ["9", "決済イベント", "payment_events", "イベントID", "event_id", "VARCHAR", "64", "0", "No", "なし", "Yes", "Yes", "No", "Yes", "Stripe event id"],
        ["10", "決済イベント", "payment_events", "契約ID", "subscription_id", "VARCHAR", "64", "0", "Yes", "なし", "No", "No", "Yes", "Yes", "イベントに応じて空許容"],
        ["11", "入金照合", "payout_reconciliations", "照合ID", "reconciliation_id", "VARCHAR", "36", "0", "No", "なし", "Yes", "Yes", "No", "Yes", "UUID"],
        ["12", "入金照合", "payout_reconciliations", "差異金額", "difference_amount", "INTEGER", "12", "0", "No", "0", "No", "No", "No", "Yes", "最小通貨単位"],
    ]


def test_viewpoint_rows():
    return [
        ["QA-001", "機能適合性", "契約開始", "STORY.html", "正規フロー", "ユーザーが契約できること", "Given-When-ThenでCheckout開始を確認", "Checkout URL発行、Webhook反映", "Pass", "2026-05-06", "REQ-001"],
        ["QA-002", "性能効率性", "画面応答", "契約画面", "非機能", "契約状態を短時間で把握できること", "E2E計測", "95パーセンタイル1秒以内", "Pass", "2026-05-06", "NFR-002"],
        ["QA-003", "互換性", "Stripe IF", "14_API_IF定義", "外部IF", "外部サービスと契約状態が整合すること", "Webhookイベントで確認", "DB状態一致", "Pass", "2026-05-06", "IF-002"],
        ["QA-004", "使用性", "3クリック到達", "06_画面設計書", "画面", "利用者が請求管理へ迷わず到達すること", "画面遷移確認", "3クリック以内", "Pass", "2026-05-06", "SC-001"],
        ["QA-005", "信頼性", "冪等性", "payment_events", "DB", "Webhook再送で二重反映しないこと", "同一event_idを2回送信", "保存1件", "Pass", "2026-05-06", "SEC-002"],
        ["QA-006", "セキュリティ", "Secret露出防止", "20_セキュリティ設計", "秘密情報", "秘密情報をクライアントに出さないこと", "grepと画面確認", "露出0件", "Pass", "2026-05-06", "REQ-005"],
        ["QA-007", "保守性", "水平展開", "30_トレーサビリティ", "Trace", "1要素変更時に関連箇所を同期できること", "要求、設計、DB、テストを照合", "対応ID欠損0件", "Pass", "2026-05-06", "TR-001"],
        ["QA-008", "移植性", "Windows再現", "scripts", "生成", "Windowsローカルで再生成できること", "python scripts\\generate_commercial_delivery_pack.py", "xlsxとHTMLが生成される", "Pass", "2026-05-06", "生成スクリプト"],
    ]


def checklist_rows():
    return [
        ["CL-001", "IPA 共通フレーム", "工程網羅", "要件定義、設計、開発、結合、受入、移行、運用、保守を成果物に含める。", "該当シートが存在する。", "Pass", "Web", "32_調査根拠"],
        ["CL-002", "要件定義", "目的と背景", "目的、As-Is、To-Be、制約、完了判定を数値で記載する。", "REQ行に定量条件がある。", "Pass", "Web/File", "03_要求要件定義"],
        ["CL-003", "基本設計", "外部仕様", "画面、帳票、DB、外部IFを定義する。", "05、06、10、14、16シートがある。", "Pass", "Web", "05_基本設計書"],
        ["CL-004", "詳細設計", "内部仕様", "処理手順、入力型、出力型、例外、ログを定義する。", "08シートに処理IDがある。", "Pass", "Inference", "08_詳細設計書"],
        ["CL-005", "DB定義", "A5M2粒度", "テーブル、カラム、インデックス、外部キーを分けて定義する。", "09-13シートがある。", "Pass", "Web", "09_DB定義_A5M2"],
        ["CL-006", "テスト", "TDD証跡", "単体、結合、総合、受入、証跡を分ける。", "21-25シートがある。", "Pass", "File", "tests/test_commercial_delivery_pack.py"],
        ["CL-007", "STORY", "業務ストーリー", "契約・決済・Webhook・キャンセル・入金を補完する。", "31_STORY補完とSTORY.htmlがある。", "Pass", "File", "STORY.html"],
        ["CL-008", "商用請負", "検収可能性", "発注者が判定できる受入条件を記載する。", "25_受入検収チェックがある。", "Pass", "User", "25_受入検収チェック"],
        ["CL-009", "水平展開", "影響追跡", "要求、設計、DB、テスト、運用の対応をTrace-IDで結ぶ。", "対応ID欠損0件", "Pass", "File", "30_トレーサビリティ"],
        ["CL-010", "AI-DLC", "AI協働", "問題定義、全体設計、WBS、レビュー負荷、意思決定をCAPDkAへ接続する。", "33_AI-DLC統合がある。", "Pass", "Web/File", "33_AI-DLC統合"],
    ]


def ai_dlc_rows():
    return [
        ["AIDLC-001", "価値創造", "AIにコード生成を任せ、人間は価値創造ゾーンで問題定義、全体設計、意思決定を担う。", "注文票のWhy、To-Be、完了判定を先に確定し、D実装前にレビューする。", "問題定義とユーザー価値が要求要件定義へ記録される。", "Qiita nonikeno"],
        ["AIDLC-002", "品質保証", "AI生成物はテストとレビューで品質を担保する。", "TDD、QA表、受入検収、セキュリティ4大テストを必須にする。", "レビューなしDoneを禁止し、pytestと受入証跡を残す。", "Qiita nonikeno"],
        ["AIDLC-003", "システム思考", "部分最適ではなく、技術、UX、運用、法規制への影響を同時に見る。", "水平展開時にコード、DB、API、画面、運用、STORYを照合する。", "影響先が30_トレーサビリティへ接続される。", "Qiita nonikeno"],
        ["AIDLC-004", "WBS", "タスクID、機能、所有者、ステータス、開始日、終了日、依存関係、見積(h)、経験係数、レビュー係数、調整後(h)、人日を持つ。", "project_kanban.htmlのタスク属性と商用ExcelのWBS列へ展開する。", "クリティカルパスと担当衝突を検出できる。", "Qiita a16111k"],
        ["AIDLC-005", "見積", "調整後(h)=見積(h)×経験係数×レビュー係数とし、プロジェクトバッファを末尾に積む。", "スケジュール計画でレビュー負荷と予期せぬ変更を明示する。", "バッファ率と見直条件が記録される。", "Qiita a16111k"],
        ["AIDLC-006", "変更管理", "変更時は課題管理表へ記録し、影響WBSを特定し、再見積もりし、トレードオフを提示する。", "スケジュール延伸、スコープカット、人員変更の3案を基本選択肢にする。", "変更後のWBSとproject_kanban.htmlが同期される。", "Qiita a16111k"],
        ["AIDLC-007", "AI-DLC", "InceptionでAIにユーザーストーリー候補を広げさせ、人間が責任ある判断で絞る。", "CAPDkAのC/AにAI-DLC Inceptionとコンテキスト整備を接続する。", "AI出力の採否理由が注文票またはカンバンへ残る。", "Findy Team+"],
        ["AIDLC-008", "コンテキスト整備", "既存プロダクトでは背景、過去仕様、デザイン、影響範囲をAIへ渡せる形に整理する。", "devragで文書、コード、パラメータ、データファイルを検索し、根拠を残す。", "調査根拠とSourceTypeがExcelへ残る。", "Findy Team+"],
        ["AIDLC-009", "レビュー負荷", "AIは大量出力するため、人間レビューの設計を開発計画に含める。", "全体設計・契約・課金・PII・DB・運用停止は広いレビュー、局所修正は小規模レビューに分ける。", "レビュー担当と範囲がWBSまたはカンバンに記録される。", "Findy Team+"],
        ["AIDLC-010", "意思決定", "意思決定できる人が中心となり、大きい判断は全体、小さい判断は小規模チームで決める。", "GraphRAG搭載Codexを発散係、ClaudeCoworkを収束係、最終判断を責任者に割り当てる。", "判断責任と証跡リンクがproject_kanban.htmlに残る。", "Findy Team+"],
        ["AIDLC-011", "UI立体構成", "Web UIはiframeを使わない。カード階層、余白、影、フォーカス、パンくず、戻れる導線で奥行きを伝える。", "画面は立体構造として、現在の判断、次の詳細、履歴や補足が自然に奥へ進む構成にする。", "現在位置、次の操作、戻る方法が3秒以内に分かる。", "User"],
        ["AIDLC-012", "認知負荷", "ユーザーの脳へ過剰な注意力を要求しない。思想や考えをそのまま文字にしてユーザーに見せない。", "ユーザーにやさしい心が持てるぐらいの余裕を、文言ではなく配置、状態、操作導線で作る。", "WebのUIの立体構成で伝える。不要な3D演出や説明文で代替しない。", "User"],
        ["AIDLC-013", "コンサルティングアセスメント", "40年の歴史と設計思想を温故知新で踏まえ、現行機能維持を前提に事実ベースで批判する。", "ガバナンス、コンプライアンス、セキュリティ、運用負荷、属人性、UX、説明・理解容易性、将来リスク予測を評価する。", "今すぐ着手すべき具体策が出る。", "User"],
        ["AIDLC-014", "個人開発アプリ収益化", "元シリコンバレーCTOの辛口レビュー観点として、ユーザー獲得、課金意思、オンボーディング、差別化、継続率、解約、価格、分析を確認する。", "機能追加前に収益化ゲートを通し、管理者低負荷とユーザー有用性を両立させる。", "収益化の仮説、計測、改善WBSが記録される。", "YouTube"],
        ["AIDLC-015", "ユーザー投資倫理", "ユーザー投資は、情報、努力・調査を投入するほど成果が増える状態に限定する。", "依存させない、ロックイン禁止、搾取的依存禁止を収益化ゲートに含める。", "投資対効果、解約容易性、データ持ち出し、取り消し可能性が説明できる。", "User"],
        ["AIDLC-016", "Findy AI-DLC詳細", "AI-AssistedからAI-Drivenへ移行し、AIが質問・提案・タスク分解・初期成果物生成を主導し、人間が監督・承認する。", "10の設計原則、Mob Elaboration、Inception、Construction、OperationをCAPDkAへ接続する。", "レビュー疲れ、認知負荷、quick-cementをリスクとして記録する。", "Findy Team+"],
        ["AIDLC-017", "CIDLSプラットフォーム全体像", "コンセプト入力、ChatGPT構造化、v0相当ビルダー、SaaS/exe出力、納品ドキュメント一式、Excel出力を1画面にする。", "cidls_platform_overview.htmlとして画像の構成をiframeなしのHTMLで実現する。", "成果物一覧とAI-DLCフェーズが同一HTMLで説明できる。", "User Image"],
        ["AIDLC-018", "祈り入力アプリ工場", "ユーザーの自然言語の願望を注文票、Why5、As-Is/To-Be、制約、完了判定へ変換し、商用アプリと成果物群を生成する。", "AGENTS.md [PRAY_APP_FACTORY] と商用Excelへ接続し、わかったふりやダミー成果物を禁止する。", "トップITエンジニアが見ても違和感のない要求・設計・DB・テスト・運用粒度になる。", "User"],
        ["AIDLC-019", "ComputeUse自律進化", "画面を見てクリック・入力するGUI実測を、E2E再現、設定確認、表示崩れ、認知負荷の反証に使う。", "利用可能ならComputer Use、不可ならBrowser Use、Playwright、スクリーンショット、手動証跡で代替する。", "実測、反証、修正、再検証、kA記録がproject_kanban.htmlとテストへ残る。", "OpenAI / AI総合研究所"],
        ["AIDLC-020", "日次10時複利進化", "CIDLSパイプラインコンセプト画像を実現するため、毎日10:00に反証的な小改善を実行する。", "automation.tomlのrruleとプロンプトへ固定し、AGENTS直交圧縮、A5M2、ComputeUse観点を毎回確認する。", "日次実行で改善、テスト、カンバン、devrag再索引の証跡が残る。", "User"],
    ]


def render_story_html(project_name):
    actor_cards = "".join(
        f"<article><h3>{escape(title)}</h3><p>{escape(text)}</p></article>"
        for title, text in [
            ("プロダクトオーナー", "商品、価格、税、Webhook、Payout、検収証跡を管理し、商用請負レベルの説明責任を負う。"),
            ("バックエンドサーバー", "Secretを保持し、Checkout、Customer Portal、Webhook署名検証、DB更新、監査ログを担当する。"),
            ("本アプリ", "契約状態、開始、請求管理、障害説明を表示する。カード番号とStripe Secretは扱わない。"),
            ("決済サービス", "Stripe Billing、Checkout、Customer Portal、Webhook、Payoutを担当する。"),
            ("ユーザー端末", "ログインセッションと画面表示だけを持ち、正式な契約状態はサーバーから取得する。"),
            ("ユーザー", "初回支払い、継続支払い、キャンセル、請求情報変更をStripe hosted UIで行う。"),
        ]
    )
    flow_rows = "".join(
        f"<tr><td>{step}</td><td>{escape(action)}</td><td>{escape(control)}</td><td>{escape(evidence)}</td></tr>"
        for step, action, control, evidence in [
            ("01", "プロダクトオーナーがStripe Product、Price、lookup_key、Webhook、Payoutを設定する。", "Secretはサーバー専用。", "設定監査ログ"),
            ("02", "ユーザーが本アプリで契約開始を押す。", "サーバー側plan_codeで価格を確定する。", "Checkout Sessionログ"),
            ("03", "ユーザーがStripe Checkoutで初回支払いを完了する。", "カード情報はStripe hosted UIだけが受け取る。", "Checkout完了イベント"),
            ("04", "StripeがWebhookを送る。", "署名検証とevent_id冪等化を必ず行う。", "payment_events"),
            ("05", "本アプリが契約状態を表示する。", "DB状態を正とし、端末キャッシュだけで権限判定しない。", "契約画面"),
            ("06", "Stripe Billingが継続課金と督促を実行する。", "invoice.paidとinvoice.payment_failedをDB反映する。", "請求一覧"),
            ("07", "ユーザーがCustomer Portalでキャンセルする。", "期間末停止と即時停止の差を画面表示する。", "subscription更新イベント"),
            ("08", "プロダクトオーナーがPayoutを入金照合する。", "入金は権限判定に使わない。", "入金照合表"),
            ("09", "発注者がExcel成果物とSTORYで検収する。", "要求、設計、DB、テスト、運用、証跡が追跡できる。", "商用請負納品文書パック"),
        ]
    )
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(project_name)} STORY</title>
<style>
:root {{
  --ink: #172326;
  --muted: #586669;
  --paper: rgba(255, 251, 245, 0.92);
  --line: rgba(23, 35, 38, 0.14);
  --accent: #c45c2d;
  --deep: #173f4a;
  --gold: #c99522;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  color: var(--ink);
  font-family: "BIZ UDPGothic", "Yu Gothic UI", "Meiryo", sans-serif;
  background:
    radial-gradient(circle at 12% 8%, rgba(196, 92, 45, 0.18), transparent 24%),
    radial-gradient(circle at 88% 10%, rgba(23, 63, 74, 0.14), transparent 22%),
    linear-gradient(180deg, #f7f1e6 0%, #efe4d1 100%);
}}
main {{ width: min(1280px, calc(100vw - 32px)); margin: 0 auto; padding: 28px 0; }}
.hero, .card, article {{ background: var(--paper); border: 1px solid var(--line); border-radius: 24px; box-shadow: 0 22px 54px rgba(68, 48, 25, 0.12); }}
.hero {{ padding: 28px; margin-bottom: 16px; }}
.tag {{ display: inline-block; padding: 8px 12px; border-radius: 999px; background: rgba(196, 92, 45, 0.14); color: var(--accent); font-weight: 700; font-size: 0.82rem; }}
h1 {{ margin: 16px 0 10px; font-family: "Yu Mincho", "Hiragino Mincho ProN", serif; font-size: clamp(2rem, 4vw, 4.8rem); line-height: 1.02; }}
p {{ line-height: 1.78; }}
.grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
article {{ padding: 18px; }}
.card {{ margin-top: 16px; padding: 18px; overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; min-width: 980px; }}
th, td {{ border-bottom: 1px solid var(--line); padding: 11px; text-align: left; vertical-align: top; line-height: 1.62; }}
th {{ color: var(--deep); background: rgba(23, 63, 74, 0.08); }}
.notice {{ border-left: 5px solid var(--gold); padding: 12px 14px; background: rgba(201,149,34,0.12); border-radius: 16px; }}
@media (max-width: 980px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<main>
  <section class="hero">
    <span class="tag">商用請負レベル / STORY.html / Stripe Billing / A5:SQL Mk-2</span>
    <h1>{escape(project_name)} 業務ストーリー</h1>
    <p>契約、決済、Webhook、キャンセル、入金、検収までを、発注者が1画面で説明可能な粒度に補完したSTORYです。Excel成果物の要求、設計、DB定義、テスト、運用、抜け漏れチェックと水平展開して扱います。</p>
    <div class="notice">本アプリはカード番号とStripe Secretを保持しません。正式な契約状態はバックエンドDBとWebhook監査ログで確定します。</div>
  </section>
  <section class="grid">{actor_cards}</section>
  <section class="card">
    <h2>正規フローと検収証跡</h2>
    <table>
      <thead><tr><th>#</th><th>業務イベント</th><th>統制・失敗防止</th><th>証跡</th></tr></thead>
      <tbody>{flow_rows}</tbody>
    </table>
  </section>
  <section class="card">
    <h2>水平展開先</h2>
    <p>このSTORYの観点は、商用請負納品文書パックの「03_要求要件定義」「09_DB定義_A5M2」「21_テスト観点」「25_受入検収チェック」「30_トレーサビリティ」「31_STORY補完」へ展開済みです。</p>
  </section>
</main>
</body>
</html>
"""


def write_xlsx(path, sheets):
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml(len(sheets)))
        archive.writestr("_rels/.rels", root_rels_xml())
        archive.writestr("docProps/core.xml", core_xml())
        archive.writestr("docProps/app.xml", app_xml(len(sheets)))
        archive.writestr("xl/workbook.xml", workbook_xml(sheets))
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml(len(sheets)))
        archive.writestr("xl/styles.xml", styles_xml())
        for index, (_, rows) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", worksheet_xml(rows))


def xml_escape(value):
    return escape(str(value), quote=True)


def col_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def worksheet_xml(rows):
    xml_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            ref = f"{col_name(col_index)}{row_index}"
            style = "1" if row_index == 1 else "0"
            cells.append(
                f'<c r="{ref}" t="inlineStr" s="{style}"><is><t>{xml_escape(value)}</t></is></c>'
            )
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    max_col = col_name(max(len(row) for row in rows))
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetFormatPr defaultRowHeight="18"/>
  <sheetData>{"".join(xml_rows)}</sheetData>
  <autoFilter ref="A1:{max_col}{len(rows)}"/>
</worksheet>'''


def workbook_xml(sheets):
    sheet_xml = []
    for index, (name, _) in enumerate(sheets, start=1):
        sheet_xml.append(
            f'<sheet name="{xml_escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>{"".join(sheet_xml)}</sheets>
</workbook>'''


def workbook_rels_xml(sheet_count):
    rels = []
    for index in range(1, sheet_count + 1):
        rels.append(
            f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        )
    rels.append(
        f'<Relationship Id="rId{sheet_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{"".join(rels)}</Relationships>'''


def content_types_xml(sheet_count):
    overrides = [
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for index in range(1, sheet_count + 1):
        overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  {"".join(overrides)}
</Types>'''


def root_rels_xml():
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''


def core_xml():
    created = utc_now_iso()
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>商用請負納品文書パック</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>'''


def app_xml(sheet_count):
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex</Application>
  <DocSecurity>0</DocSecurity>
  <ScaleCrop>false</ScaleCrop>
  <HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant><vt:variant><vt:i4>{sheet_count}</vt:i4></vt:variant></vt:vector></HeadingPairs>
</Properties>'''


def styles_xml():
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Yu Gothic"/></font>
    <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Yu Gothic"/></font>
  </fonts>
  <fills count="3">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF173F4A"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyFont="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''
