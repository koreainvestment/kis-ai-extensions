"""
shared/scripts/youcom_research.py 단위 테스트 (stdlib unittest + mock, 네트워크 없음).

실행:
  python3 -m unittest test.test_youcom_research -v
  (또는 저장소 루트에서) python3 -m unittest discover -s test -p "test_*.py" -v

중점 검증:
  - format_search / format_research: 순수 함수, 다양한 입력 방어
  - do_search / do_research: 주입된 http 콜러블로 요청 구성(URL, 헤더, 바디) 검증
  - 오류 경로: 키 없음, 401/403/422/429/5xx, 타임아웃, JSON 파싱 실패, 빈 응답
  - 보안: API 키가 어떤 경로(성공/실패)에서도 절대 출력/반환되지 않음
"""

import importlib.util
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "shared" / "scripts" / "youcom_research.py"

_spec = importlib.util.spec_from_file_location("youcom_research", SCRIPT_PATH)
yr = importlib.util.module_from_spec(_spec)
sys.modules["youcom_research"] = yr
_spec.loader.exec_module(yr)


FAKE_KEY = "sk-TEST-super-secret-do-not-leak-9f8e7d6c"


def make_http_error(code, body=""):
    fp = mock.Mock()
    if body:
        fp.read.return_value = body.encode("utf-8")
    else:
        fp.read.return_value = b""
    return urllib.error.HTTPError(
        url="https://ydc-index.io/v1/search", code=code, msg="err", hdrs=None, fp=fp
    )


# ---------------------------------------------------------------------------
# format_search
# ---------------------------------------------------------------------------

class TestFormatSearch(unittest.TestCase):
    def test_web_results_present(self):
        data = {
            "results": {
                "web": [
                    {"title": "삼성전자 실적", "url": "https://a.com", "description": "설명1",
                     "snippets": ["스니펫1", "스니펫2"]},
                    {"title": "삼성전자 뉴스", "url": "https://b.com", "description": "설명2"},
                ]
            }
        }
        out = yr.format_search(data)
        self.assertIn("[웹 검색 결과]", out)
        self.assertIn("1. 삼성전자 실적", out)
        self.assertIn("URL: https://a.com", out)
        self.assertIn("설명: 설명1", out)
        self.assertIn("- 스니펫1", out)
        self.assertIn("- 스니펫2", out)
        self.assertIn("2. 삼성전자 뉴스", out)

    def test_news_results_present(self):
        data = {"results": {"news": [{"title": "뉴스 제목", "url": "https://n.com", "description": "d"}]}}
        out = yr.format_search(data)
        self.assertIn("[뉴스 검색 결과]", out)
        self.assertIn("1. 뉴스 제목", out)

    def test_web_and_news_both_present(self):
        data = {
            "results": {
                "web": [{"title": "W", "url": "https://w.com", "description": ""}],
                "news": [{"title": "N", "url": "https://n.com", "description": ""}],
            }
        }
        out = yr.format_search(data)
        self.assertIn("[웹 검색 결과]", out)
        self.assertIn("[뉴스 검색 결과]", out)
        # web section should come first
        self.assertLess(out.index("[웹 검색 결과]"), out.index("[뉴스 검색 결과]"))

    def test_both_absent(self):
        data = {"results": {}}
        self.assertEqual(yr.format_search(data), "검색 결과가 없습니다.")

    def test_results_none(self):
        data = {"results": None}
        self.assertEqual(yr.format_search(data), "검색 결과가 없습니다.")

    def test_web_none(self):
        data = {"results": {"web": None, "news": None}}
        self.assertEqual(yr.format_search(data), "검색 결과가 없습니다.")

    def test_missing_results_key_entirely(self):
        self.assertEqual(yr.format_search({}), "검색 결과가 없습니다.")

    def test_data_not_dict(self):
        self.assertEqual(yr.format_search(None), "검색 결과가 없습니다.")
        self.assertEqual(yr.format_search("oops"), "검색 결과가 없습니다.")
        self.assertEqual(yr.format_search([1, 2, 3]), "검색 결과가 없습니다.")

    def test_missing_each_field(self):
        data = {"results": {"web": [{}]}}
        out = yr.format_search(data)
        self.assertIn("(제목 없음)", out)
        self.assertNotIn("URL:", out)
        self.assertNotIn("설명:", out)

    def test_empty_and_blank_snippets_filtered(self):
        data = {"results": {"web": [{"title": "T", "snippets": ["", "   ", "실제내용", None, 123]}]}}
        out = yr.format_search(data)
        self.assertIn("- 실제내용", out)
        # blank/empty/non-str snippets must not produce stray bullet lines
        lines = [l for l in out.splitlines() if l.strip().startswith("-")]
        self.assertEqual(lines, ["   - 실제내용"])

    def test_non_dict_items_in_web_list_skipped(self):
        data = {"results": {"web": ["not-a-dict", 42, None, {"title": "OK"}]}}
        out = yr.format_search(data)
        self.assertIn("1. OK", out)
        self.assertNotIn("2.", out)

    def test_unicode_korean_preserved(self):
        data = {"results": {"web": [{"title": "한글 제목 테스트 🇰🇷", "description": "설명입니다"}]}}
        out = yr.format_search(data)
        self.assertIn("한글 제목 테스트 🇰🇷", out)
        self.assertIn("설명입니다", out)

    def test_error_field_short_circuits(self):
        data = {"error": "무언가 실패", "results": {"web": [{"title": "안보임"}]}}
        out = yr.format_search(data)
        self.assertEqual(out, "검색 실패: 무언가 실패")
        self.assertNotIn("안보임", out)


