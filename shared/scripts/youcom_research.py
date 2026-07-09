#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///

"""
You.com 리서치/검색 - 종목·시장·뉴스 리서치.

stdlib only (urllib). 민감 값(API 키)은 절대 stdout에 출력하지 않음.

API 키는 환경변수 YDC_API_KEY 에서만 읽는다 (https://you.com/platform/api-keys 발급).

Usage:
  uv run youcom_research.py search "<검색어>" [--count N]   # 웹/뉴스 검색 (기본 10, 최대 20)
  uv run youcom_research.py research "<검색어>"             # 심층 리서치 (요약 + 출처)
"""

import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

SEARCH_URL = "https://ydc-index.io/v1/search"
RESEARCH_URL = "https://api.you.com/v1/research"

DEFAULT_COUNT = 10
MAX_COUNT = 20
TIMEOUT_SECONDS = 15
# research/lite는 응답까지 수십 초가 걸릴 수 있어 검색보다 긴 타임아웃을 둔다.
RESEARCH_TIMEOUT_SECONDS = 120

# api.you.com은 Cloudflare 뒤에 있어 Python 기본 User-Agent(Python-urllib/*)를
# 403으로 차단한다. 브라우저 형태의 UA를 붙여 모든 요청에서 통과시킨다
# (search 호스트에는 무해, research 호스트에는 필수).
BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

ERR_NO_KEY = (
    "YDC_API_KEY 환경변수가 설정되지 않았습니다. "
    "https://you.com/platform/api-keys 에서 발급 후 설정하세요."
)


# ---------------------------------------------------------------------------
# API 키
# ---------------------------------------------------------------------------

def _get_api_key() -> str:
    """환경변수에서만 키를 읽는다. 절대 로그/출력하지 않음."""
    return os.environ.get("YDC_API_KEY", "") or ""


# ---------------------------------------------------------------------------
# 오류 처리 - 민감 값 노출 없는 고정 한국어 메시지로만 변환
# ---------------------------------------------------------------------------

def _clean_error(exc: BaseException) -> str:
    """예외를 안전한 고정 한국어 메시지로 변환한다.

    원본 예외 문자열(응답 바디, URL 등)은 절대 그대로 반환하지 않는다 -
    서버가 에러 메시지에 요청 값을 반사(echo)하더라도 유출되지 않도록 함.
    """
    if isinstance(exc, urllib.error.HTTPError):
        code = exc.code
        if code == 401:
            return "인증 실패 (401): API 키를 확인하세요."
        if code == 403:
            return "접근 거부 (403): API 키 권한 또는 요청 경로를 확인하세요."
        if code == 422:
            return "잘못된 요청 파라미터입니다 (422)."
        if code == 429:
            return "요청 한도를 초과했습니다 (429). 잠시 후 다시 시도하세요."
        if 500 <= code < 600:
            return f"서버 오류가 발생했습니다 ({code}). 잠시 후 다시 시도하세요."
        return f"HTTP 오류가 발생했습니다 ({code})."
    if isinstance(exc, TimeoutError):
        return "요청 시간이 초과되었습니다. 네트워크 상태를 확인 후 다시 시도하세요."
    if isinstance(exc, json.JSONDecodeError):
        return "응답을 해석할 수 없습니다 (형식 오류)."
    if isinstance(exc, urllib.error.URLError):
        # 타임아웃은 URLError(TimeoutError)로 감싸져 오는 경우도 있음
        if isinstance(getattr(exc, "reason", None), TimeoutError):
            return "요청 시간이 초과되었습니다. 네트워크 상태를 확인 후 다시 시도하세요."
        return "네트워크 연결 오류가 발생했습니다."
    return "요청 처리 중 오류가 발생했습니다."


# ---------------------------------------------------------------------------
# 실제 HTTP 호출 (urllib, stdlib only) - 테스트 시 주입 가능
# ---------------------------------------------------------------------------

def _http_request(url: str, headers: dict, data: bytes | None = None, method: str = "GET") -> dict:
    """실제 네트워크 호출. 성공 시 파싱된 JSON dict 반환, 실패 시 예외 발생."""
    merged = {"User-Agent": BROWSER_UA}
    merged.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=merged, method=method)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=_timeout_for(url)) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body.strip() else {}


def _timeout_for(url: str) -> int:
    """research 호스트는 응답이 느리므로 더 긴 타임아웃을 사용한다."""
    return RESEARCH_TIMEOUT_SECONDS if str(url).startswith(RESEARCH_URL) else TIMEOUT_SECONDS


# ---------------------------------------------------------------------------
# 검색 (search) - GET https://ydc-index.io/v1/search
# ---------------------------------------------------------------------------

def _normalize_count(count) -> int:
    try:
        c = int(count)
    except (TypeError, ValueError):
        return DEFAULT_COUNT
    if c <= 0:
        return DEFAULT_COUNT
    if c > MAX_COUNT:
        return MAX_COUNT
    return c


def do_search(query, count=DEFAULT_COUNT, http=_http_request) -> dict:
    """You.com 웹 검색. http는 (url, headers, data=None, method="GET") -> dict 시그니처의
    주입 가능한 콜러블 (테스트 시 네트워크 대체용)."""
    api_key = _get_api_key()
    if not api_key:
        return {"error": ERR_NO_KEY}

    q = "" if query is None else str(query)
    c = _normalize_count(count)
    params = {"query": q, "count": c}
    url = f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"
    headers = {"X-API-Key": api_key}

    try:
        raw = http(url, headers)
    except Exception as e:  # noqa: BLE001 - 모든 예외를 안전한 메시지로 변환
        return {"error": _clean_error(e)}
    finally:
        api_key = ""

    # 응답에서 필요한 필드만 취하고 나머지는 버린다 (심층 방어: http 콜러블이
    # 예상치 못한 값을 반환하더라도 그 값이 그대로 전파/출력되지 않도록 함).
    if not isinstance(raw, dict):
        return {"error": "응답 형식이 올바르지 않습니다."}
    return {"results": raw.get("results")}


