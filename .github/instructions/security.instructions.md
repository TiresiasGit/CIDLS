---
name: 'セキュリティ規約 (OWASP Top 10準拠)'
description: 'セキュリティ関連のコーディング規約'
applyTo: '**/*.py,**/*.ts,**/*.js,**/*.tsx,**/*.jsx'
---

# セキュリティコーディング規約

## OWASP Top 10 対策 [Q1.1]

### A01: アクセス制御の不備
- 全エンドポイントに認証・認可チェック必須
- 権限チェック機構の無断削除・省略: **絶対禁止**
- 最小権限の原則を適用
- **未ログイン状態でPII(氏名/メアド/顔写真/学歴)が1フィールドも返らないこと: 必須**

### A02: 暗号化の失敗
- 秘密情報(APIキー/パスワード/トークン)はコード内にハードコード禁止
- `.env` ファイル使用、`.gitignore` に必ず追加
- 通信は HTTPS 必須

### A03: インジェクション
```python
# 禁止: SQLインジェクション
query = f"SELECT * FROM users WHERE name = '{user_input}'"  # 禁止

# OK: パラメータ化クエリ
query = "SELECT * FROM users WHERE name = ?"
cursor.execute(query, (user_input,))
```

### A05: セキュリティの設定ミス
- デバッグモードを本番環境で有効化: 禁止
- デフォルト認証情報の使用: 禁止

### A07: 識別と認証の失敗
- パスワードはハッシュ化必須 (bcrypt/argon2)
- セッション管理を適切に実装
- **メールドメイン制限はサーバーサイドのみで判定 (クライアント側判定禁止)**

### A08: ソフトウェアとデータの整合性の失敗
- 入力値バリデーション: システム境界での必須実施
- ユーザー入力を信頼しない

## 秘密情報管理
```
禁止ファイル (コミット禁止):
  - .env
  - *.key, *.pem, *.p12
  - config/secrets.*
  - credentials.*
```

## 高リスク操作 [AV.4]
認証・決済・個人情報処理は:
- AI委譲低 + 厳格レビュー + セキュリティスキャン必須
- 人間レビュー増加

---

## [CRITICAL] クライアント信頼禁止原則 [SEC.NEVER_TRUST_CLIENT]

> 以下の4パターンは「安心安全を謳いながら全て破綻する」実例から抽出した禁止事項。
> ①課金無限 ②未ログインPII全公開 ③クライアント側メール判定 ④マイナンバー自己申告
> これら全ての根本原因 = **サーバーがクライアントの値を無検証で信頼したこと**

### 禁止パターン 1: クライアント申告の認証状態をDBに保存
```python
# 禁止 (マイナンバー自己申告・権限昇格に直結)
is_verified = request.json.get("is_verified", False)
role = request.json.get("role", "user")
db.save(user_id=uid, is_verified=is_verified, role=role)  # 禁止

# OK: サーバーが状態を付与する
is_verified = False  # 登録時は常にFalse
role = _determine_role_from_server_rules(email)  # サーバールールで決定
```

### 禁止パターン 2: 未認証エンドポイントでのPII返却
```python
# 禁止 (未ログインでも名前・メアドが取得可能になる)
@app.route("/api/users")
def list_users():
    return db.execute("SELECT name, email, photo FROM users").fetchall()  # 禁止

# OK: 認証デコレータ必須 + フィールド最小化
@app.route("/api/users")
@require_auth
def list_users(user):
    return db.execute(
        "SELECT display_name, avatar_url FROM users WHERE visibility='public'"
    ).fetchall()
```

### 禁止パターン 3: 課金数量・金額をクライアントから受信
```python
# 禁止 (数量改ざんで課金アイテム無限取得)
quantity = int(request.json["quantity"])  # 禁止
price = request.json.get("unit_price", 0)  # 禁止: クライアント送信金額

# OK: 数量上限をサーバーで強制・金額はサーバーマスタから取得
MAX_QUANTITY = 10  # サーバー定義
quantity = min(max(int(request.json.get("quantity", 1)), 1), MAX_QUANTITY)
price = _get_price_from_server_master(item_id)  # サーバーマスタ参照
```

### 禁止パターン 4: クライアント側のみのドメイン/資格判定
```typescript
// 禁止 (DevToolsで容易にバイパス可能)
if (email.endsWith('@u-tokyo.ac.jp')) { allowRegistration(); }  // 禁止

// OK: 全判定はAPIリクエストを経由してサーバーで実施
// フロント側は「UX改善のための入力ヒント表示」のみに使用
```

---

## [CRITICAL] PII保護レベル定義

```yaml
高機密 (返却禁止・暗号化保存必須):
  - マイナンバー
  - パスワードハッシュ
  - 生体情報
  - 決済カード情報

中機密 (本人のみ閲覧可):
  - メールアドレス
  - 電話番号
  - 生年月日
  - 住所
  - 学歴 (入学年・学部)

低機密 (認証済みユーザーのみ閲覧可):
  - 表示名
  - 公開設定済みアバター
  - 公開プロフィール文

未認証状態: 全PII返却禁止 (404ではなく401を返す)
```

---

## [CRITICAL] ガバナンス・コンプライアンス必須確認

```
リリース前チェック:
  [ ] 全APIエンドポイントの認証要否リストを作成・承認済みか
  [ ] 未認証エンドポイントにPIIが含まれていないか (自動テスト必須)
  [ ] 課金エンドポイントにサーバーサイド上限・冪等性キーが実装済みか
  [ ] 認証状態フラグ (verified/approved/admin) がクライアントから書き換え不可か
  [ ] メールドメイン・資格判定がサーバーサイドで実施されているか
  [ ] 監査ログがimmutableストレージに記録されているか
  [ ] プライバシーポリシーと実装が一致しているか
  [ ] インシデント対応手順書が存在するか
  [ ] 第三者セキュリティ監査を受けているか (高リスクシステム必須)
```
