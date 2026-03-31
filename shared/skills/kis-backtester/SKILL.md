---
name: kis-backtester
description: "KIS 전략을 과거 데이터로 검증하거나 성과를 확인할 때 반드시 사용. '백테스팅', '백테스트
  해줘', '전략 검증', '성과 분석', '파라미터 최적화', '수익률 확인', '과거 검증', '샤프 확인',
  '최대낙폭 보고 싶어', '이 전략 수익률이 어떻게 돼?'라고 할 때 자동 실행된다.
  backtester MCP 서버를 통해 10개 프리셋(sma_crossover, momentum 등) 또는 .kis.yaml 전략 실행,
  BacktestResult(총수익률·CAGR·최대낙폭·샤프) 해석, Grid/Random 파라미터 최적화,
  배치 전략 비교, 포트폴리오 분석, HTML 리포트 생성을 수행한다."
model: sonnet
---

# [Step 2] KIS 백테스팅

## Purpose

backtester 백테스팅 시스템으로 전략의 과거 성과를 검증한다.
10개 프리셋 또는 Step 1에서 만든 `.kis.yaml`을 실행해 수익률·샤프·최대낙폭을 확인하고,
파라미터 최적화와 HTML 리포트 생성까지 지원한다.
날짜 관련 사용자의 요청이 없으면 모든 end_date는 시스템 날짜로 오늘 날짜를 기본으로 하며(datetime.today()) start_date는 1년전을 기본으로 넣는다.

## Prerequisites (필수 — 미충족 시 실행 불가)

- **Docker 실행 중** (`quantconnect/lean:latest`) — 백테스트 엔진이 Docker 컨테이너로 동작
- KIS 인증 완료 (`/auth vps` 또는 `/auth prod`)

```bash
# Docker 상태 확인
docker ps
# lean 이미지 없으면:
docker pull quantconnect/lean:latest
```

## 서버 시작

```bash
# MCP 서버 (port 3846) — IDE에서 백테스트 도구 직접 호출
cd $CLAUDE_PROJECT_DIR/backtester && bash scripts/start_mcp.sh
# → http://127.0.0.1:3846/mcp

# (선택) Backend REST API (port 8002)
cd $CLAUDE_PROJECT_DIR/backtester && uv run uvicorn backend.main:app --reload --port 8002

# (선택) Frontend
cd $CLAUDE_PROJECT_DIR/backtester/frontend && pnpm dev
# → http://localhost:3001
```

## Workflow

### 0. 백테스트 조건 확인 (커스텀 YAML인 경우)

커스텀 YAML(프리셋이 아닌)로 백테스트 요청이 들어오면, 실행 전 사용자에게 조건을 확인받는다:

```
📋 백테스트 조건 확인

| 항목 | 값 |
|------|-----|
| 전략 | 삼성전자 스윙 전략 |
| 종목 | 005930 (삼성전자) |
| 기간 | 2024-02-25 ~ 2026-02-25 (1년) |
| 초기자금 | 10,000,000원 |
| 주요 지표 | EMA(20,60), RSI(14), ATR(14) |
| 진입 | EMA 골든크로스 AND RSI < 40 |
| 청산 | EMA 데드크로스 OR RSI > 70 |
| 손절/익절 | 4.0% / 12.0% |

이 조건으로 백테스트를 실행할까요? 변경할 항목이 있으면 말씀해주세요.
```

**YAML 사전 검증**:
- `validate_yaml_tool`로 문법 검증
- 조건의 `value` 필드에 `$param_name` 변수가 있으면 → 해당 파라미터의 default 값으로 치환 후 실행
- `value`가 숫자가 아니면 사용자에게 알리고 수정

사용자가 확인하면 실행 단계로 진행한다.

### 1. 전략 선택

- **프리셋 ID**: `"sma_crossover"`, `"momentum"` 등 10개
  ```
  Tool: list_presets_tool          # 전체 목록 + param 스키마 확인
  Tool: get_preset_yaml_tool       # { "strategy_id": "sma_crossover" }
  ```
- **커스텀 YAML**: Step 1에서 생성한 `.kis.yaml` 사용
  ```
  Tool: validate_yaml_tool         # { "yaml_content": "..." } — 반드시 먼저 실행
  # valid: false이면 errors 수정 후 재검증. valid: true 확인 후에만 실행
  Tool: run_backtest_tool          # yaml_content로 직접 실행
  ```
- **지표 목록 확인**:
  ```
  Tool: list_indicators_tool       # 80개 지표 + 57개 캔들스틱 파라미터 정의
  ```

## YAML 자동 생성

