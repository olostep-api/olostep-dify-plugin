import json
from collections.abc import Callable, Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from olostep_client.client import OlostepClient, OlostepError


def to_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


def as_text(result: dict) -> str:
    """Readable text for agents, next to the JSON output for workflows."""
    if "pages" in result:
        sections = [f"## {page['url']}\n\n{page.get('markdown') or page.get('error') or ''}" for page in result["pages"]]
        return "\n\n".join(sections) or "No pages were returned."
    if result.get("markdown"):
        return result["markdown"]
    return json.dumps(result, ensure_ascii=False, indent=2)


def respond(tool: Tool, call: Callable[[OlostepClient], dict]) -> Generator[ToolInvokeMessage, None, None]:
    try:
        result = call(OlostepClient(tool.runtime.credentials.get("api_key")))
    except OlostepError as error:
        raise ValueError(str(error)) from None
    yield tool.create_json_message(result)
    yield tool.create_text_message(as_text(result))
