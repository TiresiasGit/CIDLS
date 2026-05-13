# CIDLS ヒアリングメモ

## 利用目的
- board / docs / automation を一体の運用システムとして扱いたい
- 画像的な構想を実作業面へ落としたい
- AGENTS.md の方針を repo 内で実際に回したい

## As-Is
- AGENTS / hook / automation が root hook 前提に揃っていない時期があり、legacy hook path 依存が drift の原因だった
- QA / Scenario / log intake / docs pack が board に直接つながっていなかった
- devrag は code indexing は通るが markdown docs は configured directory 外で失敗する

## To-Be
- Start Cycle が hook で自動化される
- board から QA / docs / log intake を辿れる
- 未完了は Review / Todo / Blocker として見える

## ステークホルダー
- 実装者: SoT と next action を追いたい
- レビュー担当: Review gate を明確にしたい
- 運用者: automation と hook の健全性を保ちたい
