import re
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from olostep_client.invoke import respond, to_int

MAX_URLS = 100


class BatchScrapeTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        urls = [url for url in re.split(r"[\s,]+", str(tool_parameters.get("urls") or "")) if url]
        if not urls:
            raise ValueError("Enter at least one URL.")
        if len(urls) > MAX_URLS:
            raise ValueError(f"Enter at most {MAX_URLS} URLs (got {len(urls)}).")
        max_wait = to_int(tool_parameters.get("max_wait_seconds"), 120, 0, 240)
        yield from respond(self, lambda client: client.batch_scrape(urls, max_wait))
