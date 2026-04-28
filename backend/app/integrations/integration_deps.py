"""API-key authentication for external integrations (IVR, chatbot)."""

from typing import Annotated

from fastapi import Header, HTTPException, Request


def require_integration_api_key(integration: str):
    """
    Factory: validates `X-API-Key` against the secret loaded for `integration`
    (`ivr` or `chatbot`). Keys come from Key Vault or INTEGRATION_API_KEYS_JSON.
    """

    async def _verify(
        request: Request,
        x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    ) -> None:
        keys: dict[str, str] = getattr(request.app.state, "integration_keys", {})
        expected = keys.get(integration)
        if not expected or not x_api_key or x_api_key != expected:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

    return _verify


require_ivr_api_key = require_integration_api_key("ivr")
require_chatbot_api_key = require_integration_api_key("chatbot")
