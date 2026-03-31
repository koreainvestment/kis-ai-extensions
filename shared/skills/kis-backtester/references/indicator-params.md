# 지표 YAML 파라미터 레퍼런스

| id | 주요 params | output (다중 출력) | 비고 |
|----|-------------|-------------------|------|
| `sma` | period | — | |
| `ema` | period | — | |
| `rsi` | period | — | 0~100 |
| `macd` | fast, slow, signal | value, signal, histogram | |
| `bollinger` | period, std | upper, middle, lower | `std`(표준편차 배수) |
| `stochastic` | k_period, d_period | k, d | 0~100. 별칭 2개로 분리 |
| `atr` | period | — | |
| `adx` | period | value, plus_di, minus_di | |
| `obv` | — | — | |
| `cci` | period | — | |
| `williams_r` | period | — | -100~0 |
| `mfi` | period | — | 0~100 |
| `vwap` | period | — | |
| `consecutive` | direction | — | direction: up\|down |
| `roc` | period | — | 변화율(%) |
| `ibs` | — | — | (close-low)/(high-low) |
| `std` | period | — | 표준편차 |
| `maximum` | period | — | N일 최고값 |
| `minimum` | period | — | N일 최저값 |
| `natr` | period | — | 정규화 ATR |
| `stochrsi` | rsi_period, stoch_period, k_period, d_period | k, d | |
| `close` | — | — | 조건 `indicator` 필드에 특수값으로 사용 |

> **다중 출력 지표 사용법**: 지표 정의 시 같은 id를 다른 alias로 2개 선언하고 각각 `output` 지정.
> 또는 조건에서 `output`/`compare_output` 필드로 참조.

# YAML 생성 전 체크

- [ ] `strategy.id`: snake_case, 영문+숫자+_ 조합
- [ ] 모든 indicator `alias` 고유 (같은 지표 2개 사용 시 별도 alias 필수)
- [ ] 조건의 `indicator` 값이 indicators 목록의 alias 또는 `close`와 일치
- [ ] 다중 출력 지표(`macd`, `bollinger`, `stochastic`)는 `output`/`compare_output` 필드 명시
- [ ] `compare_to`와 `value` 동시 사용 금지 (하나만)
- [ ] `risk.stop_loss/take_profit`: `{enabled: true, percent: X.0}` 형식
- [ ] `version: "1.0"` 고정
- [ ] 파일 저장 전 기존 파일 덮어쓰기 여부 사용자 확인
