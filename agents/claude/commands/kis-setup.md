---
name: kis-setup
description: 프로젝트 세팅 도우미 (환경 진단 + 자동 설치)
---

# KIS Setup

## 스크립트 경로

프로젝트 루트의 `.claude/scripts/` 에 있다. 실행 시 **절대 경로**를 사용한다.
먼저 `pwd`로 현재 디렉토리를 확인하고, 프로젝트 루트를 기준으로 경로를 구성한다.

- 환경 진단: `uv run <프로젝트루트>/.claude/scripts/setup_check.py <프로젝트루트>`

## 인자 처리

`$ARGUMENTS`를 파싱하여 동작을 결정한다.

| 입력 | 동작 |
|---|---|
| (인자 없음) | 전체 진단 + 실패 항목 순서대로 수정 |
| `check`, `status`, `상태` | 진단만 수행, 수정 없음 |
| `p1` | P1만 설치 (uv sync + pnpm install) |
| `p2` | P2만 설치 (uv sync + pnpm install + lean) |
| `lean` | Lean 환경만 설정 (Docker + 데이터) |
| `mcp` | MCP 서버 시작만 |

## 실행 순서

### Step 1: 프로젝트 파일 확인

먼저 `pwd`로 프로젝트 루트를 확인하고 `<프로젝트루트>` 변수로 저장한다.

`<프로젝트루트>/.claude/scripts/setup_check.py`가 없으면:
→ "플러그인 파일이 설치되지 않았습니다. `npx @koreainvestment/kis-quant-plugin init --agent claude --force`를 실행하세요."

`.claude/settings.json`이 없거나 `statusLine` 키가 없으면:
→ `bash <프로젝트루트>/.claude/scripts/create_settings.sh <프로젝트루트>` 실행

파일을 새로 생성한 경우 "Claude 설정 완료! Claude를 재시작하면 statusLine이 적용됩니다."라고 안내한다.
이미 있으면 이 단계는 건너뛴다.

### Step 2: 환경 진단

`setup_check.py <프로젝트루트>`를 실행하여 JSON 결과를 받는다.

결과를 아래 형식의 상태 표로 정리하여 사용자에게 보여준다:

| 항목 | 상태 | 비고 |
|---|---|---|
| Python 3.11+ | ✅ | 3.13.3 |
| uv | ✅ | |
| Node.js 18+ | ✅ | 20.10.0 |
| npm | ✅ | |
| Docker | ✅ | 실행 중 |
| KIS 설정파일 | ✅ | 모의+실전 |
| P1 의존성 | ❌ | 프론트엔드 미설치 |
| P2 의존성 | ❌ | 프론트엔드 미설치 |
| Lean 환경 | ❌ | 워크스페이스 없음 |
| P2 .env | ❌ | |
| MCP 서버 | ❌ | 연결 실패 |
| 인증 | ✅ | 모의투자 |

`all_ok`이 `true`면 "모든 설정이 완료되었습니다!"라고 안내하고 종료한다.
`check` / `status` 인자면 표만 보여주고 종료한다.

### Step 3: 사전 요구사항 (prereqs 실패 시)

`checks.prereqs`에서 실패한 항목별로 설치 방법을 안내한다.

| 항목 | 안내 |
|---|---|
| Python | `brew install python@3.11` 또는 공식 사이트 안내 |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | `brew install node` 또는 nvm 안내 |
| npm | Node.js와 함께 설치됨 |
| Docker 미설치 | https://www.docker.com/products/docker-desktop 안내 |
| Docker 미실행 | "Docker Desktop을 시작해주세요" 안내 후 대기, 사용자가 확인하면 재진단 |

사전 요구사항이 하나라도 실패하면, 사용자에게 안내 후 **해결될 때까지 다음 단계로 넘어가지 않는다**.

### Step 4: KIS 설정파일 (kis_config 실패 시)

`~/KIS/config/kis_devlp.yaml` 파일이 없거나 키가 부족하면 안내한다.

1. 디렉토리 생성: `mkdir -p ~/KIS/config`
2. 아래 템플릿을 보여주고 사용자가 직접 작성하도록 안내:

