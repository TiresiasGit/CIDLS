# AGENTS.md - セキュリティ規約 [OWASP, AV.4]

## OWASP Top 10 対策

### A01: アクセス制御の不備
```python
# 禁止: 権限チェックなし
def get_user_data(user_id):
    return db.query(f"SELECT * FROM users WHERE id={user_id}")

# OK: 認証・認可チェック必須
def get_user_data(request, user_id):
    if not request.user.is_authenticated:
        raise PermissionError("認証が必要です")
    if request.user.id != user_id and not request.user.is_admin:
        raise PermissionError("権限がありません")
    return db.query("SELECT * FROM users WHERE id=?", (user_id,))
```

### A03: インジェクション
```python
# 禁止: SQLインジェクション
query = f"SELECT * FROM users WHERE name = '{user_input}'"

# OK: パラメータ化クエリ
query = "SELECT * FROM users WHERE name = ?"
cursor.execute(query, (user_input,))

# DuckDB例
conn.execute("SELECT * FROM users WHERE name = ?", [user_input])
```

### A02: 秘密情報の管理
```python
# 禁止: ハードコード
API_KEY = "<SECRET_VALUE>"  # 禁止

# OK: 環境変数から読み込み
import os
API_KEY = os.environ["API_KEY"]  # KeyErrorで起動時に検出
```

`.gitignore`に必ず追加:
```
.env
*.key
*.pem
config/secrets.*
credentials.*
```

### A07: 入力バリデーション
```python
# システム境界での必須バリデーション
def process_input(data: str) -> str:
    if not isinstance(data, str):
        raise TypeError(f"文字列が必要: {type(data)}")
    if len(data) > 10000:
        raise ValueError("入力が長すぎます")
    # XSS対策: HTMLエスケープ
    return html.escape(data)
```

## AI委譲リスクレベル [AV.4]

```yaml
低リスク (AI委譲高 + 軽微レビュー):
  - テストコード
  - ドキュメント
  - CLIユーティリティ

中リスク (AI委譲中 + 通常レビュー):
  - ビジネスロジック
  - APIエンドポイント

高リスク (AI委譲低 + 厳格レビュー + セキュリティスキャン):
  - 認証・認可
  - 決済処理
  - 個人情報処理
  → 人間レビュー必須
```

## セキュリティチェックリスト [AV.5]

```
  [ ] エッジケース網羅か
  [ ] エラーハンドリングが楽観的すぎないか
  [ ] 既存規約準拠か
  [ ] N+1クエリがないか
  [ ] ハードコード値がないか
  [ ] 認証認可チェックがあるか
  [ ] 入力バリデーションがあるか
  [ ] SQLインジェクション対策があるか
  [ ] XSS対策があるか
  [ ] 秘密情報が.envに隔離されているか
  [ ] [SEC.NEVER_TRUST_CLIENT] 全バリデーションがサーバーサイドで再実施されているか
  [ ] [SEC.PII_AUTH_GATE] 未認証状態でPIIが1フィールドも返らないか
  [ ] [SEC.BILLING_ENFORCE] 課金数量・特典がサーバーサイドのみで決定されているか
  [ ] [SEC.VERIFY_INTEGRITY] 認証状態・資格情報がクライアント書き換えで変更不能か
  [ ] [SEC.GOV_COMPLIANCE] 個人情報保護法・マイナンバー法等の法令遵守を確認済みか
```

---

## [SEC.NEVER_TRUST_CLIENT] クライアント信頼禁止原則 (根本原因: L4直撃)

> **設計の核心**: フロントエンドは「信頼できない外部入力」と同等に扱う。
> クライアント側のバリデーション = UX改善用。セキュリティ = サーバーサイドのみ。

```python
# 禁止: クライアントの値をそのまま信頼
@app.route("/register", methods=["POST"])
def register():
    email = request.json["email"]
    is_verified = request.json.get("is_verified", False)  # 禁止: クライアント申告
    role = request.json.get("role", "user")                # 禁止: クライアント申告
    university = request.json.get("university", "")        # 禁止: クライアント申告
    # そのままDBに保存 → マイナンバー自己申告・権限昇格・大学偽称が全て可能

# OK: サーバーサイドで全項目を再検証
@app.route("/register", methods=["POST"])
def register():
    email = request.json.get("email", "")
    # 1. フォーマット検証 (サーバー側)
    if not _validate_email_format(email):
        raise ValueError("メールアドレスが不正です")
    # 2. ドメイン制限はサーバーで判定 (クライアント判定禁止)
    if not _is_allowed_domain(email):
        raise PermissionError("登録が許可されたドメインではありません")
    # 3. 認証状態はサーバーが付与 (クライアント申告禁止)
    is_verified = False  # 常にFalseで登録。外部認証機関が確認後にサーバーがTrueに変更
    # 4. ロールはサーバーのビジネスロジックで決定
    role = _determine_role_by_server_rules(email)
    ...
```

