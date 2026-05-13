# CIDLS 運用保守手順書

## Start Cycle
1. `cmd /c pre_prompt_cycle.bat`
2. 失敗した場合は `cmd /c installer.bat`
3. それでも失敗した場合は `logs/cidls_agents_sync_report.json` と `state/autonomy_state.json` を確認

## 日次運用
1. `project_kanban.html` を SoT として更新する
2. `project.md` と `TODO.md` を mirror として更新する
3. `scripts/sync_agents_cidls_policy.py` を通して AGENTS.md を同期する
4. `python scripts\audit_global_cidls_wiring.py` を実行して `logs/global_cidls_wiring_report.json` を更新する
5. `devrag` spill を見たら report を起点に `runtime-devrag-config.json` と `build-runtime-config.py` の両方を確認する
6. `%CODEX_HOME%` が空でも監査できるよう、global path は `%USERPROFILE%\.codex` または明示された `%CODEX_HOME%` を基準に扱う

## Log Intake
1. `python scripts\alaya_log_intake.py`
2. `logs/alaya_intake_report.json` を確認する
3. 入力が見つかったら改善候補を `CIDLS-*` ticket に起票する

## Browser Review
1. desktop で `project_kanban.html` を開く
2. mobile 相当の narrow viewport でも開く
3. `CIDLS-108` を Review から Done に移す条件を満たしたら board / project / TODO を同期する

## 既知 blocker
- `CIDLS-108`: browser review 未完了
- `CIDLS-119`: global devrag runtime config が `.codex` 全域を index している
- `CIDLS-120`: global `build-runtime-config.py` が bare `%CODEX_HOME%` を再注入する
- automation shell では `%CODEX_HOME%` が空のことがあるため、global wiring 監査は絶対パス基準で行う