# ---------------------------------------------------------------------------
# format_research
# ---------------------------------------------------------------------------

class TestFormatResearch(unittest.TestCase):
    def test_content_and_sources(self):
        data = {
            "content": "삼성전자는 최근 실적이 개선되었습니다.",
            "sources": [
                {"title": "출처1", "url": "https://s1.com"},
                {"title": "출처2", "url": "https://s2.com"},
            ],
        }
        out = yr.format_research(data)
        self.assertIn("삼성전자는 최근 실적이 개선되었습니다.", out)
        self.assertIn("[출처]", out)
        self.assertIn("1. 출처1 (https://s1.com)", out)
        self.assertIn("2. 출처2 (https://s2.com)", out)

    def test_sources_as_plain_strings(self):
        data = {"content": "c", "sources": ["https://x.com", "", "  ", "https://y.com"]}
        out = yr.format_research(data)
        self.assertIn("1. https://x.com", out)
        self.assertIn("2. https://y.com", out)
        self.assertNotIn("3.", out)

    def test_source_missing_title_or_url(self):
        data = {"content": "c", "sources": [{"url": "https://only-url.com"}, {"title": "only title"}, {}]}
        out = yr.format_research(data)
        self.assertIn("1. https://only-url.com", out)
        self.assertIn("2. only title", out)
        self.assertNotIn("3.", out)  # empty dict source contributes nothing

    def test_no_sources(self):
        data = {"content": "내용만 있음"}
        out = yr.format_research(data)
        self.assertEqual(out, "내용만 있음")
        self.assertNotIn("[출처]", out)

    def test_empty_content_no_sources(self):
        self.assertEqual(yr.format_research({}), "리서치 결과가 없습니다.")
        self.assertEqual(yr.format_research({"content": ""}), "리서치 결과가 없습니다.")
        self.assertEqual(yr.format_research({"content": "   "}), "리서치 결과가 없습니다.")

    def test_data_not_dict(self):
        self.assertEqual(yr.format_research(None), "리서치 결과가 없습니다.")
        self.assertEqual(yr.format_research(42), "리서치 결과가 없습니다.")

    def test_error_field_short_circuits(self):
        data = {"error": "리서치 오류", "content": "안보임"}
        out = yr.format_research(data)
        self.assertEqual(out, "리서치 실패: 리서치 오류")
        self.assertNotIn("안보임", out)

    def test_unicode_korean(self):
        data = {"content": "한글 리서치 내용 결과"}
        self.assertEqual(yr.format_research(data), "한글 리서치 내용 결과")


# ---------------------------------------------------------------------------
# do_search - request construction via injected http
# ---------------------------------------------------------------------------

