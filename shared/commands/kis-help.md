---
name: kis-help
description: KIS 플러그인 전체 커맨드·에이전트 안내 및 오류코드 조회.
---

# KIS Help

`$ARGUMENTS`가 있으면 해당 키워드로 아래 내용을 필터해서 보여준다.
없으면, "안녕하세요 고객님! 한국투자증권 openapi입니다. 무엇을 도와드릴까요?" 라고 말한 후 어떤 작업을 할 수 있는지(커맨드 설명) 안내한다.

---

## 커맨드 목록

| 커맨드 | 설명 | 예시 |
|--------|------|------|
| `/auth` | 인증 상태 확인·모의/실전 인증·WebSocket 인증·전환 | `/auth vps` `/auth prod` `/auth switch` `/auth ws vps` |
| `/my-status` | 잔고·보유종목·코스피/코스닥 지수 조회 | `/my-status` `/my-status 잔고` `/my-status 전체` |
| `/kis-help` | 이 도움말. 키워드 검색 가능 | `/kis-help EGW00201` `/kis-help 주문` |

---

## 에이전트 목록

에이전트는 트리거 문구를 입력하면 자동 실행된다.

| 트리거 문구 | 에이전트 | 단계 | 주요 기능 |
|------------|----------|------|----------|
| "전략 만들어줘", "YAML 전략", "지표 조합" | **kis-strategy-builder** | Step 1 | 10개 프리셋 또는 커스텀 `.kis.yaml` 생성 |
| "백테스트 해줘", "성과 분석", "수익률 확인" | **kis-backtester** | Step 2 | 과거 성과 검증, 파라미터 최적화, HTML 리포트 |
| "신호 확인", "실행해줘", "매수 신호 있어?" | **kis-order-executor** | Step 3 | 신호 생성(BUY/SELL/HOLD) → 모의/실전 주문 |
| "다 해줘", "풀파이프라인", "전략부터 주문까지" | **kis-team** | Step 1→2→3 | 3단계 전체 자동 오케스트레이션 |

---

## 자주 쓰는 흐름

```
# 처음 시작
/auth vps          → 모의투자 인증
/my-status         → 잔고 확인

# 전략 설계 → 검증 → 실행
"RSI 전략 만들어줘"       → kis-strategy-builder
"백테스트 해줘"           → kis-backtester
"삼성전자 신호 확인해줘"   → kis-order-executor

# 한 번에 다
"전략부터 주문까지 다 해줘" → kis-team
```

---

## 오류코드 참조

### EGW 서버 (REST API Gateway)

| 코드 | 메시지 | 대응 |
|------|--------|------|
| EGW00001 | 일시적 오류 | 재시도 |
| EGW00002 | 서버 에러 | 재시도 |
| EGW00003 | 접근 거부 | AppKey/Secret 확인 |
| EGW00004 | 권한 없는 고객 | KIS 권한 신청 필요 |
| EGW00101 | 유효하지 않은 요청 | 요청 파라미터 확인 |
| EGW00102 | AppKey 누락 | 헤더에 `appkey` 추가 |
| EGW00103 | 유효하지 않은 AppKey | `/auth` 재인증 |
| EGW00104 | AppSecret 누락 | 헤더에 `appsecret` 추가 |
| EGW00105 | 유효하지 않은 AppSecret | `/auth` 재인증 |
| EGW00106 | redirect_uri 누락 | OAuth 파라미터 확인 |
| EGW00107 | 유효하지 않은 redirect_uri | OAuth 설정 확인 |
| EGW00108 | 유효하지 않은 service 구분 | 서비스 구분값 확인 |
| EGW00109 | scope 누락 | OAuth 파라미터 확인 |
| EGW00110 | 유효하지 않은 scope | scope 값 확인 |
| EGW00111 | 유효하지 않은 state | state 파라미터 확인 |
| EGW00112 | 유효하지 않은 grant | grant_type 확인 |
| EGW00113 | response_type 누락 | OAuth 파라미터 추가 |
| EGW00114 | 지원하지 않는 response_type | `code` 또는 `token` 사용 |
| EGW00115 | grant_type 누락 | `authorization_code` 추가 |
| EGW00130 | 유효하지 않은 user | 사용자 정보 확인 |
| EGW00131 | 유효하지 않은 hashkey | hashkey 재발급 |
| EGW00132 | Content-Type 오류 | `application/json` 설정 |
| EGW00201 | **초당 거래건수 초과** | 요청 간격 늘리기 (Rate Limit) |
| EGW00202 | GW 라우팅 오류 | 재시도 |
| EGW00203 | OPS 라우팅 오류 | 재시도 |
| EGW00204 | Internal GW 인스턴스 오류 | 요청 파라미터 확인 |
| EGW00205 | credentials_type 오류 | `Bearer` 토큰 방식 확인 |
| EGW00206 | **API 사용 권한 없음** | KIS OpenAPI 신청 필요 |
| EGW00207 | IP 주소 오류 | 허용 IP 등록 확인 |
| EGW00208 | custtype 오류 | `P`(개인) 또는 `B`(법인) 확인 |
| EGW00209 | seq_no 오류 | 일련번호 확인 |
| EGW00210 | 법인 모의투자 불가 | 법인은 실전만 가능 |
| EGW00211 | personalname 누락 | 고객명 파라미터 추가 |
| EGW00212 | personalphone 누락 | 휴대전화 파라미터 추가 |
| EGW00213 | corpname 누락 / 모의투자 TR 불일치 | TR_ID 확인 (T→V 변환 필요) |
| EGW00300 | GW 라우팅 오류 | 재시도 |

