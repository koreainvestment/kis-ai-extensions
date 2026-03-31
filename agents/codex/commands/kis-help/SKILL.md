---
name: kis-help
description: "KIS 플러그인 사용법을 안내할 때 사용. '사용법', '도움말', '커맨드 목록', '오류코드', 'kis-help'라고 할 때 자동 실행된다."
---

# KIS Help

`$ARGUMENTS`가 있으면 해당 키워드로 필터해서 보여준다.
없으면 "안녕하세요 고객님! 한국투자증권 openapi입니다. 무엇을 도와드릴까요?" 라고 말한 후 사용법을 안내한다.

---

## 스킬 목록

| 트리거 문구 | 스킬 | 단계 | 주요 기능 |
|------------|------|------|----------|
| "전략 만들어줘", "YAML 전략" | **kis-strategy-builder** | Step 1 | 10개 프리셋 또는 커스텀 `.kis.yaml` 생성 |
| "백테스트 해줘", "수익률 확인" | **kis-backtester** | Step 2 | 과거 성과 검증, 파라미터 최적화, HTML 리포트 |
| "신호 확인", "매수 신호 있어?" | **kis-order-executor** | Step 3 | BUY/SELL/HOLD 신호 → 모의/실전 주문 |
| "다 해줘", "전략부터 주문까지" | **kis-team** | 1→2→3 | 3단계 전체 오케스트레이션 |
| $auth, "auth vps" | **auth** | — | 모의/실전 인증 |
| "잔고 확인", "보유종목" | **my-status** | — | 잔고·보유종목·지수 조회 |
| "환경 확인", "setup" | **kis-setup** | — | 환경 진단 및 자동 설치 |

---

## 자주 쓰는 흐름

```
# 처음 시작
$auth vps            → auth 스킬
"잔고 확인해줘"           → my-status 스킬

# 전략 설계 → 검증 → 실행
"RSI 전략 만들어줘"       → kis-strategy-builder
"백테스트 해줘"           → kis-backtester
"삼성전자 신호 확인해줘"   → kis-order-executor

# 한 번에 다
"전략부터 주문까지 다 해줘" → kis-team
```

---

## 오류코드 빠른 참조

| 상황 | 코드 | 해결책 |
|------|------|--------|
| API 너무 빠르게 호출 | EGW00201 | 초당 1건 이하로 제한 |
| 토큰 만료 | EGW00103/105 | $auth vps 또는 $auth prod |
| 모의투자인데 TR_ID가 T로 시작 | EGW00213 | TR_ID를 V로 변경 |
| WebSocket 중복 연결 | OPSP8996 | 기존 연결 종료 후 재연결 |
| 세션 끊김 | OPSQ1002 | $auth로 재인증 |
| API 권한 없음 | EGW00206 | KIS OpenAPI 신청 필요 |
