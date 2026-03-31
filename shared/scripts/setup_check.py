#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///

"""
KIS Setup Check - 프로젝트 환경 진단

8개 카테고리를 검사하여 JSON으로 결과를 출력한다.
prereqs, kis_config, p1_deps, p2_deps, lean, p2_env, mcp, auth

보안: 토큰, 앱키, 시크리트 등 민감 값은 절대 출력하지 않음.

Usage:
  uv run setup_check.py                # 전체 검사
  uv run setup_check.py /path/to/root  # 프로젝트 루트 지정
"""

import base64
import json
import re
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


def _find_project_root() -> Path:
    """프로젝트 루트를 결정한다. 인자 > 스크립트 위치 기반."""
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if p.is_dir():
            return p.resolve()
    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT = _find_project_root()
CONFIG_ROOT = Path.home() / "KIS" / "config"
CONFIG_FILE = CONFIG_ROOT / "kis_devlp.yaml"


# ── stdlib YAML 파서 (auth.py 동일 패턴, PEP 723 제약으로 인라인) ──────

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


# ── 유틸 ──────────────────────────────────────────────────────────

def _run(cmd: list[str], timeout: int = 10) -> tuple[int, str]:
    """subprocess 실행. (returncode, stdout) 반환."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode, r.stdout.strip()
    except FileNotFoundError:
        return -1, ""
    except subprocess.TimeoutExpired:
        return -2, ""
    except Exception:
        return -99, ""


def _parse_version(text: str) -> str:
    """버전 문자열에서 숫자 부분만 추출."""
    m = re.search(r"(\d+\.\d+[\.\d]*)", text)
    return m.group(1) if m else ""


def _version_ge(version: str, minimum: str) -> bool:
    """version >= minimum 비교 (major.minor)."""
    try:
        v_parts = [int(x) for x in version.split(".")[:2]]
        m_parts = [int(x) for x in minimum.split(".")[:2]]
        return v_parts >= m_parts
    except (ValueError, IndexError):
        return False


# ── 1. Prerequisites ─────────────────────────────────────────────

def check_prereqs() -> dict:
    result: dict = {"ok": True}

    # Python
    py_rc, py_out = _run([sys.executable, "--version"])
    py_ver = _parse_version(py_out) if py_rc == 0 else ""
    py_ok = _version_ge(py_ver, "3.11") if py_ver else False
    result["python"] = {"ok": py_ok, "version": py_ver}

    # uv
    uv_rc, uv_out = _run(["uv", "--version"])
    uv_ok = uv_rc == 0
    result["uv"] = {"ok": uv_ok}

    # Node.js
    node_rc, node_out = _run(["node", "--version"])
    node_ver = _parse_version(node_out) if node_rc == 0 else ""
    node_ok = _version_ge(node_ver, "18") if node_ver else False
    result["node"] = {"ok": node_ok, "version": node_ver}

    # npm
    npm_rc, _ = _run(["npm", "--version"])
    result["npm"] = {"ok": npm_rc == 0}

    # Docker installed
    docker_rc, _ = _run(["docker", "--version"])
    docker_installed = docker_rc == 0

    # Docker daemon running
    docker_running = False
    if docker_installed:
        di_rc, _ = _run(["docker", "info"], timeout=15)
        docker_running = di_rc == 0

    result["docker"] = {
        "ok": docker_installed and docker_running,
        "installed": docker_installed,
        "running": docker_running,
    }

    result["ok"] = all([
        py_ok, uv_ok, node_ok, npm_rc == 0,
        docker_installed and docker_running,
    ])
    return result


# ── 2. KIS Config ────────────────────────────────────────────────

def check_kis_config() -> dict:
    if not CONFIG_FILE.exists():
        return {"ok": False, "exists": False, "has_paper": False, "has_prod": False}

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

    has_paper = {"paper_app", "paper_sec"}.issubset(found_keys)
    has_prod = {"my_app", "my_sec"}.issubset(found_keys)
    return {
        "ok": has_paper,
        "exists": True,
        "has_paper": has_paper,
        "has_prod": has_prod,
    }


# ── 3. P1 Dependencies ──────────────────────────────────────────

def check_p1_deps() -> dict:
    p1 = PROJECT_ROOT / "strategy_builder"
    py_ok = (p1 / ".venv").is_dir() or (p1 / "uv.lock").exists()
    fe_ok = (p1 / "frontend" / "node_modules").is_dir()
    return {"ok": py_ok and fe_ok, "python": py_ok, "frontend": fe_ok}


# ── 4. P2 Dependencies ──────────────────────────────────────────

def check_p2_deps() -> dict:
    p2 = PROJECT_ROOT / "backtester"
    py_ok = (p2 / ".venv").is_dir() or (p2 / "uv.lock").exists()
    fe_ok = (p2 / "frontend" / "node_modules").is_dir()
    return {"ok": py_ok and fe_ok, "python": py_ok, "frontend": fe_ok}


# ── 5. Lean Environment ─────────────────────────────────────────

def check_lean() -> dict:
    ws = PROJECT_ROOT / "backtester" / ".lean-workspace"
    workspace_ok = ws.is_dir()

    mh = ws / "data" / "market-hours" / "market-hours-database.json"
    sp = ws / "data" / "symbol-properties" / "symbol-properties-database.csv"
    data_ok = mh.exists() and sp.exists()

    image_ok = False
    rc, out = _run(["docker", "images", "-q", "quantconnect/lean:latest"])
    if rc == 0 and out.strip():
        image_ok = True

    return {
        "ok": workspace_ok and data_ok and image_ok,
        "workspace": workspace_ok,
        "image": image_ok,
        "data": data_ok,
    }


# ── 6. P2 .env ──────────────────────────────────────────────────

def check_p2_env() -> dict:
    env_file = PROJECT_ROOT / "backtester" / ".env"
    return {"ok": env_file.exists()}


# ── 7. MCP Server ────────────────────────────────────────────────

def check_mcp() -> dict:
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:3846/health", method="GET",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                return {"ok": True}
            return {"ok": False, "reason": f"status_{resp.status}"}
    except urllib.error.URLError:
        return {"ok": False, "reason": "connection_refused"}
    except Exception as e:
        return {"ok": False, "reason": str(type(e).__name__)}


# ── 8. Auth (auth.py 로직 재사용) ────────────────────────────────

def check_auth() -> dict:
    def _token_file() -> Path:
        today = CONFIG_ROOT / f"KIS{datetime.now().strftime('%Y%m%d')}"
        if today.exists():
            return today
        from datetime import timedelta
        yesterday = CONFIG_ROOT / f"KIS{(datetime.now() - timedelta(days=1)).strftime('%Y%m%d')}"
        return yesterday if yesterday.exists() else today

    tf = _token_file()
    if not tf.exists():
        return {"ok": False, "reason": "no_token"}

    data = _read_yaml_keys(tf, {"token", "valid-date"})
    token_val = data.get("token", "")
    valid_date = data.get("valid-date", "")
    if not token_val or not valid_date:
        return {"ok": False, "reason": "invalid_format"}

    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if valid_date <= now_str:
            return {"ok": False, "reason": "expired"}
    except Exception:
        return {"ok": False, "reason": "parse_error"}

    # 모드 판별 (jti = appkey)
    try:
        payload_b64 = token_val.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        jti = payload.get("jti", "")
    except Exception:
        jti = ""

    mode = "unknown"
    if jti:
        cfg = _read_yaml_keys(CONFIG_FILE, {"my_app", "paper_app"})
        if jti == cfg.get("my_app"):
            mode = "prod"
        elif jti == cfg.get("paper_app"):
            mode = "vps"

    return {"ok": True, "mode": mode}


# ── Main ─────────────────────────────────────────────────────────

def get_setup_status() -> dict:
    checks = {
        "prereqs": check_prereqs(),
        "kis_config": check_kis_config(),
        "p1_deps": check_p1_deps(),
        "p2_deps": check_p2_deps(),
        "lean": check_lean(),
        "p2_env": check_p2_env(),
        "mcp": check_mcp(),
        "auth": check_auth(),
    }

    passed = sum(1 for c in checks.values() if c["ok"])
    total = len(checks)
    all_ok = passed == total

    next_steps = [k for k, v in checks.items() if not v["ok"]]

    return {
        "all_ok": all_ok,
        "checks": checks,
        "summary": f"{passed}/{total} passed",
        "next_steps": next_steps,
        "project_root": str(PROJECT_ROOT),
        "ts": datetime.now().isoformat(),
    }


def main():
    print(json.dumps(get_setup_status(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
