from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from olostep_client.invoke import respond, to_int


class CrawlWebsiteTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        max_pages = to_int(tool_parameters.get("max_pages"), 10, 1, 100_000)
        max_wait = to_int(tool_parameters.get("max_wait_seconds"), 120, 0, 240)
        yield from respond(self, lambda client: client.crawl(tool_parameters.get("url"), max_pages, max_wait))
