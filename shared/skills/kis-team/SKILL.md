---
name: kis-team
description: Orchestrate full KIS pipeline from strategy design to backtest to execution. Use when user asks for end-to-end flow like "전략부터 주문까지", "다 해줘", or full pipeline automation with stage-by-stage confirmation.
---

# KIS Team Orchestrator

Coordinate 3 stages with explicit user confirmation between stages.

## Stages

1. Strategy design (`kis-strategy-builder`)
2. Backtest validation (`kis-backtester`)
3. Signal and order execution (`kis-order-executor`)

## Rules

- Before stage 1, check current auth status.
- Before stage 3, if mode is `prod`, present a clear warning and ask confirmation.
- Stop on any stage failure, report cause, and ask whether to retry/adjust.
- Do not auto-advance without user confirmation.