class TestDoSearch(unittest.TestCase):
    def setUp(self):
        self.env_patcher = mock.patch.dict("os.environ", {"YDC_API_KEY": FAKE_KEY})
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def test_url_and_header_and_default_count(self):
        captured = {}

        def fake_http(url, headers, data=None, method="GET"):
            captured["url"] = url
            captured["headers"] = headers
            captured["data"] = data
            captured["method"] = method
            return {"results": {"web": []}}

        yr.do_search("삼성전자", http=fake_http)
        self.assertIn("ydc-index.io/v1/search", captured["url"])
        self.assertIn("query=", captured["url"])
        self.assertIn("count=10", captured["url"])
        self.assertEqual(captured["headers"]["X-API-Key"], FAKE_KEY)
        self.assertIsNone(captured["data"])

    def test_query_is_url_encoded(self):
        captured = {}

        def fake_http(url, headers, data=None, method="GET"):
            captured["url"] = url
            return {}

        yr.do_search("삼성전자 뉴스", http=fake_http)
        # raw Korean text/space must not appear unescaped
        self.assertNotIn(" ", captured["url"])

    def test_count_explicit(self):
        captured = {}

        def fake_http(url, headers, data=None, method="GET"):
            captured["url"] = url
            return {}

        yr.do_search("q", count=5, http=fake_http)
        self.assertIn("count=5", captured["url"])

    def test_count_capped_at_20(self):
        captured = {}

        def fake_http(url, headers, data=None, method="GET"):
            captured["url"] = url
            return {}

        yr.do_search("q", count=999, http=fake_http)
        self.assertIn("count=20", captured["url"])

    def test_count_invalid_falls_back_to_default(self):
        for bad in ["abc", None, [], {}, 0, -5]:
            captured = {}

            def fake_http(url, headers, data=None, method="GET"):
                captured["url"] = url
                return {}

            yr.do_search("q", count=bad, http=fake_http)
            self.assertIn("count=10", captured["url"], f"failed for count={bad!r}")

    def test_returns_http_result_passthrough(self):
        def fake_http(url, headers, data=None, method="GET"):
            return {"results": {"web": [{"title": "hit"}]}}

        result = yr.do_search("q", http=fake_http)
        self.assertEqual(result["results"]["web"][0]["title"], "hit")


class TestDoSearchAdversarialQuery(unittest.TestCase):
    def setUp(self):
        self.env_patcher = mock.patch.dict("os.environ", {"YDC_API_KEY": FAKE_KEY})
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def test_whitespace_query(self):
        def fake_http(url, headers, data=None, method="GET"):
            return {}
        result = yr.do_search("   ", http=fake_http)
        self.assertNotIn("error", result)

    def test_huge_query_no_crash(self):
        def fake_http(url, headers, data=None, method="GET"):
            return {}
        huge = "가" * 50000
        result = yr.do_search(huge, http=fake_http)
        self.assertNotIn("error", result)

    def test_non_string_query_no_crash(self):
        def fake_http(url, headers, data=None, method="GET"):
            return {}
        for q in [12345, None, ["list"], {"k": "v"}]:
            result = yr.do_search(q, http=fake_http)
            self.assertNotIn("error", result, f"failed for query={q!r}")


# ---------------------------------------------------------------------------
# do_search - error paths
# ---------------------------------------------------------------------------