사용자가 "RSI+MACD 전략 백테스트 해줘"처럼 말할 경우 에이전트가 직접 YAML을 생성 후 파일로 저장해 실행한다.

### 생성 규칙
1. `strategy.id`: snake_case 영문+숫자+_ (고유값, 예: `my_rsi_macd`)
2. `strategy.indicators`: 지표마다 고유 `alias` 필수. 같은 지표 중복 사용 시 다른 alias 사용
3. 다중 출력 지표(`macd`, `bollinger`, `stochastic`)는 지표 정의에 `output` 필드로 분리하거나, 조건에서 `output`/`compare_output` 필드 사용
4. `conditions`: `value`(숫자) 또는 `compare_to`(alias) 중 하나만 — 동시 사용 금지
5. `risk`: `{enabled: true, percent: X.0}` 형식
6. `version`: `"1.0"` 고정

### References 파일 요약

| 파일 | 내용 |
|------|------|
| `references/yaml-templates.md` | 10개 YAML 기반 전략 템플릿 (golden_cross 등) — 커스텀 YAML 빠른 시작용 |
| `references/indicator-params.md` | 21개 지표 id·params·다중출력 레퍼런스 (sma, ema, rsi, macd, bollinger 등) |
| `references/batch-optimize.md` | run_batch_backtest_tool / optimize_strategy_tool 상세 입출력 명세 |

### 프리셋 → YAML 변환
`references/yaml-templates.md` 에서 해당 전략 복사 → alias/params 조정 → 파일 저장

### 커스텀 전략 → YAML 생성
`references/indicator-params.md` 에서 지표 id/params 확인 → 조건 조합 → 체크리스트 검증 후 저장

### 2. 파라미터 설정

```
Tool: list_presets_tool    # 해당 전략의 params 스키마 확인 (type, min, max, default)
Tool: get_preset_yaml_tool # { "strategy_id": "sma_crossover", "param_overrides": {"fast_period": 50} }
```

각 프리셋별 주요 파라미터 (period, oversold, overbought, fast_period, slow_period 등)

### 3. 실행 옵션 설정

**프리셋 실행** — `start_date`/`end_date` 생략 시 자동 설정 (1년 전 ~ 오늘):
```
Tool: run_preset_backtest_tool {
  "strategy_id": "sma_crossover",
  "symbols": ["005930", "000660"],
  "initial_capital": 10000000,
  "param_overrides": { "fast_period": 5, "slow_period": 20 }
}
→ { job_id, status: "running" }
```

**커스텀 YAML 실행**:
```
Tool: run_backtest_tool {
  "yaml_content": "<.kis.yaml 내용>",
  "symbols": ["005930"]
}
→ { job_id, status: "running" }
```

**결과 조회** (기본: 완료까지 자동 대기, 폴링 불필요):
```
Tool: get_backtest_result_tool { "job_id": "<job_id>" }
→ 서버 내부에서 완료까지 대기 후 최종 결과 반환 (최대 5분)
→ 완료 시   : { status: "completed", result: { metrics, equity_curve, ... } }
→ 실패 시   : { status: "failed", error: "..." }
→ 타임아웃  : { status: "running", message: "타임아웃..." }

# 즉시 상태만 확인 (대기 없음):
Tool: get_backtest_result_tool { "job_id": "<job_id>", "wait": false }
```

### 4. 결과 해석

`BacktestResult` 필드:

| 필드 | 의미 |
|------|------|
| `total_return_pct` | 총 수익률 (%) |
| `cagr` | 연평균 복리 수익률 |
| `sharpe_ratio` | 위험 대비 수익 (1.0+ 양호) |
| `sortino_ratio` | 하락 위험 대비 수익 |
| `max_drawdown` | 최대 낙폭 (낮을수록 좋음) |
| `win_rate` | 승률 (%) |
| `profit_factor` | 총이익/총손실 비율 |
| `total_trades` | 총 거래 횟수 |

### 4b. 백테스트 재시도 (실패 시)

EGW00201(초당 한도 초과) 등 일시적 오류로 실패한 경우 재시도:
```
Tool: retry_backtest_tool { "job_id": "<실패한 job_id>" }
→ { new_job_id, status: "running" }
# 이후 get_backtest_result_tool { "job_id": "<new_job_id>" } 로 결과 조회
```
> 캐시된 데이터는 재다운로드하지 않으므로 빠르게 재실행됨.
> 충분히 대기(10~30초)한 뒤 호출할 것.

### 5. 파라미터 최적화 (선택)

→ 상세 입출력/동작 방식: [`references/batch-optimize.md`](references/batch-optimize.md)

