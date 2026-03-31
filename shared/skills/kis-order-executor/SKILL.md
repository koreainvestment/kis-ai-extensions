---
name: kis-order-executor
description: "KIS 전략의 실시간 신호를 확인하거나 주문을 실행할 때 반드시 사용. '전략 실행해줘',
  '신호 확인', '종목 돌려봐줘', '매수 신호 있어?', '매도 타이밍', '실시간 매매', '자동매매',
  '삼성전자 지금 들어가도 돼?', '이 전략으로 주문 넣어줘'라고 할 때 자동 실행된다.
  종목 코드를 먼저 선택한 뒤 전략을 실행해 BUY·SELL·HOLD 신호와 강도(0~1)를 확인하고,
  신호 강도에 따라 모의(vps)/실전(prod) 주문을 실행한다.
  실전투자 주문 전 반드시 사용자 확인을 받는다."
model: sonnet
---

# [Step 3] KIS 전략 실행 & 신호 기반 주문

## Purpose

종목을 선택하고 전략을 실행해 BUY/SELL/HOLD 신호를 확인한다.
신호 강도에 따라 모의(vps) 또는 실전(prod) 주문으로 이어진다.

> **중요**: "삼성전자 매수해줘"처럼 직접 주문 요청이 아니라,
> 먼저 **종목 선택 → 전략 실행 → 신호 확인** 과정을 거친 뒤에만 주문이 발생한다.

## 중요 안전 규칙

- **실전(prod) 주문**: 종목명·수량·예상금액 명시 후 반드시 사용자 확인 요청
- **주문 전**: 현재 모드(vps/prod) 반드시 고지
- **신호 강도 < 0.5**: 자동으로 주문 건너뜀

## Prerequisites

- KIS 인증 완료: `/auth vps` (모의) 또는 `/auth prod` (실전)
- strategy_builder 백엔드 실행 중 (port 8000)

## 서버 시작

```bash
# Backend
cd $CLAUDE_PROJECT_DIR/strategy_builder && uv run uvicorn backend.main:app --reload --port 8000

# Frontend
cd $CLAUDE_PROJECT_DIR/strategy_builder/frontend && pnpm dev
# → http://localhost:3000/execute
```

## 주문 가능 시간 (참고 — 실제 판단은 KIS API)

| 시간대 | 시간 (KST) | 주문 유형 |
|--------|-----------|----------|
| 장 전 시간외 | 08:00 ~ 09:00 | 지정가만 가능 |
| 정규장 | 09:00 ~ 15:30 | 시장가·지정가 모두 가능 |
| 장 후 시간외 | 15:40 ~ 18:00 | 지정가만 가능 |

> ⚠️ 위 시간은 **한국 주식 기준 참고값**이다. 품목·시장에 따라 다를 수 있으며,
> 실제 주문 가능 여부는 KIS OpenAPI가 최종 판단한다.
> 장외 시도 시 API가 자동 거부하므로, 오류 발생 시 장 운영 시간을 확인한다.

## Workflow

### 1. 인증 상태 확인

```bash
/auth   # 현재 모드(vps/prod) 및 토큰 만료 시간 먼저 확인
```

### 2. 종목 선택 (먼저)

```bash
# 종목 코드 직접 입력
codes: ["005930", "000660", "035420"]

# 종목 검색
GET /api/symbols/search?q=삼성
GET /api/symbols/search?q=하이닉스
```

### 3. 전략 선택

```bash
# 프리셋 목록 확인
GET /api/strategies

# 커스텀 YAML (Step 1 결과물)
GET /api/strategies/custom
```

### 4. 전략 실행 → 신호 생성

```bash
POST /api/strategies/execute
Body: {
  "strategy_id": "golden_cross",
  "codes": ["005930", "000660"],
  "params": { "fast_period": 50, "slow_period": 200 }
}
```

응답 (`SignalResult`):
```json
[
  { "code": "005930", "name": "삼성전자", "action": "BUY", "strength": 0.85, "reason": "RSI 28.3 < 30" },
  { "code": "000660", "name": "SK하이닉스", "action": "HOLD", "strength": 0.3, "reason": "RSI 45.2 범위 내" }
]
```

### 5. 신호 해석

| 강도 | 의미 | 주문 유형 |
|------|------|----------|
| 0.8 ~ 1.0 | 강한 신호 | 시장가 주문 |
| 0.5 ~ 0.8 | 보통 신호 | 지정가 주문 |
| 0.0 ~ 0.5 미만 | 약한 신호 | 주문 안 함 |

> **기준**: 강도 < 0.5이면 주문을 건너뜀. 강도가 정확히 0.5이면 "보통 신호"로 처리해 지정가 주문 가능.

### 6. 주문 실행 (신호 확인 후)

**실전(prod) 시** — 아래 정보 고지 후 사용자 확인 필수:
```
종목: 삼성전자 (005930)
수량: 10주
예상금액: 약 730,000원
모드: 실전투자 (prod)
→ 실행하시겠습니까?
```

```bash
POST /api/orders
Body: {
  "code": "005930",
  "action": "BUY",       # BUY | SELL
  "quantity": 10,
  "order_type": "market" # market | limit
  # 지정가(limit) 시 "price" 필드 필수 — 현재가 기준으로 설정
  # 매수 지정가: 현재가 이하 (예: 현재가의 99~100%)
  # 매도 지정가: 현재가 이상 (예: 현재가의 100~101%)
}
```

**모의(vps) 시** — 바로 실행 가능

### 7. 결과 모니터링

```bash
# 보유종목 확인
GET /api/account/holdings

# 주문 내역
GET /api/orders/history
```

ExecutionLog에서 타임스탬프별 이벤트 추적 가능

## Troubleshooting

- **인증 오류** → `/auth` 로 현재 상태 확인 후 `/auth vps` 또는 `/auth prod` 재인증
- **주문 거부** → 잔고 부족 또는 거래 시간 외 (정규장 09:00~15:30)
- **신호 없음 (HOLD만 나옴)** → 전략 조건 미충족. 파라미터 조정 또는 다른 전략 시도
- **execute 오류** → strategy_builder 백엔드 실행 중인지 확인 (`lsof -i :8000`)

## 다음 단계

- **[Step 1]** `/kis-strategy-builder` — 신호가 기대와 다를 때 전략 조건 수정
- **[Step 2]** `/kis-backtester` — 실행 전 성과 재검증이 필요할 때