```yaml
適用必須のルール:
  - クライアントから送られた is_verified / is_admin / role / verified_at 等を
    そのままDBに保存: 絶対禁止
  - 外部認証の状態 (マイナンバー/学生証/メール認証) は
    必ず認証機関APIをサーバーサイドで呼び出して確認する
  - フォームの hidden フィールドに業務ロジック値を埋め込む: 禁止
```

---

## [SEC.PII_AUTH_GATE] 未認証状態でのPII公開禁止

> **直撃する脆弱性**: ②ログインしていなくても全員の名前・メアド・顔写真・高校・大学が公開

```python
# 禁止: 認証なしでPIIを返す
@app.route("/api/users")
def get_users():
    return jsonify(db.execute("SELECT * FROM users").fetchall())  # 禁止

# OK: 認証ゲート + データ最小化
from functools import wraps

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        user = _verify_jwt_server_side(token)  # サーバーサイドで検証
        if not user:
            return jsonify({"error": "認証が必要です"}), 401
        return f(*args, user=user, **kwargs)
    return decorated

@app.route("/api/users")
@require_auth
def get_users(user):
    # 自分のデータのみ返す (他ユーザーのPIIは非表示)
    return jsonify(_get_public_profile_only(user.id))

def _get_public_profile_only(user_id):
    # 公開フィールドのみ (メアド・電話番号・生年月日は返さない)
    return db.execute(
        "SELECT display_name, avatar_url FROM users WHERE id = ?",
        [user_id]
    ).fetchone()
```

```yaml
チェックリスト:
  [ ] 全APIエンドポイントに @require_auth が付いているか (ホワイトリスト方式)
  [ ] 公開エンドポイント (認証不要) はリストアップして明示的に承認されているか
  [ ] SELECT * の使用禁止 (必要フィールドのみ取得・返却)
  [ ] メールアドレス・電話番号・生年月日・住所はログイン済み本人のみ閲覧可
  [ ] 顔写真・氏名の公開範囲はユーザーが制御可能か (プライバシー設定)
  [ ] APIレスポンスに不要フィールドが混入していないか (diff確認必須)

PII定義 (最低限):
  高機密: マイナンバー / パスワードハッシュ / 生体情報 / 決済情報
    → 原則返却禁止。表示が必要な場合はマスキング (下4桁のみ等)
  中機密: メールアドレス / 電話番号 / 生年月日 / 住所
    → 本人のみ閲覧可
  低機密: 表示名 / アバター画像 (公開設定済み)
    → 認証済みユーザーのみ閲覧可 (未ログインは禁止)
```

---

## [SEC.BILLING_ENFORCE] 課金・特典のサーバーサイド強制

> **直撃する脆弱性**: ①課金アイテム無限取得

```python
# 禁止: 数量をクライアントから受け取りそのまま処理
@app.route("/api/purchase", methods=["POST"])
def purchase():
    quantity = int(request.json["quantity"])  # 禁止: 0以下・上限超過・改ざん可能
    item_id = request.json["item_id"]
    total = quantity * get_price(item_id)
    charge_user(total)
    grant_items(quantity)  # 無限付与が可能

# OK: サーバーサイドで全課金ロジックを制御
@app.route("/api/purchase", methods=["POST"])
@require_auth
def purchase(user):
    item_id = request.json.get("item_id")
    quantity = request.json.get("quantity", 1)
    # 1. 数量の上限・下限をサーバーが強制
    if not isinstance(quantity, int) or not (1 <= quantity <= MAX_PURCHASE_QUANTITY):
        raise ValueError(f"数量は1〜{MAX_PURCHASE_QUANTITY}の整数のみ許可")
    # 2. 価格はサーバーのマスタから取得 (クライアント送信の金額は禁止)
    unit_price = _get_price_from_server_master(item_id)
    total = unit_price * quantity
    # 3. 残高・制限をサーバーで確認
    _check_purchase_limit(user.id, item_id, quantity)
    # 4. 冪等性キーで二重課金防止
    idempotency_key = request.headers.get("X-Idempotency-Key")
    _charge_with_idempotency(user.id, total, idempotency_key)
    # 5. 付与もサーバーが完結
    _grant_items_server_side(user.id, item_id, quantity)
```

