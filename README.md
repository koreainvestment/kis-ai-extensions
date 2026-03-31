KIS Plugin은 [한국투자증권 Open API](https://github.com/koreainvestment/open-trading-api)의 **전략 설계 → 백테스팅 → 주문 실행** 파이프라인을 AI 코딩 에이전트에서 자연어로 조작할 수 있게 해주는 플러그인입니다.

Claude Code, Cursor, Codex, Gemini CLI 등 주요 AI 에이전트에서 자연어로 전략 설계 → 백테스팅 → 주문 실행을 조작할 수 있게 해주는 플러그인입니다.

## Features

- **전략 설계** — 10개 프리셋 전략 + 80개 기술지표 조합으로 `.kis.yaml` 생성
- **백테스팅** — Docker 기반 QuantConnect Lean 엔진으로 과거 검증, 파라미터 최적화, HTML 리포트
- **신호 기반 주문** — BUY/SELL/HOLD 신호 + 강도(0~1) 확인 후 모의/실전 주문
- **보안 훅** — appkey/token 유출 차단, 실전 주문 시 사용자 확인 강제
- **MCP 서버** — 백테스팅 엔진과 AI 에이전트를 연결하는 MCP 서버 제공

## Installation

### Quick Install (npx / bunx)

`open-trading-api` 레포 안에서 한 줄로 설치할 수 있습니다.

```bash
git clone https://github.com/koreainvestment/open-trading-api
cd open-trading-api
npx @koreainvestment/kis-quant-plugin init --agent claude
# or
bunx @koreainvestment/kis-quant-plugin init --agent claude
```

| 커맨드 | 역할 |
|--------|------|
| `npx @koreainvestment/kis-quant-plugin init --agent claude` | Claude Code 설치 |
| `npx @koreainvestment/kis-quant-plugin init --agent cursor` | Cursor 설치 |
| `npx @koreainvestment/kis-quant-plugin init --agent codex` | Codex 설치 |
| `npx @koreainvestment/kis-quant-plugin init --agent gemini` | Gemini CLI 설치 |
| `npx @koreainvestment/kis-quant-plugin init --agent all` | 모든 에이전트 설치 |
| `npx @koreainvestment/kis-quant-plugin init --force` | 기존 파일 덮어쓰기 |
| `npx @koreainvestment/kis-quant-plugin doctor` | 환경 진단 |
| `npx @koreainvestment/kis-quant-plugin update` | 최신 버전 확인 |

### Prerequisites

이 플러그인은 [open-trading-api](https://github.com/koreainvestment/open-trading-api) 메인 레포의 `strategy_builder/`와 `backtester/`를 활용합니다.

```bash
git clone https://github.com/koreainvestment/open-trading-api
cd open-trading-api
uv sync
```

| 항목 | 설치 | 용도 |
|------|------|------|
| Python 3.11+ | [python.org](https://www.python.org/) | strategy_builder, backtester |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | 의존성 관리 |
| Node.js 18+ | [nodejs.org](https://nodejs.org/) | 프론트엔드 UI |
| Docker Desktop | [docker.com](https://www.docker.com/products/docker-desktop) | 백테스팅 (Lean 엔진) |
| KIS Open API | [서비스 신청](https://apiportal.koreainvestment.com/about-howto) | 앱키/시크릿 발급 |

### 에이전트별 설치 후 구조

모든 에이전트는 자급자족(self-contained) 구조입니다. 플러그인 파일이 에이전트 디렉토리 안에 모두 포함됩니다.

**Claude Code** (`npx @koreainvestment/kis-quant-plugin init --agent claude`)
```
.claude/
  scripts/     # api_client.py, auth.py, do_auth.py, setup_check.py, create_settings.sh
  skills/      # kis-strategy-builder, kis-backtester, kis-order-executor, kis-team, kis-cs
  commands/    # auth.md, kis-setup.md, kis-help.md, my-status.md
  hooks/       # kis-secret-guard.sh, kis-prod-guard.sh, kis-trade-log.sh, kis-mcp-log.sh, hooks.json
  status_lines/  # kis_status_line.py
  logs/
.mcp.json      # MCP 서버 설정
AGENTS.md      # 에이전트 가이드
```

**Cursor** (`npx @koreainvestment/kis-quant-plugin init --agent cursor`)
```
.cursor/
  scripts/     # api_client.py, auth.py, do_auth.py, setup_check.py
  skills/      # kis-strategy-builder, kis-backtester, kis-order-executor, kis-team, kis-cs
  commands/    # auth.md, kis-setup.md, kis-help.md, my-status.md
  hooks/       # cursor/secret-scan.sh, cursor/session-log.sh, hooks.json
  rules/       # kis-safety.mdc
  logs/
.mcp.json
AGENTS.md
```

**Codex** (`npx @koreainvestment/kis-quant-plugin init --agent codex`)
```
.codex/
  scripts/     # api_client.py, auth.py, do_auth.py, setup_check.py
  skills/      # kis-strategy-builder, ..., kis-cs, auth, kis-setup, kis-help, my-status
  config.toml  # MCP 서버 + skill 경로 설정
  rules/       # default.rules
  logs/
codex-local.sh
AGENTS.md
```

**Gemini CLI** (`npx @koreainvestment/kis-quant-plugin init --agent gemini`)
```
.gemini/
  scripts/     # api_client.py, auth.py, do_auth.py, setup_check.py
  skills/      # kis-strategy-builder, kis-backtester, kis-order-executor, kis-team, kis-cs
  commands/    # auth.toml, kis-setup.toml, kis-help.toml, my-status.toml
  hooks/       # kis-secret-guard.sh, kis-prod-guard.sh, kis-trade-log.sh, kis-mcp-log.sh
  settings.json  # MCP + hooks 설정
  logs/
gemini-extension.json
AGENTS.md
```

설치 후 각 에이전트에서:
1. `/kis-setup`으로 환경 진단
2. `/auth vps` 또는 `/auth prod`로 인증
3. `/my-status`로 계좌 확인

## Skills

플러그인이 설치되면, AI 에이전트가 사용자의 의도에 따라 아래 스킬을 자동으로 활성화합니다.

| Skill | 트리거 예시 | 설명 |
|-------|------------|------|
| **kis-strategy-builder** | "전략 만들어줘", "RSI+MACD 조합" | 10개 프리셋 + 80개 지표로 `.kis.yaml` 전략 설계 |
| **kis-backtester** | "백테스트 해줘", "수익률 확인" | Lean 엔진 백테스팅, 파라미터 최적화, HTML 리포트 |
| **kis-order-executor** | "신호 확인해줘", "모의투자 실행" | BUY/SELL/HOLD 신호 확인 후 모의/실전 주문 |
| **kis-team** | "다 해줘", "전략부터 주문까지" | Step 1→2→3 풀파이프라인 (단계별 사용자 확인) |
| **kis-cs** | 사용법 문의, 오류 발생 | 고객 서비스 스타일 안내 + 오류코드 해석 |

### 10개 프리셋 전략

`kis-strategy-builder`와 `kis-backtester` 양쪽에서 동일하게 지원합니다.

| # | 전략명 | 유형 | 한줄 설명 |
|---|--------|------|-----------|
| 01 | 골든크로스 | 추세추종 | 단기 이동평균이 장기 이동평균을 상향 돌파하면 매수 |
| 02 | 모멘텀 | 추세추종 | 최근 N일 수익률이 높은 종목을 매수 |
| 03 | 52주 신고가 | 돌파매매 | 종가가 52주 최고가를 갱신하면 매수 |
| 04 | 연속 상승/하락 | 추세추종 | N일 연속 종가 상승 시 매수, N일 연속 하락 시 매도 |
| 05 | 이격도 | 역추세 | 종가/이동평균 비율로 과열(매도)·침체(매수) 판단 |
| 06 | 돌파 실패 | 손절 | 전고점 돌파 후 다시 아래로 빠지면 손절 |
| 07 | 강한 종가 | 모멘텀 | 종가가 당일 고가 근처에서 마감하면 매수 |
| 08 | 변동성 확장 | 돌파매매 | 변동성이 줄어든 뒤 급등하면 매수 |
| 09 | 평균회귀 | 역추세 | 가격이 평균에서 크게 벗어나면 반대 방향으로 매매 |
| 10 | 추세 필터 | 추세추종 | 장기 이동평균 위에서 상승 중이면 매수 |

## Commands

AI 에이전트 채팅창에서 슬래시 커맨드를 사용합니다.

| 커맨드 | 동작 |
|--------|------|
| `/auth` | KIS API 인증 (기본: 모의투자) |
| `/auth prod` | 실전투자 인증 |
| `/auth ws` | WebSocket 실시간 시세용 인증 |
| `/auth switch` | 모의↔실전 전환 |
| `/my-status` | 잔고 + 보유종목 + 코스피/코스닥 지수 |
| `/kis-setup` | 환경 자동 진단 및 설정 |
| `/kis-help` | 사용법 안내 + 오류코드 검색 |

## MCP Server

백테스팅 엔진은 MCP(Model Context Protocol) 서버로 동작하며, AI 에이전트가 백테스트를 실행할 수 있게 합니다.

```json
{
  "mcpServers": {
    "kis-backtest": {
      "type": "http",
      "url": "http://127.0.0.1:3846/mcp"
    }
  }
}
```

MCP 서버 시작:

```bash
bash backtester/scripts/start_mcp.sh
```

### MCP Tools

| 도구 | 설명 |
|------|------|
| `run_backtest` | 프리셋 또는 `.kis.yaml` 전략으로 백테스트 실행 |
| `optimize_params` | Grid/Random 파라미터 최적화 |
| `get_report` | HTML 리포트 조회 |
| `list_strategies` | 사용 가능한 전략 목록 |

## Security

플러그인은 자격 증명 유출 방지를 위해 다중 보안 계층을 적용합니다. 보안 훅은 에이전트별로 분리되어 있습니다.

**Claude Code** (`.claude/hooks/hooks.json`)

| 훅 | 이벤트 | 동작 |
|----|--------|------|
| `kis-secret-guard` | PreToolUse | appkey/appsecret/token 하드코딩 즉시 차단 |
| `kis-prod-guard` | PreToolUse | 실전(prod) 모드 주문 시 사용자 확인 요구 |
| `kis-trade-log` | PostToolUse | 모든 거래 활동을 로그에 기록 |
| `kis-mcp-log` | PostToolUse | 백테스트/최적화 MCP 호출 로깅 |

**Gemini CLI** (`.gemini/settings.json`)

| 훅 | 이벤트 | 동작 |
|----|--------|------|
| `kis-secret-guard` | BeforeTool | appkey/appsecret/token 하드코딩 즉시 차단 |
| `kis-prod-guard` | BeforeTool | 실전(prod) 모드 주문 시 사용자 확인 요구 |
| `kis-trade-log` | AfterTool | 모든 거래 활동을 로그에 기록 |
| `kis-mcp-log` | AfterTool | 백테스트/최적화 MCP 호출 로깅 |

**Cursor** (`.cursor/hooks/hooks.json`)

| 훅 | 이벤트 | 동작 |
|----|--------|------|
| `secret-scan` | afterAgentResponse | 에이전트 응답에서 secret 패턴 사후 감지 |
| `session-log` | stop | 세션 종료 시 거래 활동 요약 로깅 |

> Cursor는 도구 호출 전 가로채기를 지원하지 않으므로, 주문 안전장치는 `.cursor/rules/kis-safety.mdc` 규칙으로 대체됩니다.

**안전 규칙:**
- 신호 강도 0.5 미만 → 주문 자동 건너뜀
- 실전(prod) 주문 → 종목/수량/예상금액 표시 후 반드시 사용자 승인
- `appkey`, `appsecret`, 토큰 등 민감 정보 출력 금지

## Usage Examples

### 전략 설계

```
> 골든크로스 전략 만들어줘
> RSI 30 이하에서 매수, 70 이상에서 매도하는 전략 설계해줘
> MACD + 볼린저밴드 조합 전략 만들어줘
```

### 백테스팅

```
> 삼성전자로 1년치 백테스트 해줘
> 골든크로스 전략 파라미터 최적화 해줘
> 최근 6개월 수익률 확인해줘
```

### 신호 확인 및 주문

```
> 삼성전자 신호 확인해줘
> 모의투자로 실행해줘
> 전략부터 주문까지 다 해줘
```

## Troubleshooting

### 토큰 오류

```
/auth vps     # 모의투자 재인증
/auth prod    # 실전투자 재인증
```

### MCP 서버 연결 실패

```bash
# MCP 서버 시작
bash backtester/scripts/start_mcp.sh

# Docker 상태 확인
docker info
docker images | grep lean
```

### 초당 거래건수 초과 (`EGW00201`)

모의투자 계좌는 REST API 호출 제한이 낮습니다. 파라미터 최적화 등 연속 호출이 많으면 실전투자 계좌를 권장합니다.

### 오류코드 검색

```
/kis-help EGW00201
```

## Links

- [한국투자증권 Open API 메인 레포](https://github.com/koreainvestment/open-trading-api)
- [KIS Developers 포털](https://apiportal.koreainvestment.com/)
- [KIS Open API 챗봇](https://chatgpt.com/g/g-68b920ee7afc8191858d3dc05d429571-hangugtujajeunggweon-open-api-seobiseu-gpts)