```
Tool: optimize_strategy_tool {
  "strategy_id": "sma_crossover",
  "symbols": ["005930"],
  "parameters": [
    {"name": "fast_period", "min": 2, "max": 20, "step": 3},
    {"name": "slow_period", "min": 10, "max": 60, "step": 10}
  ],
  "search_type": "grid",   # 또는 "random" + "max_samples": 30
  "target": "sharpe_ratio" # sharpe_ratio | total_return | max_drawdown | win_rate
}
→ { job_id, total_combinations: 12, status: "running" }

Tool: get_backtest_result_tool { "job_id": "<job_id>" }
→ { result: { best_params, best_metrics, all_runs, total_runs, successful_runs } }

# 실행 중 진행률:
Tool: get_backtest_result_tool { "job_id": "<job_id>", "wait": false }
→ { status: "running", progress: { done: 7, total: 12 } }
```

### 5b. 배치 백테스트 — 여러 전략 동시 비교 (선택)

→ 상세 입출력/동작 방식: [`references/batch-optimize.md`](references/batch-optimize.md)

```
Tool: run_batch_backtest_tool {
  "items": [
    {"strategy_id": "sma_crossover", "symbols": ["005930"]},
    {"strategy_id": "golden_cross",  "symbols": ["005930"], "param_overrides": {"fast_period": 50}},
    {"yaml_content": "<커스텀 YAML>", "symbols": ["000660"]}
  ]
}
→ { completed, comparison: { by_sharpe, by_return, by_drawdown }, runs, job_ids }
```

### 6. 포트폴리오 분석 (선택)

복수 종목을 단일 백테스트로 실행하면 포트폴리오 효과 확인 가능:
```
Tool: run_preset_backtest_tool {
  "symbols": ["005930", "000660", "035420"],
  "initial_capital": 30000000
}
# → 전체 포트폴리오 통합 성과 (equity_curve, 총수익률, 샤프)
```

### 7. HTML 리포트 생성

```
Tool: get_report_tool { "job_id": "<job_id>", "format": "html" }
# → 브라우저 자동 오픈 + 차트·거래 내역·통계 포함 리포트 경로 반환

Tool: get_report_tool { "job_id": "<job_id>", "format": "json" }
# → 핵심 지표 요약 JSON (총수익률, CAGR, MDD, 샤프 등)
```

## 10개 프리셋 ID 목록

| ID | 이름 | 카테고리 | 주요 파라미터 |
|----|------|----------|--------------|
| `sma_crossover` | SMA 골든/데드 크로스 | trend | fast_period, slow_period |
| `momentum` | 모멘텀 | momentum | lookback, threshold |
| `trend_filter_signal` | 추세 필터 + 시그널 | composite | trend_period |
| `week52_high` | 52주 신고가 돌파 | trend | lookback, stop_loss_pct |
| `ma_divergence` | 이동평균 이격도 | mean_reversion | period, buy_ratio, sell_ratio |
| `false_breakout` | 추세 돌파 후 이탈 | trend | lookback |
| `short_term_reversal` | 단기 반전 | mean_reversion | period, threshold_pct |
| `strong_close` | 강한 종가 | momentum | close_ratio, stop_loss_pct |
| `volatility_breakout` | 변동성 축소 후 확장 | volatility | atr_period, lookback |
| `consecutive_moves` | 연속 상승·하락 | momentum | up_days, down_days |

## 결과 해석 기준

| 지표 | 기준 | 평가 |
|------|------|------|
| Sharpe Ratio | > 1.5 | 우수 / 1.0~1.5 양호 / < 1.0 개선 필요 |
| Max Drawdown | < 10% | 우수 / < 20% 권장 / > 20% 위험 |
| Win Rate | > 55% | 양호 (단, Profit Factor와 함께 해석) |
| Profit Factor | > 1.5 | 양호 / > 2.0 우수 |

## Troubleshooting

- **MCP 서버 미실행** → `curl http://127.0.0.1:3846/health` 확인 후 `bash backtester/scripts/start_mcp.sh`
- **Docker 미실행** → `docker ps` 확인 후 Docker Desktop 시작 (필수)
- **데이터 없음** → `/auth` 로 KIS 인증 상태 확인 (`/auth vps` or `/auth prod`)
- **포트 8002 충돌** → `lsof -i :8002` 로 프로세스 확인 후 종료
- **최적화 느림** → 파라미터 범위 축소 또는 종목 1개로 먼저 테스트

## 다음 단계

- **[Step 3]** `/kis-order-executor` — 검증된 전략으로 실전/모의 매매 실행
- **[Step 1]** `/kis-strategy-builder` — 성과 부족 시 전략 수정
