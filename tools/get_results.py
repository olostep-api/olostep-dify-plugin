from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from olostep_client.invoke import respond


class GetResultsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        job_id = str(tool_parameters.get("id") or "")
        yield from respond(self, lambda client: client.results(job_id, 0))
