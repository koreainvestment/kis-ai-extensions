# 10개 프리셋 YAML 템플릿

`.kis.yaml`로 저장 후 `POST /api/backtest/run-custom`에 사용한다.

### golden_cross
```yaml
version: "1.0"
metadata:
  name: "골든크로스"
  description: "단기 SMA가 장기 SMA 상향 돌파 시 진입 (골든크로스)"
  author: user
  tags: [trend, sma, golden_cross]
strategy:
  id: golden_cross
  category: trend
  params:
    fast_period: {default: 50, type: int}
    slow_period: {default: 200, type: int}
  indicators:
    - id: sma
      alias: fast
      params: {period: $fast_period}
    - id: sma
      alias: slow
      params: {period: $slow_period}
  entry:
    logic: AND
    conditions:
      - {indicator: fast, operator: cross_above, compare_to: slow}
  exit:
    logic: OR
    conditions:
      - {indicator: fast, operator: cross_below, compare_to: slow}
risk:
  stop_loss: {enabled: true, percent: 5.0}
  take_profit: {enabled: true, percent: 15.0}
```

### adx_trend
```yaml
version: "1.0"
metadata:
  name: "ADX 강한 추세 추종"
  description: "ADX 임계치 초과 시 일간 수익률 방향으로 진입"
  author: user
  tags: [trend, adx]
strategy:
  id: adx_trend
  category: trend
  params:
    period: {default: 14, type: int}
    threshold: {default: 25, type: float}
  indicators:
    - id: adx
      alias: adx
      params: {period: $period}
    - id: roc
      alias: daily_roc
      params: {period: 1}
  entry:
    logic: AND
    conditions:
      - {indicator: adx, operator: greater_than, value: $threshold}
      - {indicator: daily_roc, operator: greater_than, value: 0}
  exit:
    logic: OR
    conditions:
      - {indicator: adx, operator: less_than, value: $threshold}
risk:
  stop_loss: {enabled: true, percent: 5.0}
  take_profit: {enabled: true, percent: 15.0}
```

### obv_divergence
```yaml
version: "1.0"
metadata:
  name: "OBV 거래량 추세 확인"
  description: "가격이 이동평균 위에 있을 때 OBV 상승 확인 후 진입"
  author: user
  tags: [volume, obv, trend]
strategy:
  id: obv_divergence
  category: volume
  params:
    period: {default: 20, type: int}
  indicators:
    - id: obv
      alias: obv
    - id: sma
      alias: price_ma
      params: {period: $period}
  entry:
    logic: AND
    conditions:
      - {indicator: close, operator: cross_above, compare_to: price_ma}
  exit:
    logic: OR
    conditions:
      - {indicator: close, operator: cross_below, compare_to: price_ma}
risk:
  stop_loss: {enabled: true, percent: 5.0}
  take_profit: {enabled: true, percent: 10.0}
```

### mfi_oversold
```yaml
version: "1.0"
metadata:
  name: "MFI 과매도 반등"
  description: "MFI 20 이하 상향 돌파 시 진입, 80 이상 하향 돌파 시 청산"
  author: user
  tags: [oscillator, mfi, oversold]
strategy:
  id: mfi_oversold
  category: oscillator
  params:
    period: {default: 14, type: int}
    oversold: {default: 20, type: float}
    overbought: {default: 80, type: float}
  indicators:
    - id: mfi
      alias: mfi
      params: {period: $period}
  entry:
    logic: AND
    conditions:
      - {indicator: mfi, operator: cross_above, value: $oversold}
  exit:
    logic: OR
    conditions:
      - {indicator: mfi, operator: cross_below, value: $overbought}
risk:
  stop_loss: {enabled: true, percent: 5.0}
  take_profit: {enabled: true, percent: 10.0}
```

### vwap_bounce
```yaml
version: "1.0"
metadata:
  name: "VWAP 반등"
  description: "종가가 VWAP 상향 돌파 시 진입, 하향 돌파 시 청산"
  author: user
  tags: [trend, vwap, bounce]
strategy:
  id: vwap_bounce
  category: trend
  params:
    period: {default: 14, type: int}
  indicators:
    - id: vwap
      alias: vwap
      params: {period: $period}
  entry:
    logic: AND
    conditions:
      - {indicator: close, operator: cross_above, compare_to: vwap}
  exit:
    logic: OR
    conditions:
      - {indicator: close, operator: cross_below, compare_to: vwap}
risk:
  stop_loss: {enabled: true, percent: 3.0}
  take_profit: {enabled: true, percent: 8.0}
```

