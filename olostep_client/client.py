"""Olostep REST API client used by the Dify tools."""

import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urlparse

import httpx

API_URL = "https://api.olostep.com/v1"
TIMEOUT = httpx.Timeout(120.0, connect=10.0)
RETRY_STATUSES = (429, 500, 502, 503, 504)
ATTEMPTS = 3
POLL_SECONDS = 10
PAGE_SIZE = 50
RETRIEVE_WORKERS = 8
USER_AGENT = "olostep-dify-plugin/0.1.0"


class OlostepError(Exception):
    """An error whose message is safe to show to Dify users."""


def check_url(value: Any) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise OlostepError(f"Enter a full http(s) URL, for example https://example.com (got {url!r}).")
    return url


def error_message(response: httpx.Response) -> str:
    if response.status_code in (401, 403):
        return "Your Olostep API key is invalid or revoked. Update it in the plugin credentials."
    if response.status_code == 402:
        return "Your Olostep credits are used up. Check your plan at https://www.olostep.com/dashboard."
    try:
        data = response.json()
    except ValueError:
        data = None
    detail = None
    if isinstance(data, dict):
        detail = data.get("detail") or data.get("title") or data.get("message")
    if isinstance(detail, str) and detail:
        return f"Olostep API error (HTTP {response.status_code}): {detail}"
    return f"Olostep API error (HTTP {response.status_code})."


class OlostepClient:
    def __init__(
        self,
        api_key: Any,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        key = str(api_key or "").strip()
        if not key:
            raise OlostepError("Add your Olostep API key in the plugin credentials.")
        self._headers = {"Authorization": f"Bearer {key}", "User-Agent": USER_AGENT}
        self._transport = transport
        self._sleep = sleep

    def _send(self, method: str, path: str, body: Any = None, params: dict | None = None) -> httpx.Response:
        with httpx.Client(timeout=TIMEOUT, transport=self._transport) as client:
            return client.request(method, f"{API_URL}/{path}", headers=self._headers, json=body, params=params)

    def request(self, method: str, path: str, *, body: Any = None, params: dict | None = None) -> dict:
        """Calls the API, retrying rate limits, server errors and network errors."""
        for attempt in range(ATTEMPTS):
            last = attempt == ATTEMPTS - 1
            try:
                response = self._send(method, path, body, params)
            except httpx.HTTPError:
                if last:
                    raise OlostepError("Could not reach the Olostep API. Try again later.") from None
                self._sleep(2 ** (attempt + 1))
                continue
            if response.status_code < 400:
                try:
                    return response.json()
                except ValueError:
                    raise OlostepError("The Olostep API returned an invalid response.") from None
            if response.status_code in RETRY_STATUSES and not last:
                self._sleep(2 ** (attempt + 1))
                continue
            raise OlostepError(error_message(response))
        raise OlostepError("Could not reach the Olostep API. Try again later.")

    def check_key(self) -> None:
        """Checks the key with a lookup that uses no credits."""
        try:
            response = self._send("GET", "batches/batch_dify_key_check")
        except httpx.HTTPError:
            raise OlostepError("Could not reach the Olostep API. Try again later.") from None
        if response.status_code in (401, 403):
            raise OlostepError(error_message(response))

    def scrape(self, url: str) -> dict:
        url = check_url(url)
        data = self.request("POST", "scrapes", body={"url_to_scrape": url, "formats": ["markdown"]})
        result = data.get("result") or {}
        page = {"url": url, "markdown": result.get("markdown_content")}
        if result.get("markdown_hosted_url"):
            page["markdown_hosted_url"] = result["markdown_hosted_url"]
        return page

    def search(self, query: str, limit: int) -> dict:
        data = self.request("POST", "searches", body={"query": query, "limit": limit})
        return {"query": query, "results": (data.get("result") or {}).get("links") or []}

    def answer(self, task: str) -> dict:
        result = self.request("POST", "answers", body={"task": task}).get("result") or {}
        content = result.get("json_content")
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except ValueError:
                pass
        if isinstance(content, dict) and "result" in content:
            content = content["result"]
        return {"task": task, "answer": content, "sources": result.get("sources") or []}

    def map(self, url: str, top_n: int) -> dict:
        url = check_url(url)
        data = self.request("POST", "maps", body={"url": url, "top_n": top_n})
        return {"url": url, "urls": data.get("urls") or []}

    def crawl(self, url: str, max_pages: int, max_wait: int) -> dict:
        job = self.request("POST", "crawls", body={"start_url": check_url(url), "max_pages": max_pages})
        return self.finish("crawls", job["id"], max_wait)

    def batch_scrape(self, urls: list[str], max_wait: int) -> dict:
        items = [{"custom_id": str(i), "url": check_url(url)} for i, url in enumerate(urls)]
        job = self.request("POST", "batches", body={"items": items})
        return self.finish("batches", job["id"], max_wait)

    def results(self, job_id: str, max_wait: int) -> dict:
        job_id = job_id.strip()
        if job_id.startswith("crawl_"):
            return self.finish("crawls", job_id, max_wait)
        if job_id.startswith("batch_"):
            return self.finish("batches", job_id, max_wait)
        raise OlostepError(f"Enter a crawl or batch id, for example crawl_abc123 or batch_abc123 (got {job_id!r}).")

    def finish(self, kind: str, job_id: str, max_wait: int) -> dict:
        """Waits for a crawl or batch, then returns the markdown of each page."""
        info = self.request("GET", f"{kind}/{job_id}")
        waited = 0
        while info.get("status") == "in_progress" and waited < max_wait:
            self._sleep(POLL_SECONDS)
            waited += POLL_SECONDS
            info = self.request("GET", f"{kind}/{job_id}")
        if info.get("status") == "in_progress":
            return {
                "id": job_id,
                "status": "in_progress",
                "message": "Still running. Use the Get Results tool with this id in a few minutes.",
            }
        if kind == "batches":
            items = self._list(f"batches/{job_id}/items", "items", {"status": "completed"})
        else:
            items = self._list(f"crawls/{job_id}/pages", "pages", {})
        with ThreadPoolExecutor(max_workers=RETRIEVE_WORKERS) as pool:
            pages = list(pool.map(self._retrieve, items))
        return {"id": job_id, "status": info.get("status") or "completed", "pages": pages}

    def _list(self, path: str, key: str, params: dict) -> list[dict]:
        items: list[dict] = []
        cursor = None
        while True:
            page_params = {**params, "limit": PAGE_SIZE}
            if cursor is not None:
                page_params["cursor"] = cursor
            data = self.request("GET", path, params=page_params)
            page_items = data.get(key) or []
            items.extend(page_items)
            cursor = data.get("cursor")
            if not page_items or cursor is None:
                return items

    def _retrieve(self, item: dict) -> dict:
        page = {"url": item.get("url"), "markdown": None}
        try:
            data = self.request(
                "GET", "retrieve", params={"retrieve_id": item.get("retrieve_id"), "formats": "markdown"}
            )
        except OlostepError as error:
            page["error"] = str(error)
            return page
        page["markdown"] = data.get("markdown_content")
        if data.get("markdown_hosted_url"):
            page["markdown_hosted_url"] = data["markdown_hosted_url"]
        return page
