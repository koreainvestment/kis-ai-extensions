---
name: auth
description: KIS 한국투자증권 인증 (모의/실전/WebSocket/전환)
---

# KIS 인증

## 스크립트 경로

프로젝트 루트의 `{{AGENT_DIR}}/scripts/` 에 있다. 실행 시 **절대 경로**를 사용한다.
먼저 `pwd`로 현재 디렉토리를 확인하고, 프로젝트 루트를 기준으로 경로를 구성한다.

- 상태 확인: `uv run <프로젝트루트>/{{AGENT_DIR}}/scripts/auth.py`
- 인증 실행: `uv run <프로젝트루트>/{{AGENT_DIR}}/scripts/do_auth.py <인자>`

## 인자 처리

`$ARGUMENTS`를 파싱하여 동작을 결정한다.

| 입력 | 동작 |
|---|---|
| `모의`, `vps`, `paper` | 모의투자 REST 인증 |
| `실전`, `prod`, `real` | 실전투자 REST 인증 |
| `ws 모의`, `ws vps` | 모의투자 WebSocket 인증 |
| `ws 실전`, `ws prod` | 실전투자 WebSocket 인증 |
| `switch`, `전환` | 현재 모드 반대로 전환 (모의↔실전) |
| 인자 없음 | 현재 상태 확인 후 사용자에게 물어본다 |

## 실행 순서

### 1. 현재 상태 확인

`auth.py`를 실행하여 JSON 결과를 확인한다.

### 2. 인증 실행

인자에 따라 `do_auth.py`를 호출한다.

- REST 인증: `do_auth.py <vps|prod>`
- WebSocket 인증: `do_auth.py ws <vps|prod>`
- 모드 전환: `do_auth.py switch`

### 3. 결과 확인

do_auth.py의 JSON 출력에서 `success`를 확인한다.
- 성공: `action`, `mode_display`, `expires`를 알려준다.
- 실패: `error` 필드의 메시지를 전달한다.

### 4. 상태 재확인

`auth.py`를 한 번 더 실행하여 인증이 정상 반영되었는지 확인한다.

## 주의사항

- 토큰, 앱키, 시크리트 등 민감 정보는 **절대 출력하지 않는다**.
- 스크립트의 JSON 출력만 참조하며, config 파일(`kis_devlp.yaml`)을 직접 읽지 않는다.
- **실전투자(`prod`) 인증** 시에는 반드시 사용자에게 한 번 더 확인을 받는다.
- **모드 전환(`switch`)** 시에는 기존 토큰이 삭제됨을 안내한다.
- WebSocket 인증의 `approval_key`는 발급 여부만 확인하며, 키 값 자체는 출력하지 않는다.
