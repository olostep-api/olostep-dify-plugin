from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from olostep_client.client import OlostepClient, OlostepError


class OlostepProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            OlostepClient(credentials.get("api_key")).check_key()
        except OlostepError as error:
            raise ToolProviderCredentialValidationError(str(error)) from None
