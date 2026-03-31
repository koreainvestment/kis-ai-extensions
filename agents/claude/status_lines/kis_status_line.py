#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///

"""
KIS Status Line - [한국투자증권] [모의|실전|미인증] | yyyy-mm-dd(요일) | 만료:HH:MM

auth.py의 JSON 출력을 기반으로 포맷된 status line 표시.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CYAN = "\033[36m"
YELLOW = "\033[33m"
BRIGHT_RED = "\033[91m"
BRIGHT_BLUE = "\033[38;5;33m"
DIM = "\033[90m"
RED = "\033[31m"
RESET = "\033[0m"

BRAND = "한국투자증권"
DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]

MODE_COLORS = {
    "vps": CYAN,
    "prod": BRIGHT_RED,
    "unknown": YELLOW,
    "none": DIM,
}

AUTH_SCRIPT = Path(__file__).parent.parent / "scripts" / "auth.py"


def get_auth_status() -> dict:
    try:
        result = subprocess.run(
            ["uv", "run", str(AUTH_SCRIPT)],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return {"authenticated": False, "mode": "none", "mode_display": "미인증", "token": {}}


def format_status_line(status: dict) -> str:
    mode = status.get("mode", "none")
    mode_display = status.get("mode_display", "미인증")
    color = MODE_COLORS.get(mode, YELLOW)

    now = datetime.now()
    day = DAY_NAMES[now.weekday()]

    parts = [
        f"{BRIGHT_BLUE}［{BRAND}］{RESET}",
        f"{color}［{mode_display}］{RESET}",
        f"{DIM}{now.strftime('%Y-%m-%d')}（{day}）{RESET}",
    ]

    expires = status.get("token", {}).get("expires", "")
    if status.get("authenticated") and expires:
        try:
            exp_dt = datetime.strptime(expires, "%Y-%m-%d %H:%M:%S")
            remaining = exp_dt - now
            hours = int(remaining.total_seconds()) // 3600
            mins = (int(remaining.total_seconds()) % 3600) // 60
            parts.append(f"{DIM}만료:{exp_dt.strftime('%m/%d %H:%M')}（{hours}h{mins:02d}m남음）{RESET}")
        except Exception:
            parts.append(f"{DIM}만료:{expires[:16]}{RESET}")

    return " | ".join(parts)


def main():
    try:
        sys.stdin.read()
    except Exception:
        pass

    status = get_auth_status()
    print(format_status_line(status))


if __name__ == "__main__":
    main()