class TestDoSearchErrors(unittest.TestCase):
    def test_missing_key_no_network_call(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            if "YDC_API_KEY" in __import__("os").environ:
                del __import__("os").environ["YDC_API_KEY"]

            called = {"n": 0}

            def fake_http(*a, **kw):
                called["n"] += 1
                return {}

            result = yr.do_search("q", http=fake_http)
            self.assertEqual(called["n"], 0)
            self.assertIn("YDC_API_KEY", result["error"])

    def _run_with_key(self, http):
        with mock.patch.dict("os.environ", {"YDC_API_KEY": FAKE_KEY}):
            return yr.do_search("q", http=http)

    def test_http_401(self):
        def fake_http(url, headers, data=None, method="GET"):
            raise make_http_error(401)
        result = self._run_with_key(fake_http)
        self.assertIn("401", result["error"])

    def test_http_403(self):
        def fake_http(url, headers, data=None, method="GET"):
            raise make_http_error(403)
        result = self._run_with_key(fake_http)
        self.assertIn("403", result["error"])

    def test_http_422(self):
        def fake_http(url, headers, data=None, method="GET"):
            raise make_http_error(422)
        result = self._run_with_key(fake_http)
        self.assertIn("422", result["error"])

    def test_http_429(self):
        def fake_http(url, headers, data=None, method="GET"):
            raise make_http_error(429)
        result = self._run_with_key(fake_http)
        self.assertIn("429", result["error"])

    def test_http_500(self):
        def fake_http(url, headers, data=None, method="GET"):
            raise make_http_error(500)
        result = self._run_with_key(fake_http)
        self.assertIn("500", result["error"])

    def test_http_503(self):
        def fake_http(url, headers, data=None, method="GET"):
            raise make_http_error(503)
        result = self._run_with_key(fake_http)
        self.assertIn("503", result["error"])

    def test_timeout(self):
        def fake_http(url, headers, data=None, method="GET"):
            raise TimeoutError("timed out")
        result = self._run_with_key(fake_http)
        self.assertIn("시간", result["error"])

    def test_url_error_timeout_reason(self):
        def fake_http(url, headers, data=None, method="GET"):
            raise urllib.error.URLError(TimeoutError("timed out"))
        result = self._run_with_key(fake_http)
        self.assertIn("시간", result["error"])

    def test_url_error_generic(self):
        def fake_http(url, headers, data=None, method="GET"):
            raise urllib.error.URLError("connection refused")
        result = self._run_with_key(fake_http)
        self.assertIn("네트워크", result["error"])

    def test_malformed_json(self):
        def fake_http(url, headers, data=None, method="GET"):
            raise json.JSONDecodeError("bad", "doc", 0)
        result = self._run_with_key(fake_http)
        self.assertIn("해석할 수 없습니다", result["error"])

    def test_empty_body_handled_by_http_layer_no_crash(self):
        # simulate what _http_request would return for an empty body
        def fake_http(url, headers, data=None, method="GET"):
            return {}
        result = self._run_with_key(fake_http)
        self.assertEqual(yr.format_search(result), "검색 결과가 없습니다.")

    def test_unexpected_exception_does_not_crash(self):
        def fake_http(url, headers, data=None, method="GET"):
            raise RuntimeError("something unforeseen")
        result = self._run_with_key(fake_http)
        self.assertIn("error", result)
        self.assertIn("오류", result["error"])

    def test_error_message_never_leaks_raw_http_error_body(self):
        # server echoes something suspicious-looking in the error body;
        # our mapping must not surface it verbatim.
        def fake_http(url, headers, data=None, method="GET"):
            raise make_http_error(400, body="您的 X-API-Key 값이 유효하지 않습니다: " + FAKE_KEY)
        result = self._run_with_key(fake_http)
        self.assertNotIn(FAKE_KEY, result["error"])


# ---------------------------------------------------------------------------
# do_research
# ---------------------------------------------------------------------------

class TestDoResearch(unittest.TestCase):
    def setUp(self):
        self.env_patcher = mock.patch.dict("os.environ", {"YDC_API_KEY": FAKE_KEY})
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def test_url_method_header_and_body(self):
        captured = {}

        def fake_http(url, headers, data=None, method="GET"):
            captured["url"] = url
            captured["headers"] = headers
            captured["data"] = data
            captured["method"] = method
            # 실제 응답 형태: content/sources는 output 아래에 중첩됨
            return {"output": {"content": "요약", "content_type": "text", "sources": []}}

        yr.do_research("삼성전자 전망", http=fake_http)
        self.assertEqual(captured["url"], "https://api.you.com/v1/research")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["headers"]["X-API-Key"], FAKE_KEY)
        body = json.loads(captured["data"].decode("utf-8"))
        self.assertEqual(body["input"], "삼성전자 전망")
        self.assertEqual(body["research_effort"], "lite")

    def test_content_and_sources_passthrough(self):
        # 실제 응답 형태: {"output": {"content": ..., "sources": [{url,title,snippets}]}}
        def fake_http(url, headers, data=None, method="GET"):
            return {
                "output": {
                    "content": "결과 내용 [[1]]",
                    "content_type": "text",
                    "sources": [
                        {"url": "https://u.com", "title": "T", "snippets": ["일부 발췌"]},
                    ],
                }
            }

        result = yr.do_research("q", http=fake_http)
        out = yr.format_research(result)
        self.assertIn("결과 내용", out)
        self.assertIn("T (https://u.com)", out)

    def test_top_level_content_is_not_read(self):
        # 회귀 방지: content/sources를 최상위에서 읽던 버그. 최상위에만 있고
        # output 아래에 없으면 실패로 처리되어야 한다 (조용한 빈 결과 금지).
        def fake_http(url, headers, data=None, method="GET"):
            return {"content": "최상위 내용", "sources": [{"title": "X", "url": "https://x.com"}]}

        result = yr.do_research("q", http=fake_http)
        self.assertIn("error", result)
        self.assertNotIn("content", result)

    def test_200_with_empty_content_is_failure(self):
        # 200이지만 output.content가 비면 error를 반환해 main이 non-zero로 종료하도록 함.
        for raw in ({}, {"output": {}}, {"output": {"content": ""}},
                    {"output": {"content": "   "}}, {"output": {"content": None}}):
            def fake_http(url, headers, data=None, method="GET", _r=raw):
                return _r
            result = yr.do_research("q", http=fake_http)
            self.assertIn("error", result, f"expected error for raw={raw!r}")

    def test_missing_key(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            if "YDC_API_KEY" in __import__("os").environ:
                del __import__("os").environ["YDC_API_KEY"]
            called = {"n": 0}

            def fake_http(*a, **kw):
                called["n"] += 1
                return {}

            result = yr.do_research("q", http=fake_http)
            self.assertEqual(called["n"], 0)
            self.assertIn("YDC_API_KEY", result["error"])

    def test_http_errors(self):
        for code in (401, 403, 422, 429, 500):
            def fake_http(url, headers, data=None, method="GET", _c=code):
                raise make_http_error(_c)
            result = yr.do_research("q", http=fake_http)
            self.assertIn(str(code), result["error"])

    def test_timeout(self):
        def fake_http(url, headers, data=None, method="GET"):
            raise TimeoutError()
        result = yr.do_research("q", http=fake_http)
        self.assertIn("시간", result["error"])

    def test_malformed_json(self):
        def fake_http(url, headers, data=None, method="GET"):
            raise json.JSONDecodeError("bad", "doc", 0)
        result = yr.do_research("q", http=fake_http)
        self.assertIn("해석할 수 없습니다", result["error"])

    def test_non_string_query_no_crash(self):
        # 적대적 쿼리로도 예외 없이 dict를 반환해야 한다 (여기선 빈 응답을
        # 흘려 content 부재로 error가 나지만, 크래시하지 않는 것이 핵심).
        def fake_http(url, headers, data=None, method="GET"):
            return {"output": {"content": "ok", "sources": []}}
        for q in [12345, None, ["a"]]:
            result = yr.do_research(q, http=fake_http)
            self.assertIsInstance(result, dict)
            self.assertNotIn("error", result)


# ---------------------------------------------------------------------------
# SECURITY - the key must never appear in ANY output, success or error
# ---------------------------------------------------------------------------

class TestKeyNeverLeaks(unittest.TestCase):
    """core repo rule: '민감 값은 절대 stdout에 출력하지 않음'.

    Every code path (search + research, success + every error kind) is
    exercised here and the resolved API key string is asserted absent from
    every observable output: the returned dict (serialized), format_search
    output, and format_research output.
    """

    def setUp(self):
        self.env_patcher = mock.patch.dict("os.environ", {"YDC_API_KEY": FAKE_KEY})
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def _assert_no_leak(self, result):
        serialized = json.dumps(result, ensure_ascii=False, default=str)
        self.assertNotIn(FAKE_KEY, serialized)
        self.assertNotIn(FAKE_KEY, yr.format_search(result))
        self.assertNotIn(FAKE_KEY, yr.format_research(result))

    def test_success_search(self):
        def fake_http(url, headers, data=None, method="GET"):
            return {"results": {"web": [{"title": "T", "url": "https://x.com"}]}}
        self._assert_no_leak(yr.do_search("q", http=fake_http))

    def test_success_research(self):
        def fake_http(url, headers, data=None, method="GET"):
            return {"output": {"content": "c", "sources": []}}
        self._assert_no_leak(yr.do_research("q", http=fake_http))

    def test_missing_key_path(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            if "YDC_API_KEY" in __import__("os").environ:
                del __import__("os").environ["YDC_API_KEY"]
            self._assert_no_leak(yr.do_search("q", http=lambda *a, **k: {}))
            self._assert_no_leak(yr.do_research("q", http=lambda *a, **k: {}))

    def test_every_http_error_code(self):
        for code in (401, 403, 422, 429, 500, 502, 503):
            def fake_http(url, headers, data=None, method="GET", _c=code):
                raise make_http_error(_c, body=f"error mentions key {FAKE_KEY}")
            self._assert_no_leak(yr.do_search("q", http=fake_http))
            self._assert_no_leak(yr.do_research("q", http=fake_http))

    def test_timeout_and_network_errors(self):
        for exc in (TimeoutError("t"), urllib.error.URLError("boom"),
                    json.JSONDecodeError("bad", "doc", 0), RuntimeError("x")):
            def fake_http(url, headers, data=None, method="GET", _e=exc):
                raise _e
            self._assert_no_leak(yr.do_search("q", http=fake_http))
            self._assert_no_leak(yr.do_research("q", http=fake_http))

    def test_headers_dict_not_echoed_into_result(self):
        # Even if a buggy http callable returned the headers it received,
        # format_* must not surface an X-API-Key-shaped field as content.
        def fake_http(url, headers, data=None, method="GET"):
            return {"results": {"web": []}, "_debug_headers_seen": dict(headers)}
        result = yr.do_search("q", http=fake_http)
        self._assert_no_leak(result)

    def test_request_headers_actually_contain_key_but_output_does_not(self):
        # sanity: prove the key really is sent (so the no-leak assertion above
        # is meaningful and not vacuous), while confirming output is clean.
        seen = {}

        def fake_http(url, headers, data=None, method="GET"):
            seen["headers"] = headers
            return {"results": {"web": []}}

        result = yr.do_search("q", http=fake_http)
        self.assertEqual(seen["headers"]["X-API-Key"], FAKE_KEY)
        self._assert_no_leak(result)


# ---------------------------------------------------------------------------
# _http_request (실제 전송 계층) - User-Agent 주입 + research 타임아웃
# ---------------------------------------------------------------------------

class TestHttpRequestTransport(unittest.TestCase):
    """api.you.com이 Python 기본 UA를 403으로 막으므로 브라우저 UA가 반드시
    모든 요청에 포함되어야 한다. urlopen을 모킹해 전송된 Request를 캡처한다."""

    def _capture(self, url, headers, data=None, method="GET"):
        captured = {}

        class FakeResp:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return False

            def read(self_inner):
                return b"{}"

        def fake_urlopen(req, context=None, timeout=None):
            captured["req"] = req
            captured["timeout"] = timeout
            return FakeResp()

        with mock.patch.object(yr.urllib.request, "urlopen", fake_urlopen):
            yr._http_request(url, headers, data, method)
        return captured

    def test_user_agent_present_on_search(self):
        cap = self._capture(yr.SEARCH_URL + "?query=q", {"X-API-Key": FAKE_KEY})
        req = cap["req"]
        # urllib normalizes header keys to Capitalized form (User-agent)
        ua = req.get_header("User-agent")
        self.assertIsNotNone(ua)
        self.assertIn("Mozilla/5.0", ua)
        self.assertNotIn("Python-urllib", ua)

    def test_user_agent_present_on_research(self):
        cap = self._capture(yr.RESEARCH_URL, {"X-API-Key": FAKE_KEY}, b"{}", "POST")
        ua = cap["req"].get_header("User-agent")
        self.assertIn("Mozilla/5.0", ua)

    def test_api_key_header_preserved_alongside_ua(self):
        cap = self._capture(yr.SEARCH_URL, {"X-API-Key": FAKE_KEY})
        self.assertEqual(cap["req"].get_header("X-api-key"), FAKE_KEY)

    def test_research_uses_longer_timeout(self):
        cap = self._capture(yr.RESEARCH_URL, {"X-API-Key": FAKE_KEY}, b"{}", "POST")
        self.assertEqual(cap["timeout"], yr.RESEARCH_TIMEOUT_SECONDS)

    def test_search_uses_default_timeout(self):
        cap = self._capture(yr.SEARCH_URL + "?query=q", {"X-API-Key": FAKE_KEY})
        self.assertEqual(cap["timeout"], yr.TIMEOUT_SECONDS)


class TestTimeoutSelection(unittest.TestCase):
    def test_timeout_for_research(self):
        self.assertEqual(yr._timeout_for(yr.RESEARCH_URL), yr.RESEARCH_TIMEOUT_SECONDS)
        self.assertGreater(yr.RESEARCH_TIMEOUT_SECONDS, yr.TIMEOUT_SECONDS)

    def test_timeout_for_search(self):
        self.assertEqual(yr._timeout_for(yr.SEARCH_URL + "?query=q"), yr.TIMEOUT_SECONDS)


if __name__ == "__main__":
    unittest.main()
