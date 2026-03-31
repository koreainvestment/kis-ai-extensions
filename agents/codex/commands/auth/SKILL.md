---
name: auth
description: "KIS 인증이 필요할 때 반드시 사용. '인증해줘', '모의투자 인증', '실전 인증', '토큰 갱신', 'auth vps', 'auth prod', 'auth switch'라고 할 때 자동 실행된다."
---

# KIS 인증

## 스크립트 경로

프로젝트 루트의 `scripts/` 에 있다. 실행 시 **절대 경로**를 사용한다.
먼저 `pwd`로 현재 디렉토리를 확인하고, 프로젝트 루트를 기준으로 경로를 구성한다.

- 상태 확인: `uv run <프로젝트루트>/.codex/scripts/auth.py`
- 인증 실행: `uv run <프로젝트루트>/.codex/scripts/do_auth.py <인자>`

## 인자 처리

| 입력 | 동작 |
|---|---|
| `모의`, `vps`, `paper` | 모의투자 REST 인증 |
| `실전`, `prod`, `real` | 실전투자 REST 인증 |
| `ws 모의`, `ws vps` | 모의투자 WebSocket 인증 |
| `ws 실전`, `ws prod` | 실전투자 WebSocket 인증 |
| `switch`, `전환` | 현재 모드 반대로 전환 (모의↔실전) |
| 인자 없음 | 현재 상태 확인 후 사용자에게 물어본다 |

## 실행 순서

1. `auth.py` 실행 — 현재 상태 확인
2. 인자에 따라 `do_auth.py` 호출
   - REST: `do_auth.py <vps|prod>`
   - WebSocket: `do_auth.py ws <vps|prod>`
   - 전환: `do_auth.py switch`
3. JSON 출력의 `success` 확인 후 결과 안내
4. `auth.py` 재실행 — 정상 반영 확인

## 주의사항

- 토큰, 앱키, 시크리트 등 민감 정보는 **절대 출력하지 않는다**.
- **실전투자(`prod`) 인증** 시에는 반드시 사용자에게 한 번 더 확인을 받는다.
- **모드 전환(`switch`)** 시에는 기존 토큰이 삭제됨을 안내한다.
