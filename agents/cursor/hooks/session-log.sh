#!/usr/bin/env bash
# KIS Session Log — Cursor stop hook
# 에이전트 세션 종료 시 거래 활동 요약 로깅
#
# stdin:  {"status": "completed"|"aborted"|"error", "loop_count": N,
#          "conversation_id": "...", "transcript_path": "..."}
# stdout: {} (세션 종료 허용) 또는 {"followup_message": "..."} (계속)

set -euo pipefail

INPUT=$(cat)

LOG_DIR="${CURSOR_PROJECT_DIR:-$(pwd)}/.cursor/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
TODAY="${TIMESTAMP:0:10}"
LOG_FILE="$LOG_DIR/kis-sessions-${TODAY}.log"

read -r STATUS CONV_ID LOOP_COUNT <<< "$(python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
print(data.get('status', 'unknown'),
      data.get('conversation_id', 'unknown'),
      data.get('loop_count', 0))
" <<< "$INPUT" 2>/dev/null || echo "unknown unknown 0")"

TRANSCRIPT_PATH=$(python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
print(data.get('transcript_path') or '')
" <<< "$INPUT" 2>/dev/null || echo "")

TRADE_KEYWORDS=0
if [[ -n "$TRANSCRIPT_PATH" && -f "$TRANSCRIPT_PATH" ]]; then
    TRADE_KEYWORDS=$(python3 -c "
import sys, re
with open(sys.argv[1], 'r', errors='ignore') as f:
    text = f.read()
patterns = [r'/api/orders', r'/api/strategies/execute', r'mcp__kis-backtest']
count = sum(len(re.findall(p, text)) for p in patterns)
print(count)
" "$TRANSCRIPT_PATH" 2>/dev/null || echo "0")
fi

if [[ "$TRADE_KEYWORDS" -gt 0 ]]; then
    echo "[$TIMESTAMP] SESSION | id: ${CONV_ID:0:12} | status: $STATUS | loops: $LOOP_COUNT | trade_refs: $TRADE_KEYWORDS" >> "$LOG_FILE"
else
    echo "[$TIMESTAMP] SESSION | id: ${CONV_ID:0:12} | status: $STATUS | loops: $LOOP_COUNT | no trades" >> "$LOG_FILE"
fi

echo '{}'
exit 0
