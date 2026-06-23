"""
Layer 1: Session Memory (Redis)
Fast ephemeral storage for active research sessions.
Falls back to in-memory dict when Redis is unavailable.
"""

import json

import structlog

from config.settings import get_settings

logger = structlog.get_logger()


class InMemorySessionBackend:
    """Pure in-memory fallback when Redis is not available."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._lists: dict[str, list[str]] = {}
        self._hashes: dict[str, dict[str, str]] = {}

    async def set(self, key: str, value: str, ex: int = 0):
        self._store[key] = value

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def rpush(self, key: str, value: str):
        if key not in self._lists:
            self._lists[key] = []
        self._lists[key].append(value)

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        lst = self._lists.get(key, [])
        if end == -1:
            return lst[start:]
        return lst[start : end + 1]

    async def expire(self, key: str, ttl: int):
        pass  # No-op for in-memory

    async def hset(self, key: str, field: str, value: str):
        if key not in self._hashes:
            self._hashes[key] = {}
        self._hashes[key][field] = value

    async def hget(self, key: str, field: str) -> str | None:
        return self._hashes.get(key, {}).get(field)

    async def ping(self):
        return True

    def clear(self):
        self._store.clear()
        self._lists.clear()
        self._hashes.clear()

    async def aclose(self):
        pass


class SessionMemory:
    """Redis-backed session memory for active research state.
    Falls back to in-memory when Redis is unavailable."""

    def __init__(self):
        settings = get_settings()
        self._redis = None
        self._url = settings.redis_url
        self._prefix = "ros:session:"
        self._ttl = 86400  # 24 hours
        self._using_fallback = False

    async def connect(self):
        if self._redis is None:
            try:
                import redis.asyncio as redis
                client = redis.from_url(self._url, decode_responses=True)
                await client.ping()
                self._redis = client
                logger.info("redis_connected")
            except Exception as e:
                logger.warning("redis_unavailable_using_memory", error=str(e))
                self._redis = InMemorySessionBackend()
                self._using_fallback = True

    async def disconnect(self):
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    def _key(self, session_id: str, field: str = "") -> str:
        base = f"{self._prefix}{session_id}"
        return f"{base}:{field}" if field else base

    async def set_state(self, session_id: str, state: dict):
        """Store/merge session state."""
        await self.connect()
        key = self._key(session_id, "state")
        try:
            existing = await self._redis.get(key)
            existing_dict = json.loads(existing) if existing else {}
        except Exception:
            existing_dict = {}
        existing_dict.update(state)
        await self._redis.set(
            key,
            json.dumps(existing_dict),
            ex=self._ttl,
        )

    async def get_state(self, session_id: str) -> dict | None:
        """Retrieve session state."""
        await self.connect()
        data = await self._redis.get(self._key(session_id, "state"))
        return json.loads(data) if data else None

    async def push_event(self, session_id: str, event: dict):
        """Push an agent event to the session stream."""
        await self.connect()
        await self._redis.rpush(
            self._key(session_id, "events"),
            json.dumps(event),
        )
        await self._redis.expire(self._key(session_id, "events"), self._ttl)

    async def get_events(self, session_id: str, start: int = 0) -> list[dict]:
        """Get all events from a session."""
        await self.connect()
        events = await self._redis.lrange(
            self._key(session_id, "events"), start, -1
        )
        return [json.loads(e) for e in events]

    async def set_agent_output(self, session_id: str, agent: str, output: dict):
        """Cache agent output for the session."""
        await self.connect()
        await self._redis.hset(
            self._key(session_id, "agents"),
            agent,
            json.dumps(output),
        )
        await self._redis.expire(self._key(session_id, "agents"), self._ttl)

    async def get_agent_output(self, session_id: str, agent: str) -> dict | None:
        """Get cached agent output."""
        await self.connect()
        data = await self._redis.hget(self._key(session_id, "agents"), agent)
        return json.loads(data) if data else None

    async def clear(self):
        """Clear all session data in Redis or in-memory backend."""
        await self.connect()
        if self._using_fallback:
            self._redis.clear()
        else:
            try:
                await self._redis.flushdb()
                logger.info("redis_flushed")
            except Exception as e:
                logger.error("failed_flushing_redis", error=str(e))


_session_memory: SessionMemory | None = None


def get_session_memory() -> SessionMemory:
    global _session_memory
    if _session_memory is None:
        _session_memory = SessionMemory()
    return _session_memory
