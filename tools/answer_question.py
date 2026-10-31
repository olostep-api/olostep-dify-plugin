from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from olostep_client.invoke import respond


class AnswerQuestionTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        task = str(tool_parameters.get("task") or "").strip()
        yield from respond(self, lambda client: client.answer(task))