### OPSQ 서버 (OPS Queue)

| 코드 | 메시지 | 대응 |
|------|--------|------|
| OPSQ0001 | 호출 전처리 오류 | 재시도 |
| OPSQ0010 | 호출 결과처리 리소스 부족 | 재시도 (서버 과부하) |
| OPSQ0011 | 호출 결과처리 리소스 부족 | 재시도 |
| OPSQ1002 | 세션 연결 오류 | `/auth` 재인증 |
| OPSQ2000 | 계좌번호 유효성 오류 | 계좌번호 확인 |
| OPSQ2001 | 시장구분코드 오류 | MRKT_DIV_CODE 확인 |
| OPSQ2002 | 필드 길이 오류 | 요청 필드 길이 확인 |
| OPSQ2003 | MCI 전송 데이터 오류 | 재시도 |
| OPSQ3001 | 응답 파싱 오류 | 재시도 |
| OPSQ3002 | 응답 데이터 길이 오류 | 재시도 |
| OPSQ3004 | 문자열 배열 할당 실패 | 재시도 |
| OPSQ9995 | JSON body 없음 | 요청 body 확인 |
| OPSQ9996 | JSON header 없음 | 요청 header 확인 |
| OPSQ9997 | JSON 파싱 오류 | JSON 형식 확인 |
| OPSQ9998 | seq_no 없음 | 일련번호 추가 |
| OPSQ9999 | tr_id 없음 | TR_ID 헤더 추가 |

### OPSP 서버 (WebSocket 구독)

| 코드 | 메시지 | 대응 |
|------|--------|------|
| OPSP0000 | 구독 성공 | 정상 |
| OPSP0001 | 구독 해제 성공 | 정상 |
| OPSP0002 | 이미 구독 중 | 중복 구독 방지 |
| OPSP0003 | 구독 해제 실패 (없는 구독) | 구독 목록 확인 |
| OPSP0007 | 구독 내부 오류 | 재시도 |
| OPSP0008 | **최대 구독 초과** | 기존 구독 해제 후 재시도 |
| OPSP8992 | 유효하지 않은 tr_key | tr_key 값 확인 |
| OPSP8993 | JSON tr_key 파싱 오류 | JSON 형식 확인 |
| OPSP8994 | personalseckey 없음 | WebSocket 인증키 확인 |
| OPSP8995 | appsecret 없음 | appsecret 파라미터 추가 |
| OPSP8996 | **appkey 이미 사용 중** | 기존 WebSocket 연결 종료 후 재연결 |
| OPSP8997 | tr_type 오류 | tr_type 값 확인 |
| OPSP8998 | custtype 오류 | `P`(개인) 또는 `B`(법인) 확인 |
| OPSP8999 | 리소스 할당 실패 | 재시도 |
| OPSP9990 | tr_key 없음 | tr_key 파라미터 추가 |
| OPSP9991 | input 없음 | 요청 input 필드 확인 |
| OPSP9992 | body 없음 | 요청 body 확인 |
| OPSP9993 | 내부 오류 | 재시도 |
| OPSP9994 | 유효하지 않은 appkey | `/auth ws` 재인증 |
| OPSP9995 | 리소스 부족 | 재시도 |
| OPSP9996 | appkey 없음 | appkey 파라미터 추가 |
| OPSP9997 | custtype 없음 | custtype 파라미터 추가 |
| OPSP9998 | header 없음 | 요청 header 확인 |
| OPSP9999 | JSON 파싱 오류 | JSON 형식 확인 |

---

## 자주 발생하는 오류 빠른 참조

| 상황 | 코드 | 해결책 |
|------|------|--------|
| API 너무 빠르게 호출 | EGW00201 | 초당 1건 이하로 제한 |
| 토큰 만료 | EGW00103/105 | `/auth vps` 또는 `/auth prod` 재인증 |
| 모의투자인데 TR_ID가 T로 시작 | EGW00213 | TR_ID를 V로 시작하도록 변경 |
| WebSocket 중복 연결 | OPSP8996 | 기존 연결 종료 후 재연결 |
| WebSocket 구독 한도 초과 | OPSP0008 | 불필요한 구독 해제 |
| 세션 끊김 | OPSQ1002 | `/auth` 재인증 |
