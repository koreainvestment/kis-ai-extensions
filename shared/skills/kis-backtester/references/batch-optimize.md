# Batch & Optimize Tool Reference

## run_batch_backtest_tool

여러 전략을 동시에 백테스트하고 비교 테이블을 반환한다.

### 입력

```json
{
  "items": [
    {"strategy_id": "sma_crossover", "symbols": ["005930"]},
    {"strategy_id": "golden_cross",  "symbols": ["005930"], "param_overrides": {"fast_period": 50}},
    {"yaml_content": "<커스텀 YAML>", "symbols": ["000660"]}
  ],
  "start_date": "2025-01-01",
  "end_date":   "2025-12-31",
  "initial_capital": 10000000
}
```

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `items` | List | 필수 | 전략 목록 — `strategy_id` 또는 `yaml_content` + `symbols` |
| `start_date` | str | 1년 전 | 공통 시작일 |
| `end_date` | str | 오늘 | 공통 종료일 |
| `initial_capital` | float | 10,000,000 | 공통 초기 자본금 |
| `commission_rate` | float | 0.00015 | 공통 수수료율 |
| `tax_rate` | float | 0.002 | 공통 세율 |

### 출력

```json
{
  "success": true,
  "data": {
    "total_submitted": 3,
    "completed": 3,
    "failed": 0,
    "comparison": {
      "by_sharpe":   [{"job_id": "...", "strategy_name": "...", "sharpe_ratio": 1.42, "total_return": 18.5, "max_drawdown": 8.2, "win_rate": 55.0}, ...],
      "by_return":   [...],
      "by_drawdown": [...]
    },
    "job_ids": ["...", "...", "..."],
    "submission_errors": [],
    "runs": [{"job_id": "...", "status": "completed", "result": {...}}, ...]
  }
}
```

### 동작 방식

1. 각 item마다 `_submit_job()` 호출 → 즉시 job_id 반환
2. `asyncio.gather(*[get_backtest_result_wait(jid) for jid in job_ids])` — 전체 동시 대기
3. `_BACKTEST_SEMAPHORE(3)` 가 실제 실행을 최대 3개로 제한

---

## optimize_strategy_tool

Grid/Random Search로 최적 파라미터를 탐색한다. 즉시 job_id를 반환하고 백그라운드에서 실행된다.

### 입력

```json
{
  "strategy_id": "sma_crossover",
  "symbols": ["005930"],
  "parameters": [
    {"name": "fast_period", "min": 5, "max": 20, "step": 5},
    {"name": "slow_period", "min": 20, "max": 60, "step": 10}
  ],
  "search_type": "grid",
  "target": "sharpe_ratio"
}
```

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `strategy_id` | str | 필수 | 프리셋 전략 ID |
| `symbols` | List[str] | 필수 | 종목 코드 |
| `parameters` | List[Dict] | 필수 | `[{"name", "min", "max", "step"}, ...]` |
| `search_type` | str | `"grid"` | `"grid"` 또는 `"random"` |
| `max_samples` | int | 20 | random search 샘플 수 |
| `target` | str | `"sharpe_ratio"` | 최적화 목표 지표 |
| `seed` | int | None | random search 재현성 시드 |

target 옵션: `"sharpe_ratio"` `"total_return"` `"max_drawdown"` (낮을수록 좋음) `"win_rate"`

### 시작 응답

```json
{
  "success": true,
  "data": {
    "job_id": "uuid-...",
    "status": "running",
    "strategy_id": "sma_crossover",
    "search_type": "grid",
    "total_combinations": 12,
    "target": "sharpe_ratio"
  }
}
```

### 진행률 확인 (실행 중)

```
Tool: get_backtest_result_tool { "job_id": "<job_id>", "wait": false }
→ { "status": "running", "progress": { "done": 7, "total": 12 } }
```

### 완료 응답

```json
{
  "status": "completed",
  "result": {
    "best_params":  { "fast_period": 10, "slow_period": 30 },
    "best_job_id":  "uuid-sub-...",
    "best_metrics": { "sharpe_ratio": 1.42, "total_return": 18.5, "annual_return": 20.3, "max_drawdown": 8.2, "win_rate": 55.0 },
    "target": "sharpe_ratio",
    "total_runs": 12,
    "successful_runs": 11,
    "failed_runs": 1,
    "all_runs": [
      { "params": { "fast_period": 5, "slow_period": 20 }, "job_id": "...", "status": "completed", "sharpe_ratio": 0.9, "total_return": 10.2, "max_drawdown": 12.1, "win_rate": 48.0 },
      ...
    ],
    "progress": { "done": 12, "total": 12 }
  }
}
```

### 동작 방식

1. `ParameterGrid` (optimizer.py 재사용) 로 조합 생성
2. 부모 `BacktestJob` 생성 (progress 추적용)
3. `asyncio.create_task(_run_optimize_task(...))` — 백그라운드 실행
4. 각 조합마다 `_submit_job()` → `_BACKTEST_SEMAPHORE(3)` 내부 제어
5. `asyncio.gather` 로 전체 대기, 완료마다 `progress.done` 증가

### Grid vs Random 선택 기준

| 조건 | 권장 |
|------|------|
| 파라미터 조합 수 ≤ 30 | `grid` |
| 파라미터 조합 수 > 30 | `random` + `max_samples` 조정 |
| 넓은 탐색 공간 빠른 탐색 | `random` |
