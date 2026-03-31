#!/usr/bin/env bash
# KIS Secret Scan — Cursor afterAgentResponse hook
# 에이전트 응답 텍스트에서 KIS secret 패턴을 사후 감지
#
# stdin:  {"text": "...agent response..."}
# stdout: 없음 (fire-and-forget)

set -euo pipefail

INPUT=$(cat)

LOG_DIR="${CURSOR_PROJECT_DIR:-$(pwd)}/.cursor/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
TODAY="${TIMESTAMP:0:10}"
LOG_FILE="$LOG_DIR/kis-hooks-${TODAY}.log"

RESPONSE_TEXT=$(python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
print(data.get('text', ''))
" <<< "$INPUT" 2>/dev/null || echo "")

if [[ -z "$RESPONSE_TEXT" ]]; then
    echo "[$TIMESTAMP] secret-scan | no text | skip" >> "$LOG_FILE"
    exit 0
fi

SECRET_PATTERNS=(
    'appkey\s*=\s*["'"'"'][A-Za-z0-9]{8,}'
    'appsecret\s*=\s*["'"'"'][A-Za-z0-9]{8,}'
    'app_key\s*=\s*["'"'"'][A-Za-z0-9]{8,}'
    'app_secret\s*=\s*["'"'"'][A-Za-z0-9]{8,}'
    'APP_KEY\s*=\s*["'"'"'][A-Za-z0-9]{8,}'
    'APP_SECRET\s*=\s*["'"'"'][A-Za-z0-9]{8,}'
    'authorization:\s*Bearer\s+[A-Za-z0-9._-]{20,}'
    'approval_key\s*=\s*["'"'"'][A-Za-z0-9]{8,}'
)

FOUND=0
for pattern in "${SECRET_PATTERNS[@]}"; do
    MATCH=$(python3 -c "
import sys, re
text = sys.stdin.read()
m = re.search(r'$pattern', text, re.IGNORECASE)
if m:
    print(m.group(0)[:60])
    sys.exit(0)
sys.exit(1)
" <<< "$RESPONSE_TEXT" 2>/dev/null) && {
        echo "[$TIMESTAMP] secret-scan | DETECTED: ${MATCH}" >> "$LOG_FILE"
        echo "[KIS SECURITY] 에이전트 응답에서 secret 패턴 감지: ${MATCH}" >&2
        FOUND=1
    }
done

if [[ $FOUND -eq 0 ]]; then
    echo "[$TIMESTAMP] secret-scan | clean" >> "$LOG_FILE"
fi

exit 0