```yaml
課金セキュリティ必須要件:
  - 価格・数量・割引: クライアント送信値を使用禁止。サーバーマスタから取得
  - 上限設定: 1回取引・1日・1ユーザーあたりの上限をサーバーで強制
  - 冪等性キー: 二重決済防止のためX-Idempotency-Headerを必須化
  - 在庫管理: 在庫数はDB排他ロックで制御 (SELECT FOR UPDATE)
  - 監査ログ: 全課金トランザクションをimmutableなログに記録
  - ロールバック: 付与失敗時は課金もロールバック (ACID保証)
```

---

## [SEC.VERIFY_INTEGRITY] 認証状態・資格情報の改ざん防止

> **直撃する脆弱性**: ③クライアント側メール判定バグ / ④マイナンバー自己申告

```python
# 禁止: クライアントが送った認証状態を信頼
@app.route("/api/verify-status", methods=["POST"])
def verify_status():
    user_id = request.json["user_id"]
    is_mynumber_verified = request.json["is_verified"]  # 禁止: 自己申告
    db.execute("UPDATE users SET mynumber_verified=? WHERE id=?",
               [is_mynumber_verified, user_id])  # 禁止: 自己申告をそのまま保存

# OK: 外部認証機関への問い合わせはサーバーからのみ実施
def verify_mynumber_server_side(user_id: str, session_token: str) -> bool:
    """
    マイナンバー認証はサーバーが直接外部APIを呼ぶ。
    クライアントから認証済みフラグを受け取ることは禁止。
    """
    response = _call_official_mynumber_api(session_token)  # 公式APIをサーバーから呼出
    if response.status != "VERIFIED":
        raise PermissionError("マイナンバー認証が完了していません")
    # サーバーが検証した結果のみDBに保存
    db.execute(
        "UPDATE users SET mynumber_verified=TRUE, verified_at=NOW() WHERE id=?",
        [user_id]
    )

# 禁止: メールドメイン判定をクライアント側のみで実施
# フロントエンド (禁止例):
# if (email.endsWith('@u-tokyo.ac.jp')) { allowRegistration(); }

# OK: サーバーサイドでドメイン検証
ALLOWED_DOMAINS = frozenset({"u-tokyo.ac.jp", "m.u-tokyo.ac.jp"})  # サーバー定義

def validate_university_email(email: str) -> None:
    domain = email.split("@")[-1].lower()
    if domain not in ALLOWED_DOMAINS:
        raise PermissionError(f"許可されたドメインではありません: {domain}")
    # メール送信による所有確認も必須
    _send_verification_email(email)
```

```yaml
認証状態の保護ルール:
  - [IMMUTABLE_FLAG] 認証フラグ (verified/approved/admin等) はサーバー内部のみ変更可
  - [EXTERNAL_VERIFY] 外部認証 (マイナンバー/学生証/メール認証) は
    認証機関APIをサーバーから直接呼び出すこと。コールバック値も検証する
  - [EMAIL_DOMAIN] ドメイン制限はサーバー定義の許可リストで判定 + メール所有確認必須
  - [ANTI_REPLAY] 認証トークン/セッションは使い捨て。再利用禁止
  - [SIGNED_STATE] 認証状態をクライアントに保持させる場合はHMAC署名必須

男女・資格判定の追加注意点:
  - 性別・資格・所属はクライアントの自己申告を登録時に使用禁止
  - 公式ドキュメント (学生証/社員証/マイナンバー) と突合するか、
    公式メールアドレスへの認証フロー必須
```

---

## [SEC.GOV_COMPLIANCE] ガバナンス・コンプライアンスリスク

