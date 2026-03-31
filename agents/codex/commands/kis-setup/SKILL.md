---
name: kis-setup
description: "KIS 환경을 진단하거나 설치할 때 반드시 사용. '환경 확인', '설치해줘', 'setup', 'kis-setup'이라고 할 때 자동 실행된다."
---

# KIS Setup

## 스크립트 경로

- 환경 진단: `uv run <프로젝트루트>/.codex/scripts/setup_check.py <프로젝트루트>`

## 인자 처리

| 입력 | 동작 |
|---|---|
| (인자 없음) | 전체 진단 + 실패 항목 순서대로 수정 |
| `check`, `status`, `상태` | 진단만 수행, 수정 없음 |
| `p1` | P1만 설치 (uv sync + pnpm install) |
| `p2` | P2만 설치 (uv sync + pnpm install + lean) |
| `lean` | Lean 환경만 설정 |
| `mcp` | MCP 서버 시작만 |

## 실행 순서

### Step 1: 환경 진단

`setup_check.py <프로젝트루트>` 실행 후 상태 표로 출력.
`all_ok`가 `true`면 "모든 설정이 완료되었습니다!"라고 안내 후 종료.

### Step 2: 사전 요구사항 (prereqs 실패 시)

| 항목 | 안내 |
|---|---|
| Python | `brew install python@3.11` 또는 공식 사이트 |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | `brew install node` 또는 nvm |
| Docker 미설치 | docker.com/products/docker-desktop |
| Docker 미실행 | "Docker Desktop을 시작해주세요" 안내 후 대기 |

### Step 3: KIS 설정파일 (kis_config 실패 시)

`~/KIS/config/kis_devlp.yaml` 없으면 아래 템플릿 안내:

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

**절대로 config 파일을 직접 읽거나 쓰지 않는다.**

### Step 4~6: 의존성 및 Lean 환경

- P1: `cd strategy_builder && uv sync` + `cd frontend && pnpm install` + `.env.local` 없으면 생성:
  `cp strategy_builder/frontend/.env.example strategy_builder/frontend/.env.local`
  > ⚠️ 호가창 WebSocket(실시간 호가)을 사용하려면 `.env.local`의 `NEXT_PUBLIC_API_URL=http://localhost:8000` 설정이 필수입니다.
- P2: `cd backtester && uv sync` + `cd frontend && pnpm install`
- Lean: `bash backtester/scripts/setup_lean_data.sh`

### Step 7: MCP 서버

`bash backtester/scripts/start_mcp.sh` 백그라운드 실행 후 `http://127.0.0.1:3846/health` 확인.

### Step 8: 인증

"모의투자로 시작하려면 '인증해줘 vps'를 입력하세요."

## 주의사항

- `kis_devlp.yaml`을 **직접 읽거나 쓰지 않는다**.
- 각 단계는 **멱등(idempotent)** — 이미 완료된 단계는 건너뛴다.
