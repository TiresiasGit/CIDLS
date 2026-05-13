# CIDLS 引継ぎ資料Pkg

## 主要ファイル
- `project_kanban.html`: Primary SoT
- `project.md`: compact mirror
- `TODO.md`: checklist mirror
- `AGENTS.md`: repo-local operating guide
- `pre_prompt_cycle.bat`: workspace hook entry
- `scripts/sync_agents_cidls_policy.py`: AGENTS sync
- `scripts/audit_global_cidls_wiring.py`: global hook/devrag audit report
- `scripts/alaya_log_intake.py`: log intake
- `STORY.html`: Stripe subscription billing story and app contract artifact

## 現在の完了
- `CIDLS-113`: hook/runtime path 復旧
- `CIDLS-109`: QA / Scenario board 統合
- `CIDLS-110`: log intake 導線追加
- `CIDLS-115`: P1 docs pack 出力
- `CIDLS-112`: automation 初回 run 観測完了

## 現在の未完
- `CIDLS-108`: 実ブラウザ review
- `CIDLS-119`: global devrag corpus の再制限
- `CIDLS-120`: global `build-runtime-config.py` から bare `%CODEX_HOME%` を外す

## 次アクション
1. `CIDLS-108` の browser review を実施
2. `python scripts\audit_global_cidls_wiring.py` で current drift を確認してから global runtime config 更新を実施
3. `CIDLS-119` を解ける global runtime config 更新を実施
4. `CIDLS-120` として generator source も同時に修正し、runtime config 再生成後の再発を止める
