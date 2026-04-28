"""Load integration API keys from Azure Key Vault (managed identity) or local env."""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.core.config import Settings

logger = structlog.get_logger(__name__)


def load_integration_api_keys(settings: Settings) -> dict[str, str]:
    """
    Returns mapping integration_name -> secret value (e.g. ivr, chatbot).
    Cloud: Key Vault secret names from settings. Local: INTEGRATION_API_KEYS_JSON.
    """
    if settings.key_vault_url:
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
        except ImportError as e:
            raise RuntimeError("azure-identity and azure-keyvault-secrets are required") from e

        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=settings.key_vault_url, credential=credential)
        out: dict[str, str] = {}
        ivr = client.get_secret(settings.key_vault_ivr_secret_name).value
        bot = client.get_secret(settings.key_vault_chatbot_secret_name).value
        if ivr:
            out["ivr"] = ivr
        if bot:
            out["chatbot"] = bot
        logger.info("integration_keys_loaded", source="key_vault", keys=list(out))
        return out

    raw = settings.integration_api_keys_json.strip()
    if not raw:
        logger.warning("integration_keys_empty_no_key_vault")
        return {}

    data: Any = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("INTEGRATION_API_KEYS_JSON must be a JSON object")
    return {str(k): str(v) for k, v in data.items()}
