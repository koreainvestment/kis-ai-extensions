#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///

"""
KIS REST API Client - 계좌 조회 (예수금, 보유종목, 지수).

stdlib only (urllib). 민감 값(토큰, 앱키, 시크리트, 계좌번호)은 절대 stdout에 출력하지 않음.

Usage:
  uv run api_client.py balance     # 예수금/잔고
  uv run api_client.py holdings    # 보유종목
  uv run api_client.py index       # 코스피/코스닥 지수
  uv run api_client.py all         # 잔고 + 보유종목 + 지수
"""

import base64
import json
import ssl
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

CONFIG_ROOT = Path.home() / "KIS" / "config"
CONFIG_FILE = CONFIG_ROOT / "kis_devlp.yaml"


# ---------------------------------------------------------------------------
# YAML parser (auth.py, do_auth.py와 동일 - PEP 723 import 불가)
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
# 토큰/모드 판별
# ---------------------------------------------------------------------------

def _token_file() -> Path:
    """오늘 토큰 파일 우선, 없으면 어제 파일 fallback (자정 이후 만료 전 대응)."""
    today = CONFIG_ROOT / f"KIS{datetime.now().strftime('%Y%m%d')}"
    if today.exists():
        return today
    from datetime import timedelta
    yesterday = CONFIG_ROOT / f"KIS{(datetime.now() - timedelta(days=1)).strftime('%Y%m%d')}"
    return yesterday if yesterday.exists() else today


def _read_token() -> str:
    """오늘의 유효 토큰 반환. 없거나 만료면 ''."""
    tf = _token_file()
    if not tf.exists():
        return ""
    data = _read_yaml_keys(tf, {"token", "valid-date"})
    token_val = data.get("token", "")
    valid_date = data.get("valid-date", "")
    if not token_val or not valid_date:
        return ""
    try:
        if valid_date > datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
            return token_val
    except Exception:
        pass
    return ""


def _detect_mode(token: str) -> str:
    """JWT jti로 모드 판별. 'prod'|'vps'|''."""
    try:
        payload_b64 = token.split(".")[1]
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


def _convert_tr_id(tr_id: str, mode: str) -> str:
    """모의투자 시 TR_ID 첫 글자 T/J/C → V 변환."""
    if mode == "vps" and tr_id and tr_id[0] in ("T", "J", "C"):
        return "V" + tr_id[1:]
    return tr_id


# ---------------------------------------------------------------------------
# API 세션 (인증 정보 + API 호출)
# ---------------------------------------------------------------------------

class KISSession:
    """인증된 KIS API 세션. 생성 시 토큰과 모드를 자동 판별."""

    def __init__(self):
        self.token = _read_token()
        if not self.token:
            self._fail("인증 필요. /auth 커맨드로 먼저 인증하세요.")

        self.mode = _detect_mode(self.token)
        if not self.mode:
            self._fail("모드 판별 실패. /auth 커맨드로 재인증하세요.")

        key_app = "my_app" if self.mode == "prod" else "paper_app"
        key_sec = "my_sec" if self.mode == "prod" else "paper_sec"
        key_acct = "my_acct_stock" if self.mode == "prod" else "my_paper_stock"

        cfg = _read_yaml_keys(CONFIG_FILE, {key_app, key_sec, key_acct, self.mode, "my_prod"})

        self._appkey = cfg.get(key_app, "")
        self._appsecret = cfg.get(key_sec, "")
        self._acct = cfg.get(key_acct, "")
        self._prod = cfg.get("my_prod", "01")
        self._base_url = cfg.get(self.mode, "")

        if not all([self._appkey, self._appsecret, self._acct, self._base_url]):
            self._fail("config에 필요한 키가 부족합니다.")

    @staticmethod
    def _fail(msg: str):
        print(json.dumps({"error": msg}, ensure_ascii=False, indent=2))
        sys.exit(1)

    @property
    def acct_masked(self) -> str:
        if len(self._acct) >= 4:
            return self._acct[:4] + "****"
        return "****"

    def get(self, api_path: str, tr_id: str, params: dict) -> dict:
        """GET 요청. 응답 JSON 반환."""
        real_tr_id = _convert_tr_id(tr_id, self.mode)
        url = f"{self._base_url}{api_path}?{urllib.parse.urlencode(params)}"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.token}",
            "appkey": self._appkey,
            "appsecret": self._appsecret,
            "tr_id": real_tr_id,
            "custtype": "P",
        }

        req = urllib.request.Request(url, headers=headers, method="GET")
        ctx = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            err = body[:200] if body else str(e)
            if any(s in err.lower() for s in ("appkey", "secret", "token")):
                err = "API 호출 실패 (인증 오류)"
            return {"error": err, "rt_cd": "-1"}
        except Exception as e:
            return {"error": str(e), "rt_cd": "-1"}


