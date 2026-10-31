import json

import httpx
import pytest

from olostep_client.client import OlostepClient, OlostepError
from olostep_client.invoke import as_text, to_int


def make_client(handler):
    return OlostepClient("test-key", transport=httpx.MockTransport(handler), sleep=lambda _: None)


def test_requires_api_key():
    with pytest.raises(OlostepError, match="API key"):
        OlostepClient("  ")


def test_scrape_sends_key_and_returns_markdown():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer test-key"
        assert request.url.path == "/v1/scrapes"
        assert json.loads(request.content) == {"url_to_scrape": "https://example.com", "formats": ["markdown"]}
        return httpx.Response(200, json={"result": {"markdown_content": "# Example"}})

    assert make_client(handler).scrape("https://example.com") == {
        "url": "https://example.com",
        "markdown": "# Example",
    }


def test_rejects_invalid_url():
    with pytest.raises(OlostepError, match="full http"):
        make_client(lambda request: httpx.Response(200, json={})).scrape("example.com")


def test_retries_server_errors_then_succeeds():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"result": {"links": [{"url": "https://a.com"}]}})

    assert make_client(handler).search("q", 5)["results"] == [{"url": "https://a.com"}]
    assert len(calls) == 3


def test_invalid_key_is_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(401, json={"detail": "The provided API key is invalid."})

    with pytest.raises(OlostepError, match="invalid or revoked"):
        make_client(handler).search("q", 5)
    assert len(calls) == 1


def test_error_detail_is_shown():
    def handler(request):
        return httpx.Response(400, json={"detail": "max_pages is required"})

    with pytest.raises(OlostepError, match="HTTP 400\\): max_pages is required"):
        make_client(handler).map("https://example.com", 10)


def test_check_key():
    make_client(lambda request: httpx.Response(404, json={})).check_key()
    with pytest.raises(OlostepError):
        make_client(lambda request: httpx.Response(401, json={})).check_key()


def test_answer_parses_json_content():
    def handler(request):
        content = json.dumps({"result": "Tokyo"})
        return httpx.Response(200, json={"result": {"json_content": content, "sources": ["https://a.com"]}})

    assert make_client(handler).answer("Capital of Japan?") == {
        "task": "Capital of Japan?",
        "answer": "Tokyo",
        "sources": ["https://a.com"],
    }


def test_crawl_waits_pages_through_and_retrieves_markdown():
    statuses = iter(["in_progress", "completed"])

    def handler(request):
        path = request.url.path
        if path == "/v1/crawls" and request.method == "POST":
            assert json.loads(request.content) == {"start_url": "https://example.com", "max_pages": 2}
            return httpx.Response(200, json={"id": "crawl_1"})
        if path == "/v1/crawls/crawl_1":
            return httpx.Response(200, json={"status": next(statuses)})
        if path == "/v1/crawls/crawl_1/pages":
            if "cursor" not in request.url.params:
                return httpx.Response(200, json={"pages": [{"url": "https://example.com", "retrieve_id": "r1"}], "cursor": 1})
            return httpx.Response(200, json={"pages": [{"url": "https://example.com/a", "retrieve_id": "r2"}], "cursor": None})
        if path == "/v1/retrieve":
            return httpx.Response(200, json={"markdown_content": f"page {request.url.params['retrieve_id']}"})
        raise AssertionError(f"unexpected request {request.method} {path}")

    result = make_client(handler).crawl("https://example.com", 2, 60)
    assert result == {
        "id": "crawl_1",
        "status": "completed",
        "pages": [
            {"url": "https://example.com", "markdown": "page r1"},
            {"url": "https://example.com/a", "markdown": "page r2"},
        ],
    }


def test_batch_returns_id_when_still_running():
    def handler(request):
        if request.method == "POST":
            items = json.loads(request.content)["items"]
            assert items == [{"custom_id": "0", "url": "https://a.com"}, {"custom_id": "1", "url": "https://b.com"}]
            return httpx.Response(200, json={"id": "batch_1"})
        return httpx.Response(200, json={"status": "in_progress"})

    result = make_client(handler).batch_scrape(["https://a.com", "https://b.com"], 0)
    assert result["status"] == "in_progress"
    assert result["id"] == "batch_1"


def test_results_requires_known_id():
    with pytest.raises(OlostepError, match="crawl or batch id"):
        make_client(lambda request: httpx.Response(200, json={})).results("job_1", 0)


def test_retrieve_error_is_kept_per_page():
    def handler(request):
        if request.url.path == "/v1/batches/batch_1":
            return httpx.Response(200, json={"status": "completed"})
        if request.url.path == "/v1/batches/batch_1/items":
            return httpx.Response(200, json={"items": [{"url": "https://a.com", "retrieve_id": "r1"}], "cursor": None})
        return httpx.Response(400, json={"detail": "not found"})

    page = make_client(handler).results("batch_1", 0)["pages"][0]
    assert page["markdown"] is None
    assert "not found" in page["error"]


def test_to_int_clamps():
    assert to_int("500", 10, 1, 100) == 100
    assert to_int(None, 10, 1, 100) == 10
    assert to_int(0, 10, 1, 100) == 1


def test_as_text():
    assert as_text({"url": "u", "markdown": "# Hi"}) == "# Hi"
    assert as_text({"pages": [{"url": "u", "markdown": "body"}]}) == "## u\n\nbody"
    assert json.loads(as_text({"query": "q", "results": []})) == {"query": "q", "results": []}
