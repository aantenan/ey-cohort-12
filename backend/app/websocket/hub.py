"""Redis pub/sub fan-out to WebSocket connections on each replica."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from redis.asyncio import Redis
from starlette.websockets import WebSocket

logger = logging.getLogger(__name__)


def channel_for_agent(agent_id: str) -> str:
    return f"ws:agent:{agent_id}"


class WebSocketHub:
    """Registers local WebSockets and forwards Redis pub/sub messages to matching clients."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._by_agent: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._listener: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        self._listener = asyncio.create_task(self._run_pubsub(), name="redis-ws-pubsub")

    async def stop(self) -> None:
        self._stopped.set()
        if self._listener:
            self._listener.cancel()
            try:
                await self._listener
            except asyncio.CancelledError:
                pass

    async def register(self, agent_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._by_agent[agent_id].add(ws)

    async def unregister(self, agent_id: str, ws: WebSocket) -> None:
        async with self._lock:
            if agent_id in self._by_agent:
                self._by_agent[agent_id].discard(ws)
                if not self._by_agent[agent_id]:
                    del self._by_agent[agent_id]

    async def publish(self, agent_id: str, payload: dict[str, object]) -> None:
        """Publish an event to all replicas listening on this agent channel."""
        body = json.dumps(payload, default=str).encode("utf-8")
        await self._redis.publish(channel_for_agent(agent_id), body)

    async def _run_pubsub(self) -> None:
        pubsub = self._redis.pubsub()
        try:
            await pubsub.psubscribe("ws:agent:*")
            async for message in pubsub.listen():
                if self._stopped.is_set():
                    break
                if message["type"] != "pmessage":
                    continue
                channel_raw = message["channel"]
                channel = (
                    channel_raw.decode("utf-8") if isinstance(channel_raw, bytes) else str(channel_raw)
                )
                prefix = "ws:agent:"
                if not channel.startswith(prefix):
                    continue
                agent_id = channel[len(prefix) :]
                data_raw = message["data"]
                text = data_raw.decode("utf-8") if isinstance(data_raw, bytes) else str(data_raw)
                async with self._lock:
                    sockets = list(self._by_agent.get(agent_id, ()))
                for ws in sockets:
                    try:
                        await ws.send_text(text)
                    except Exception:
                        logger.exception("websocket_send_failed", agent_id=agent_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("redis_pubsub_listener_failed")
        finally:
            await pubsub.punsubscribe("ws:agent:*")
            await pubsub.close()
