#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///

"""
KIS 인증 실행 - REST 토큰 / WebSocket approval_key 발급 / 모드 전환.

stdlib only (urllib). 민감 값은 절대 stdout에 출력하지 않음.

Usage:
  uv run do_auth.py vps          # 모의투자 REST 인증
  uv run do_auth.py prod         # 실전투자 REST 인증
  uv run do_auth.py ws vps       # 모의투자 WebSocket 인증
  uv run do_auth.py ws prod      # 실전투자 WebSocket 인증
  uv run do_auth.py switch       # 현재 모드 반대로 전환 (토큰 삭제 → 재인증)
"""

import json
import ssl
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

CONFIG_ROOT = Path.home() / "KIS" / "config"
CONFIG_FILE = CONFIG_ROOT / "kis_devlp.yaml"


# ---------------------------------------------------------------------------
# YAML parser
# ---------------------------------------------------------------------------

def _parse_yaml_value(raw: str) -> str:
    v = raw.strip()
    if not v:
        return ""
    if v[0] in ('"', "'"):
        quote = v[0]
        end = v.find(quote, 1)
        if end != -1:
            return v[1:end]
        return v[1:]
    idx = v.find(" #")
    if idx != -1:
        v = v[:idx]
    return v.strip()


def _read_yaml_keys(path: Path, keys: set[str]) -> dict[str, str]:
    result = {}
    try:
        for line in path.read_text(encoding="UTF-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or ":" not in stripped:
                continue
            key, _, val = stripped.partition(":")
            k = key.strip()
            if k in keys:
                result[k] = _parse_yaml_value(val)
                if len(result) == len(keys):
                    break
    except Exception:
        pass
    return result


# ---------------------------------------------------------------------------
# Token file helpers
# ---------------------------------------------------------------------------

def _token_file() -> Path:
    """오늘 토큰 파일 우선, 없으면 어제 파일 fallback (자정 이후 만료 전 대응)."""
    today = CONFIG_ROOT / f"KIS{datetime.now().strftime('%Y%m%d')}"
    if today.exists():
        return today
    from datetime import timedelta
    yesterday = CONFIG_ROOT / f"KIS{(datetime.now() - timedelta(days=1)).strftime('%Y%m%d')}"
    return yesterday if yesterday.exists() else today


def _check_existing_token() -> tuple[str, str]:
    """(token, valid-date) 반환. 없거나 만료면 ('', '')."""
    tf = _token_file()
    if not tf.exists():
        return "", ""
    data = _read_yaml_keys(tf, {"token", "valid-date"})
    token_val = data.get("token", "")
    valid_date = data.get("valid-date", "")
    if not token_val or not valid_date:
        return "", ""
    try:
        if valid_date > datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
            return token_val, valid_date
    except Exception:
        pass
    return "", ""


def _today_token_file() -> Path:
    """새 토큰 저장용 - 항상 오늘 날짜."""
    return CONFIG_ROOT / f"KIS{datetime.now().strftime('%Y%m%d')}"


def _save_token(token: str, expires: str) -> None:
    tf = _today_token_file()
    tf.parent.mkdir(parents=True, exist_ok=True)
    valid_date = datetime.strptime(expires, "%Y-%m-%d %H:%M:%S")
    with open(tf, "w", encoding="utf-8") as f:
        f.write(f"token: {token}\n")
        f.write(f"valid-date: {valid_date}\n")


def _delete_token_file() -> bool:
    tf = _token_file()
    if tf.exists():
        tf.unlink()
        return True
    return False


def _detect_current_mode() -> str:
    """현재 토큰의 모드를 JWT jti로 판별. 'prod'|'vps'|''."""
    import base64
    existing_token, _ = _check_existing_token()
    if not existing_token:
        return ""
    try:
        payload_b64 = existing_token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        jti = json.loads(base64.urlsafe_b64decode(payload_b64)).get("jti", "")
    except Exception:
        return ""
    if not jti:
        return ""
    cfg = _read_yaml_keys(CONFIG_FILE, {"my_app", "paper_app"})
    if jti == cfg.get("my_app"):
        return "prod"
    if jti == cfg.get("paper_app"):
        return "vps"
    return ""


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def _post_api(url: str, body: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_credentials(svr: str) -> tuple[str, str, str]:
    """(appkey, appsecret, base_url). 실패 시 빈 문자열."""
    key_app = "my_app" if svr == "prod" else "paper_app"
    key_sec = "my_sec" if svr == "prod" else "paper_sec"
    cfg = _read_yaml_keys(CONFIG_FILE, {key_app, key_sec, svr})
    return cfg.get(key_app, ""), cfg.get(key_sec, ""), cfg.get(svr, "")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _output(success: bool, action: str, mode: str, mode_display: str,
            expires: str = "", error: str = "", **extra):
    result = {
        "success": success,
        "action": action,
        "mode": mode,
        "mode_display": mode_display,
    }
    if expires:
        result["expires"] = expires
    if error:
        result["error"] = error
    result.update(extra)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _mode_display(svr: str) -> str:
    return "실전투자" if svr == "prod" else "모의투자"


# ---------------------------------------------------------------------------
# REST 인증 (토큰 발급)
# ---------------------------------------------------------------------------

def cmd_auth(svr: str) -> None:
    if svr not in ("prod", "vps"):
        _output(False, "auth", svr, "", error="mode는 prod 또는 vps만 가능")
        sys.exit(1)

    display = _mode_display(svr)

    if not CONFIG_FILE.exists():
        _output(False, "auth", svr, display, error="config 파일 없음")
        sys.exit(1)

    existing_token, existing_expires = _check_existing_token()
    if existing_token:
        current_mode = _detect_current_mode()
        if current_mode == svr:
            _output(True, "auth", svr, display, expires=existing_expires)
            return
        # 요청 모드와 다른 토큰 → 삭제 후 재발급
        _delete_token_file()

    appkey, appsecret, base_url = _get_credentials(svr)
    if not appkey or not appsecret or not base_url:
        _output(False, "auth", svr, display, error="config에 필요한 키가 없음")
        sys.exit(1)

    try:
        data = _post_api(f"{base_url}/oauth2/tokenP", {
            "grant_type": "client_credentials",
            "appkey": appkey,
            "appsecret": appsecret,
        })
        access_token = data["access_token"]
        expires = data["access_token_token_expired"]
    except Exception as e:
        err_msg = str(e)
        if any(s in err_msg.lower() for s in ("appkey", "secret", "token", "credential")):
            err_msg = "토큰 발급 실패"
        _output(False, "auth", svr, display, error=err_msg)
        sys.exit(1)
    finally:
        appkey = appsecret = ""

    try:
        _save_token(access_token, expires)
    except Exception:
        _output(False, "auth", svr, display, error="토큰 저장 실패")
        sys.exit(1)
    finally:
        access_token = ""

    _output(True, "auth", svr, display, expires=expires)


# ---------------------------------------------------------------------------
# WebSocket 인증 (approval_key 발급)
# ---------------------------------------------------------------------------

def cmd_auth_ws(svr: str) -> None:
    if svr not in ("prod", "vps"):
        _output(False, "ws", svr, "", error="mode는 prod 또는 vps만 가능")
        sys.exit(1)

    display = _mode_display(svr)

    if not CONFIG_FILE.exists():
        _output(False, "ws", svr, display, error="config 파일 없음")
        sys.exit(1)

    appkey, appsecret, base_url = _get_credentials(svr)
    if not appkey or not appsecret or not base_url:
        _output(False, "ws", svr, display, error="config에 필요한 키가 없음")
        sys.exit(1)

    try:
        data = _post_api(f"{base_url}/oauth2/Approval", {
            "grant_type": "client_credentials",
            "appkey": appkey,
            "secretkey": appsecret,
        })
        approval_key = data["approval_key"]
    except Exception as e:
        err_msg = str(e)
        if any(s in err_msg.lower() for s in ("appkey", "secret", "approval", "credential")):
            err_msg = "WebSocket 인증 실패"
        _output(False, "ws", svr, display, error=err_msg)
        sys.exit(1)
    finally:
        appkey = appsecret = ""

    _output(True, "ws", svr, display, approval_key_issued=True)
    approval_key = ""


# ---------------------------------------------------------------------------
# 모드 전환 (토큰 삭제 → 반대 모드로 재인증)
# ---------------------------------------------------------------------------

def cmd_switch() -> None:
    current = _detect_current_mode()
    if not current:
        _output(False, "switch", "", "미인증",
                error="현재 인증된 토큰이 없음. 먼저 인증 필요")
        sys.exit(1)

    target = "prod" if current == "vps" else "vps"
    display = _mode_display(target)

    _delete_token_file()
    cmd_auth(target)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    if not args:
        print(json.dumps({
            "error": "사용법: do_auth.py [vps|prod] | ws [vps|prod] | switch"
        }, ensure_ascii=False))
        sys.exit(1)

    cmd = args[0]

    if cmd == "ws":
        if len(args) < 2:
            print(json.dumps({"error": "사용법: do_auth.py ws [vps|prod]"}, ensure_ascii=False))
            sys.exit(1)
        cmd_auth_ws(args[1])
    elif cmd == "switch":
        cmd_switch()
    elif cmd in ("vps", "prod"):
        cmd_auth(cmd)
    else:
        print(json.dumps({"error": f"알 수 없는 명령: {cmd}"}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
