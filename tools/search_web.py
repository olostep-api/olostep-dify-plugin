from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from olostep_client.invoke import respond, to_int


class SearchWebTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        query = str(tool_parameters.get("query") or "").strip()
        limit = to_int(tool_parameters.get("limit"), 10, 1, 50)
        yield from respond(self, lambda client: client.search(query, limit))