# ---------------------------------------------------------------------------
# 예수금/잔고 조회
# ---------------------------------------------------------------------------

def cmd_balance(session: KISSession) -> dict:
    params = {
        "CANO": session._acct,
        "ACNT_PRDT_CD": session._prod,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    data = session.get(
        "/uapi/domestic-stock/v1/trading/inquire-balance",
        "TTTC8434R",
        params,
    )

    if data.get("rt_cd") != "0":
        return {"error": data.get("msg1", data.get("error", "잔고 조회 실패"))}

    out2 = data.get("output2", [{}])
    summary = out2[0] if out2 else {}

    def _safe_int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0

    def _safe_float(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    deposit = _safe_int(summary.get("dnca_tot_amt"))
    total_eval = _safe_int(summary.get("tot_evlu_amt"))
    purchase = _safe_int(summary.get("pchs_amt_smtl_amt"))
    eval_amount = _safe_int(summary.get("evlu_amt_smtl_amt"))
    profit_loss = _safe_int(summary.get("evlu_pfls_smtl_amt"))
    profit_rate = round(profit_loss / purchase * 100, 2) if purchase else 0.0

    return {
        "account": session.acct_masked,
        "mode": session.mode,
        "mode_display": "실전투자" if session.mode == "prod" else "모의투자",
        "deposit": deposit,
        "total_eval": total_eval,
        "purchase_amount": purchase,
        "eval_amount": eval_amount,
        "profit_loss": profit_loss,
        "profit_rate": profit_rate,
    }


# ---------------------------------------------------------------------------
# 보유종목 조회
# ---------------------------------------------------------------------------

def cmd_holdings(session: KISSession) -> dict:
    params = {
        "CANO": session._acct,
        "ACNT_PRDT_CD": session._prod,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    data = session.get(
        "/uapi/domestic-stock/v1/trading/inquire-balance",
        "TTTC8434R",
        params,
    )

    if data.get("rt_cd") != "0":
        return {"error": data.get("msg1", data.get("error", "보유종목 조회 실패"))}

    def _safe_int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0

    def _safe_float(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    holdings = []
    for item in data.get("output1", []):
        qty = _safe_int(item.get("hldg_qty"))
        if qty <= 0:
            continue
        holdings.append({
            "code": item.get("pdno", ""),
            "name": item.get("prdt_name", ""),
            "qty": qty,
            "avg_price": _safe_int(item.get("pchs_avg_pric", "0").split(".")[0]),
            "current_price": _safe_int(item.get("prpr")),
            "eval_amount": _safe_int(item.get("evlu_amt")),
            "profit_loss": _safe_int(item.get("evlu_pfls_amt")),
            "profit_rate": round(_safe_float(item.get("evlu_pfls_rt", "0")), 2),
        })

    return {
        "account": session.acct_masked,
        "mode": session.mode,
        "mode_display": "실전투자" if session.mode == "prod" else "모의투자",
        "count": len(holdings),
        "holdings": holdings,
    }


# ---------------------------------------------------------------------------
# 코스피/코스닥 지수 조회
# ---------------------------------------------------------------------------

def cmd_index(session: KISSession) -> dict:
    today = datetime.now().strftime("%Y%m%d")

    def _fetch_index(code: str, name: str) -> dict:
        params = {
            "FID_COND_MRKT_DIV_CODE": "U",
            "FID_INPUT_ISCD": code,
            "FID_INPUT_DATE_1": today,
            "FID_INPUT_DATE_2": today,
            "FID_PERIOD_DIV_CODE": "D",
        }
        data = session.get(
            "/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice",
            "FHKUP03500100",
            params,
        )
        if data.get("rt_cd") != "0":
            return {"name": name, "error": data.get("msg1", "조회 실패")}

        out1 = data.get("output1", {})

        def _sf(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        value = _sf(out1.get("bstp_nmix_prpr"))
        prev_close = _sf(out1.get("bstp_nmix_prdy_vrss"))
        change_rate = _sf(out1.get("bstp_nmix_prdy_ctrt"))

        return {
            "name": name,
            "value": value,
            "change": prev_close,
            "change_rate": round(change_rate, 2),
        }

    return {
        "kospi": _fetch_index("0001", "코스피"),
        "kosdaq": _fetch_index("1001", "코스닥"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    if not args:
        print(json.dumps({"error": "사용법: api_client.py [balance|holdings|index|all]"}, ensure_ascii=False))
        sys.exit(1)

    cmd = args[0]
    session = KISSession()
    result = {}

    if cmd == "balance":
        result = cmd_balance(session)
    elif cmd == "holdings":
        result = cmd_holdings(session)
    elif cmd == "index":
        result = cmd_index(session)
    elif cmd == "all":
        result = {
            "balance": cmd_balance(session),
            "holdings": cmd_holdings(session),
            "index": cmd_index(session),
        }
    else:
        result = {"error": f"알 수 없는 명령: {cmd}"}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
