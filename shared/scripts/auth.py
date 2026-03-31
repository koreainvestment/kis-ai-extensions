#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///

"""
KIS Auth Status - 한국투자증권 인증 상태 확인

p1(builder), p2(backtest) 공통 유틸리티.
hooks, scripts에서 JSON 출력으로 인증 상태를 확인.

모드 판별: JWT jti 필드 = 발급 앱키 → config의 my_app/paper_app과 대조.
kis_auth.py 수정 불필요.

보안: 토큰, 앱키, 시크리트 등 민감 값은 절대 출력하지 않음.

Usage:
  uv run auth.py   # JSON 출력
"""

import base64
import json
import sys
from datetime import datetime
from pathlib import Path

CONFIG_ROOT = Path.home() / "KIS" / "config"
CONFIG_FILE = CONFIG_ROOT / "kis_devlp.yaml"


def _parse_yaml_value(raw: str) -> str:
    """YAML 값에서 인라인 주석 제거 + 따옴표 처리."""
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
    """지정된 key만 읽어서 반환. 불필요한 민감 값 로드 방지."""
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


def _token_file() -> Path:
    """오늘 토큰 파일 우선, 없으면 어제 파일 fallback (자정 이후 만료 전 대응)."""
    today = CONFIG_ROOT / f"KIS{datetime.now().strftime('%Y%m%d')}"
    if today.exists():
        return today
    from datetime import timedelta
    yesterday = CONFIG_ROOT / f"KIS{(datetime.now() - timedelta(days=1)).strftime('%Y%m%d')}"
    return yesterday if yesterday.exists() else today


def _extract_jti(token_raw: str) -> str:
    """JWT에서 jti 필드만 추출. 토큰 원본은 보관하지 않음."""
    try:
        payload_b64 = token_raw.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload.get("jti", "")
    except Exception:
        return ""


def check_token() -> tuple[dict, str]:
    """토큰 유효성 확인. (상태 dict, jti) 반환. 토큰 원본은 반환하지 않음."""
    tf = _token_file()
    if not tf.exists():
        return {"valid": False, "reason": "no_token"}, ""

    data = _read_yaml_keys(tf, {"token", "valid-date"})
    token_val = data.get("token", "")
    valid_date = data.get("valid-date", "")
    if not token_val or not valid_date:
        return {"valid": False, "reason": "invalid_format"}, ""

    jti = _extract_jti(token_val)

    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if valid_date > now_str:
            return {"valid": True, "expires": valid_date}, jti
        return {"valid": False, "reason": "expired", "expired_at": valid_date}, ""
    except Exception:
        return {"valid": False, "reason": "parse_error"}, ""


def detect_mode(jti: str) -> tuple[str, str]:
    """jti(=앱키)와 config의 my_app/paper_app만 대조. 시크리트는 읽지 않음."""
    if not jti:
        return "unknown", "알수없음"

    cfg = _read_yaml_keys(CONFIG_FILE, {"my_app", "paper_app"})
    if jti == cfg.get("my_app"):
        return "prod", "실전투자"
    if jti == cfg.get("paper_app"):
        return "vps", "모의투자"

    return "unknown", "알수없음"


def check_config() -> dict:
    """config 존재 여부와 키 보유 여부만 확인. 값은 읽지 않음."""
    if not CONFIG_FILE.exists():
        return {"exists": False}

    found_keys: set[str] = set()
    target_keys = {"my_app", "my_sec", "paper_app", "paper_sec"}
    try:
        for line in CONFIG_FILE.read_text(encoding="UTF-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or ":" not in stripped:
                continue
            key, _, val = stripped.partition(":")
            k = key.strip()
            if k in target_keys and _parse_yaml_value(val):
                found_keys.add(k)
    except Exception:
        pass

    return {
        "exists": True,
        "has_prod": {"my_app", "my_sec"}.issubset(found_keys),
        "has_paper": {"paper_app", "paper_sec"}.issubset(found_keys),
    }


def get_status() -> dict:
    token_info, jti = check_token()

    if token_info["valid"]:
        mode, mode_display = detect_mode(jti)
    else:
        mode, mode_display = "none", "미인증"

    return {
        "authenticated": token_info["valid"],
        "mode": mode,
        "mode_display": mode_display,
        "token": token_info,
        "config": check_config(),
        "ts": datetime.now().isoformat(),
    }


def main():
    print(json.dumps(get_status(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
