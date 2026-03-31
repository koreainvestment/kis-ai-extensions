---
name: my-status
description: "KIS 계좌 상태를 조회할 때 반드시 사용. '잔고 확인', '보유종목', '내 계좌', '지수 확인', 'my-status'라고 할 때 자동 실행된다."
---

# KIS 계좌 상태 조회

## 스크립트 경로

- 인증 확인: `uv run <프로젝트루트>/.codex/scripts/auth.py`
- API 조회: `uv run <프로젝트루트>/.codex/scripts/api_client.py <서브커맨드>`

## 인자 처리

| 입력 | 서브커맨드 | 설명 |
|---|---|---|
| (인자 없음) | `balance` + `holdings` | 잔고와 보유종목 |
| `잔고`, `예수금`, `balance` | `balance` | 예수금/평가금액만 |
| `보유종목`, `종목`, `holdings` | `holdings` | 보유종목만 |
| `코스피`, `지수`, `index` | `index` | 코스피/코스닥 지수 |
| `전체`, `all` | `all` | 잔고 + 보유종목 + 지수 전부 |

## 실행 순서

1. `auth.py` 실행 — `authenticated`가 `false`이면 "인증해줘"라고 안내 후 중단
2. `api_client.py <서브커맨드>` 실행
3. JSON 결과를 표로 정리하여 출력

## 주의사항

- 계좌번호는 JSON의 `account` 필드 그대로 사용 (이미 마스킹됨).
- 토큰, 앱키, 시크리트 등 민감 정보는 **절대 출력하지 않는다**.
