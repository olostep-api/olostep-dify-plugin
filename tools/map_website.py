from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from olostep_client.invoke import respond, to_int


class MapWebsiteTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        top_n = to_int(tool_parameters.get("top_n"), 100, 1, 1000)
        yield from respond(self, lambda client: client.map(tool_parameters.get("url"), top_n))