```yaml
my_app: "실전투자 앱키"
my_sec: "실전투자 앱시크릿"
paper_app: "모의투자 앱키"
paper_sec: "모의투자 앱시크릿"
my_htsid: "HTS ID"
my_acct_stock: "증권계좌 8자리"
my_paper_stock: "모의투자 증권계좌 8자리"
my_prod: "01"
```

- **절대로 config 파일을 직접 읽거나 쓰지 않는다** (보안 정책).
- 앱키/시크리트는 [한국투자증권 Open API 포털](https://apiportal.koreainvestment.com/)에서 발급받는다.
- 최소한 `paper_app`, `paper_sec`이 있어야 모의투자가 가능하다.
- 사용자가 "완료했다"고 할 때까지 대기한다.

### Step 5: P1 의존성 설치 (p1_deps 실패 시)

순서대로 실행한다:

1. Python 의존성: `cd <프로젝트루트>/strategy_builder && uv sync`
2. 프론트엔드 의존성: `cd <프로젝트루트>/strategy_builder/frontend && pnpm install`
3. 프론트엔드 환경변수: `strategy_builder/frontend/.env.local`이 없으면 생성:
   `cp <프로젝트루트>/strategy_builder/frontend/.env.example <프로젝트루트>/strategy_builder/frontend/.env.local`
   > ⚠️ 호가창 WebSocket(실시간 호가)을 사용하려면 `.env.local`의 `NEXT_PUBLIC_API_URL=http://localhost:8000` 설정이 필수입니다.

각 단계의 성공/실패를 알려준다.

### Step 6: P2 의존성 설치 (p2_deps 실패 시)

순서대로 실행한다:

1. Python 의존성: `cd <프로젝트루트>/backtester && uv sync`
2. 프론트엔드 의존성: `cd <프로젝트루트>/backtester/frontend && pnpm install`

각 단계의 성공/실패를 알려준다.

### Step 7: Lean 환경 설정 (lean 실패 시)

Docker가 실행 중이어야 한다 (Step 3에서 확인됨).

`bash <프로젝트루트>/backtester/scripts/setup_lean_data.sh`를 실행한다.

시간이 오래 걸릴 수 있으므로 사용자에게 "몇 분 소요될 수 있습니다"라고 미리 안내한다.

### Step 8: P2 환경변수 (p2_env 실패 시)

`backtester/.env.example`을 `backtester/.env`로 복사한다:

`cp <프로젝트루트>/backtester/.env.example <프로젝트루트>/backtester/.env`

기본값(MCP_PORT=3846, MCP_HOST=127.0.0.1)이면 수정 불필요하다고 안내한다.

### Step 9: MCP 서버 시작 (mcp 실패 시)

`bash <프로젝트루트>/backtester/scripts/start_mcp.sh`를 **백그라운드로** 실행한다.

시작 후 3초 대기, `http://127.0.0.1:3846/health`로 헬스 체크한다.
응답이 없으면 5초 더 대기 후 재시도한다.

### Step 10: 인증 (auth 실패 시)

인증이 안 되어 있으면 사용자에게 안내한다:

- "모의투자로 시작하려면 `/auth vps`를 실행하세요."
- "실전투자는 `/auth prod`를 실행하세요."

**자동으로 인증을 실행하지 않는다** — 사용자가 모드를 선택해야 한다.

### Step 11: 최종 검증

`setup_check.py`를 다시 실행하여 최종 상태를 확인한다.

모든 항목이 통과하면:
> "Setup 완료! `/my-status`로 계좌를 확인하거나, `/kis-help`로 사용법을 알아보세요."

일부 항목이 아직 실패하면 (예: auth는 사용자가 나중에 하겠다 한 경우):
> 실패 항목만 다시 표시하고, 나중에 `/kis-setup check`로 다시 확인할 수 있다고 안내한다.

## 주의사항

- 토큰, 앱키, 시크리트 등 민감 정보는 **절대 출력하지 않는다**.
- `kis_devlp.yaml` 파일을 **직접 읽거나 쓰지 않는다** (deny 규칙).
- 각 단계는 **멱등(idempotent)**하다 — 이미 완료된 단계는 건너뛴다.
- `setup_check.py`의 JSON 출력만 참조하여 현재 상태를 판단한다.
- Lean 이미지 pull 등 시간이 오래 걸리는 작업은 사전에 안내한다.
