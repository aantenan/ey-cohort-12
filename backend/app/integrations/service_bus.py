"""Azure Service Bus publisher — queues and topics."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings

logger = logging.getLogger(__name__)


class ServiceBusPublisher:
    """Publishes messages when a connection string is configured; otherwise no-ops."""

    def __init__(self, settings: Settings) -> None:
        self._conn = settings.azure_service_bus_connection_string.strip()
        self._client: Any = None
        if self._conn:
            try:
                from azure.servicebus.aio import ServiceBusClient

                self._client = ServiceBusClient.from_connection_string(self._conn)
            except ImportError as e:
                raise RuntimeError("azure-servicebus is required for Service Bus") from e

    async def send_queue_message(self, queue_name: str, body: bytes | str, *, content_type: str | None = None) -> None:
        if not self._client:
            logger.debug("service_bus_skipped", queue=queue_name, reason="no_connection_string")
            return
        from azure.servicebus.aio import ServiceBusMessage

        payload = body if isinstance(body, bytes) else body.encode("utf-8")
        msg = ServiceBusMessage(body=payload)
        if content_type:
            msg.content_type = content_type
        sender = self._client.get_queue_sender(queue_name)
        async with sender:
            await sender.send_messages(msg)

    async def send_topic_message(self, topic_name: str, body: bytes | str, *, content_type: str | None = None) -> None:
        if not self._client:
            logger.debug("service_bus_skipped", topic=topic_name, reason="no_connection_string")
            return
        from azure.servicebus.aio import ServiceBusMessage

        payload = body if isinstance(body, bytes) else body.encode("utf-8")
        msg = ServiceBusMessage(body=payload)
        if content_type:
            msg.content_type = content_type
        sender = self._client.get_topic_sender(topic_name)
        async with sender:
            await sender.send_messages(msg)

    async def close(self) -> None:
        if self._client:
            await self._client.close()