```yaml
個人情報保護法 (日本 / GDPR相当):
  禁止:
    - 本人同意なしに第三者へのPII開示 (②の脆弱性がこれに該当)
    - 利用目的外でのPII使用
    - 越境移転の無断実施
  必須:
    - プライバシーポリシーと実装の完全一致
    - 開示・訂正・削除請求への対応手順
    - 漏洩時72時間以内の当局報告手順

マイナンバー法:
  禁止:
    - マイナンバーの目的外収集・保管
    - 自己申告による認証済みフラグ付与 (④の脆弱性がこれに該当)
  必須:
    - 利用目的の法令根拠の明示
    - 専用の安全管理措置の実装 (アクセスログ・暗号化・物理分離)
    - 廃棄手順

不正競争防止法 / 不正アクセス禁止法:
  リスク: ①の課金無限取得は不正アクセス行為として問われる可能性
  対策: 利用規約での禁止事項明示 + サーバーサイド強制 + 自動検知・アカウント停止

コンプライアンス確認チェックリスト:
  [ ] プライバシーポリシーと実装が一致しているか (年1回以上レビュー)
  [ ] マイナンバー取扱い規程が存在するか
  [ ] インシデント対応手順書が存在するか (72時間ルール対応)
  [ ] 第三者セキュリティ監査を実施済みか (リリース前必須)
  [ ] 利用規約に禁止行為が明記されているか
  [ ] 年齢制限・本人確認の法令要件を満たしているか
```

---

## [SEC.OPS] 運用セキュリティ (低運用負荷設計)

```yaml
監査ログ設計 (改ざん不可):
  必須記録項目:
    - 認証成功/失敗: user_id, ip, timestamp, user_agent
    - PII閲覧: who, what_fields, when
    - 課金トランザクション: amount, item, idempotency_key, result
    - 認証状態変更: field, old_value, new_value, changed_by, reason
    - 管理者操作: 全操作を記録
  保管:
    - 最低1年間 (法令要件に応じて延長)
    - ログはimmutable (追記専用。削除・変更禁止)
    - 別サーバー/ストレージに保管 (アプリサーバーと分離)

異常検知・自動アラート:
  - 同一ユーザーの課金量が1日上限の80%超: 自動フラグ
  - 短時間での連続API呼び出し (レートリミット超過): 自動ブロック + 通知
  - 未ログイン状態でのPIIエンドポイントアクセス試行: 即時アラート
  - 認証フラグの直接DB操作 (管理画面外): 即時アラート

定期レビュー (低負荷化):
  月次: 異常ログサマリー確認 (自動集計レポート)
  四半期: アクセス権限棚卸し
  年次: プライバシーポリシーレビュー + 第三者監査
  リリース前: [AV.5] セキュリティチェックリスト全項目確認

インシデント対応手順:
  Level1 (低): バグ修正 → 72時間以内にパッチ
  Level2 (中): データ流出疑い → 4時間以内に調査開始 + 関係者通知
  Level3 (高): 個人情報漏洩確定 → 1時間以内にサービス停止検討 + 72時間以内に当局報告
```

---

## [SEC.UX_SECURITY] セキュリティとUXの両立

```yaml
エラーメッセージの原則 (情報漏洩防止):
  禁止:
    - "メールアドレスが存在しません" → ユーザー列挙攻撃に悪用される
    - "パスワードが間違っています" → IDの存在確認に悪用される
    - スタックトレースをUIに表示
  OK:
    - "メールアドレスまたはパスワードが正しくありません" (統一メッセージ)
    - "エラーが発生しました (コード: E1042)" → サポートに問い合わせ可能

セキュリティ機能の可視化 (UX向上):
  - 認証済みバッジの表示基準を明示 (どの認証を経たか)
  - プライバシー設定画面: 「誰に何が見えているか」を視覚的に表示
  - 認証フロー: 進捗バー + 各ステップの説明 (ユーザーが安心できる設計)

データ最小化原則 (UX + セキュリティ):
  - 登録フォームで必須でない個人情報を要求しない
  - 「なぜこの情報が必要か」を登録時に説明
  - 不要になった個人情報の自動削除スケジュール設定

説明理解容易性:
  [ ] プライバシーポリシーに平易な日本語サマリーを先頭に配置
  [ ] 「あなたのデータがどう使われるか」を図解で示す
  [ ] セキュリティ機能 (認証・暗号化) の説明をユーザー向けに記載
  [ ] 問い合わせ窓口 (セキュリティ報告先) を明示

脆弱性報告受付 (Responsible Disclosure):
  - セキュリティ報告用メールアドレスをWebサイトに明示
  - 報告受領後の対応SLAを公開 (例: 72時間以内に受領確認)
  - 対応完了後は報告者への謝辞 (任意)
```