# ---------------------------------------------------------------------------
# 리서치 (research) - POST https://api.you.com/v1/research
# ---------------------------------------------------------------------------

def do_research(query, http=_http_request) -> dict:
    """You.com 심층 리서치. http는 do_search와 동일한 시그니처."""
    api_key = _get_api_key()
    if not api_key:
        return {"error": ERR_NO_KEY}

    q = "" if query is None else str(query)
    body = json.dumps({"input": q, "research_effort": "lite"}).encode("utf-8")
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

    try:
        raw = http(RESEARCH_URL, headers, body, "POST")
    except Exception as e:  # noqa: BLE001
        return {"error": _clean_error(e)}
    finally:
        api_key = ""

    if not isinstance(raw, dict):
        return {"error": "응답 형식이 올바르지 않습니다."}

    # 실제 research 응답 형태: {"output": {"content": str, "sources": [...]}}
    output = raw.get("output")
    if not isinstance(output, dict):
        output = {}
    content = output.get("content")
    sources = output.get("sources")

    # 200이라도 사용 가능한 content가 없으면 실패로 처리한다 (조용한 exit 0 방지).
    if not (isinstance(content, str) and content.strip()):
        return {"error": "리서치 결과를 가져오지 못했습니다."}

    return {"content": content, "sources": sources}


# ---------------------------------------------------------------------------
# 출력 포맷 (순수 함수 - I/O 없음, 테스트 용이)
# ---------------------------------------------------------------------------

def _clean_str(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def _format_item(idx: int, item: dict) -> list:
    title = _clean_str(item.get("title")) or "(제목 없음)"
    url = _clean_str(item.get("url"))
    desc = _clean_str(item.get("description"))

    lines = [f"{idx}. {title}"]
    if url:
        lines.append(f"   URL: {url}")
    if desc:
        lines.append(f"   설명: {desc}")

    snippets = item.get("snippets")
    if isinstance(snippets, list):
        for s in snippets:
            cs = _clean_str(s)
            if cs:
                lines.append(f"   - {cs}")
    return lines


def format_search(data, count=DEFAULT_COUNT) -> str:
    """검색 결과 dict를 한국어 번호 매김 텍스트로 변환. I/O 없는 순수 함수."""
    if not isinstance(data, dict):
        return "검색 결과가 없습니다."

    error = data.get("error")
    if error:
        return f"검색 실패: {error}"

    results = data.get("results")
    if not isinstance(results, dict):
        return "검색 결과가 없습니다."

    lines = []

    web = results.get("web")
    if isinstance(web, list) and web:
        lines.append("[웹 검색 결과]")
        idx = 0
        for item in web:
            if not isinstance(item, dict):
                continue
            idx += 1
            lines.extend(_format_item(idx, item))

    news = results.get("news")
    if isinstance(news, list) and news:
        if lines:
            lines.append("")
        lines.append("[뉴스 검색 결과]")
        idx = 0
        for item in news:
            if not isinstance(item, dict):
                continue
            idx += 1
            lines.extend(_format_item(idx, item))

    if not lines:
        return "검색 결과가 없습니다."

    return "\n".join(lines)


def format_research(data) -> str:
    """리서치 결과 dict를 한국어 텍스트(요약 + 출처 목록)로 변환. I/O 없는 순수 함수."""
    if not isinstance(data, dict):
        return "리서치 결과가 없습니다."

    error = data.get("error")
    if error:
        return f"리서치 실패: {error}"

    content = _clean_str(data.get("content"))
    lines = [content] if content else ["리서치 결과가 없습니다."]

    sources = data.get("sources")
    if isinstance(sources, list):
        valid = []
        for src in sources:
            if isinstance(src, dict):
                title = _clean_str(src.get("title"))
                url = _clean_str(src.get("url"))
                if title and url:
                    valid.append(f"{title} ({url})")
                elif title:
                    valid.append(title)
                elif url:
                    valid.append(url)
            elif isinstance(src, str):
                cs = src.strip()
                if cs:
                    valid.append(cs)
        if valid:
            lines.append("")
            lines.append("[출처]")
            for i, label in enumerate(valid, start=1):
                lines.append(f"{i}. {label}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _usage() -> str:
    return (
        '사용법: youcom_research.py search "<검색어>" [--count N] '
        '| youcom_research.py research "<검색어>"'
    )


def _parse_count_arg(rest: list) -> int:
    if "--count" in rest:
        i = rest.index("--count")
        if i + 1 < len(rest):
            return _normalize_count(rest[i + 1])
    return DEFAULT_COUNT


def main():
    args = sys.argv[1:]
    if not args:
        print(_usage())
        sys.exit(1)

    cmd = args[0]
    rest = args[1:]

    if cmd == "search":
        if not rest:
            print('사용법: youcom_research.py search "<검색어>" [--count N]')
            sys.exit(1)
        query = rest[0]
        count = _parse_count_arg(rest[1:])
        result = do_search(query, count)
        print(format_search(result, count))
        if result.get("error"):
            sys.exit(1)
    elif cmd == "research":
        if not rest:
            print('사용법: youcom_research.py research "<검색어>"')
            sys.exit(1)
        query = rest[0]
        result = do_research(query)
        print(format_research(result))
        if result.get("error"):
            sys.exit(1)
    else:
        print(f"알 수 없는 명령: {cmd}")
        print(_usage())
        sys.exit(1)


if __name__ == "__main__":
    main()