### cci_reversal
```yaml
version: "1.0"
metadata:
  name: "CCI 반전"
  description: "CCI -100 이하에서 상향 돌파 시 진입, 0선 하향 돌파 시 청산"
  author: user
  tags: [oscillator, cci, reversal]
strategy:
  id: cci_reversal
  category: oscillator
  params:
    period: {default: 20, type: int}
    oversold: {default: -100, type: float}
    overbought: {default: 100, type: float}
  indicators:
    - id: cci
      alias: cci
      params: {period: $period}
  entry:
    logic: AND
    conditions:
      - {indicator: cci, operator: cross_above, value: $oversold}
  exit:
    logic: OR
    conditions:
      - {indicator: cci, operator: cross_below, value: 0}
risk:
  stop_loss: {enabled: true, percent: 5.0}
  take_profit: {enabled: true, percent: 10.0}
```

### williams_reversal
```yaml
version: "1.0"
metadata:
  name: "Williams %R 반전"
  description: "Williams %R -80 이하에서 상향 돌파 시 진입, -20 이상 하향 돌파 시 청산"
  author: user
  tags: [oscillator, williams_r, reversal]
strategy:
  id: williams_reversal
  category: oscillator
  params:
    period: {default: 14, type: int}
    oversold: {default: -80, type: float}
    overbought: {default: -20, type: float}
  indicators:
    - id: williams_r
      alias: wr
      params: {period: $period}
  entry:
    logic: AND
    conditions:
      - {indicator: wr, operator: cross_above, value: $oversold}
  exit:
    logic: OR
    conditions:
      - {indicator: wr, operator: cross_below, value: $overbought}
risk:
  stop_loss: {enabled: true, percent: 5.0}
  take_profit: {enabled: true, percent: 10.0}
```

### atr_breakout
```yaml
version: "1.0"
metadata:
  name: "ATR 변동성 돌파"
  description: "일간 변화율이 임계치 초과 시 진입 (ATR 확인용으로 병행 모니터)"
  author: user
  tags: [volatility, atr, breakout]
strategy:
  id: atr_breakout
  category: volatility
  params:
    atr_period: {default: 14, type: int}
    breakout_pct: {default: 3.0, type: float}
  indicators:
    - id: atr
      alias: atr
      params: {period: $atr_period}
    - id: roc
      alias: daily_return
      params: {period: 1}
  entry:
    logic: AND
    conditions:
      - {indicator: daily_return, operator: greater_than, value: $breakout_pct}
  exit:
    logic: AND
    conditions:
      - {indicator: daily_return, operator: less_than, value: 0}
risk:
  stop_loss: {enabled: true, percent: 5.0}
  take_profit: {enabled: true, percent: 12.0}
```

### disparity_mean_revert
```yaml
version: "1.0"
metadata:
  name: "이격도 평균회귀"
  description: "종가가 이동평균 대비 하락 이격 시 매수, 상향 복귀 시 청산"
  author: user
  tags: [mean_reversion, disparity, sma]
strategy:
  id: disparity_mean_revert
  category: mean_reversion
  params:
    period: {default: 20, type: int}
  indicators:
    - id: sma
      alias: ma
      params: {period: $period}
  entry:
    logic: AND
    conditions:
      - {indicator: close, operator: less_than, compare_to: ma}
  exit:
    logic: OR
    conditions:
      - {indicator: close, operator: greater_than, compare_to: ma}
risk:
  stop_loss: {enabled: true, percent: 5.0}
  take_profit: {enabled: true, percent: 10.0}
```

### consecutive_candle
```yaml
version: "1.0"
metadata:
  name: "연속 하락 후 반등"
  description: "일간 변화율 기준 연속 하락 신호 후 반등 시 진입"
  author: user
  tags: [momentum, consecutive, reversal]
strategy:
  id: consecutive_candle
  category: momentum
  params:
    threshold: {default: -1.0, type: float}
  indicators:
    - id: roc
      alias: daily_change
      params: {period: 1}
  entry:
    logic: AND
    conditions:
      - {indicator: daily_change, operator: greater_than, value: 0}
  exit:
    logic: AND
    conditions:
      - {indicator: daily_change, operator: less_than, value: $threshold}
risk:
  stop_loss: {enabled: true, percent: 5.0}
  take_profit: {enabled: true, percent: 8.0}
```
