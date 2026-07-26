"""
Layer 4: Structured Metadata (PostgreSQL)
Persistent storage for research sessions, sources, claims, papers.
Falls back to in-memory storage when PostgreSQL is unavailable.
"""

import json
from datetime import datetime

import structlog

from config.settings import get_settings

logger = structlog.get_logger()


class InMemoryMetadataBackend:
    """Pure in-memory fallback when PostgreSQL is not available."""

    def __init__(self):
        self._sessions: dict[str, dict] = {}
        self._sources: dict[str, dict] = {}
        self._claims: dict[str, dict] = {}
        self._papers: dict[str, dict] = {}
        self._executions: list[dict] = []
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return str(self._counter)

    async def get_active_session_ids(self) -> list[str]:
        transient_statuses = {
            "pending",
            "planning",
            "searching",
            "browsing",
            "reading",
            "extracting",
            "critiquing",
            "analyzing_novelty",
            "writing",
            "citing",
            "formatting",
        }
        return [sid for sid, s in self._sessions.items() if s.get("status") in transient_statuses]

    async def create_session(self, session_id: str, prompt: str) -> dict:
        session = {
            "id": session_id,
            "prompt": prompt,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "error": None,
        }
        self._sessions[session_id] = session
        return session

    async def update_session_status(self, session_id: str, status: str, error: str | None = None):
        if session_id in self._sessions:
            self._sessions[session_id]["status"] = status
            if error:
                self._sessions[session_id]["error"] = error
            if status == "completed":
                self._sessions[session_id]["completed_at"] = datetime.utcnow().isoformat()

    async def get_session(self, session_id: str) -> dict | None:
        return self._sessions.get(session_id)

    async def store_source(
        self, session_id, url, title, source_type, content, content_hash, metadata=None
    ) -> str:
        sid = self._next_id()
        self._sources[sid] = {
            "id": sid,
            "session_id": session_id,
            "url": url,
            "title": title,
            "source_type": source_type,
            "content": content[:50000],
            "content_hash": content_hash,
        }
        return sid

    async def store_claim(self, session_id, claim_text, evidence, source_id, confidence) -> str:
        cid = self._next_id()
        self._claims[cid] = {
            "id": cid,
            "session_id": session_id,
            "claim_text": claim_text,
            "evidence": evidence,
            "source_id": source_id,
            "confidence": confidence,
        }
        return cid

    async def store_paper(
        self,
        session_id,
        title,
        abstract,
        sections,
        references,
        content_md,
        layout="2 Column",
        font="Times New Roman",
    ) -> str:
        pid = self._next_id()
        self._papers[pid] = {
            "id": pid,
            "session_id": session_id,
            "title": title,
            "abstract": abstract,
            "sections": sections,
            "references": references,
            "content_md": content_md,
            "layout": layout,
            "font": font,
        }
        return pid

    async def log_agent_execution(
        self,
        session_id,
        agent_name,
        status,
        input_data=None,
        output_data=None,
        tokens_used=0,
        duration_ms=0,
        error=None,
        model_name=None,
        tokens_in=0,
        tokens_out=0,
        cost=0.0,
        latency=0,
    ):
        self._executions.append(
            {
                "session_id": session_id,
                "agent_name": agent_name,
                "status": status,
                "tokens_used": tokens_used,
                "duration_ms": duration_ms,
                "error": error,
                "model_name": model_name,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost": cost,
                "latency": latency,
            }
        )

    async def list_sessions(self, limit=20):
        sessions = sorted(
            self._sessions.values(), key=lambda s: s.get("created_at", ""), reverse=True
        )
        return sessions[:limit]

    async def get_paper_by_session(self, session_id: str) -> dict | None:
        """Find a paper by session_id."""
        for pid, paper in self._papers.items():
            if paper.get("session_id") == session_id:
                paper_dict = dict(paper)
                if "content_md" in paper_dict and "content_markdown" not in paper_dict:
                    paper_dict["content_markdown"] = paper_dict["content_md"]
                return paper_dict
        return None

    async def disconnect(self):
        pass


class MetadataStore:
    """PostgreSQL-backed structured metadata storage.
    Falls back to in-memory when PostgreSQL is unavailable."""

    def __init__(self):
        self._backend = None
        self._using_fallback = False

    async def _ensure_backend(self):
        if self._backend is not None:
            return

        settings = get_settings()
        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

            engine = create_async_engine(
                settings.postgres_dsn,
                pool_size=10,
                max_overflow=20,
                echo=False,
                pool_pre_ping=True,
            )
            # Test connection
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

            self._engine = engine
            self._session_factory = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )

            # Dynamically ensure metrics columns exist in agent_executions (Issue 3 / 9)
            try:
                async with self._session_factory() as db:
                    await db.execute(
                        text(
                            "ALTER TABLE agent_executions ADD COLUMN IF NOT EXISTS model_name VARCHAR(100)"
                        )
                    )
                    await db.execute(
                        text(
                            "ALTER TABLE agent_executions ADD COLUMN IF NOT EXISTS tokens_in INTEGER DEFAULT 0"
                        )
                    )
                    await db.execute(
                        text(
                            "ALTER TABLE agent_executions ADD COLUMN IF NOT EXISTS tokens_out INTEGER DEFAULT 0"
                        )
                    )
                    await db.execute(
                        text(
                            "ALTER TABLE agent_executions ADD COLUMN IF NOT EXISTS cost NUMERIC(10, 6) DEFAULT 0.000000"
                        )
                    )
                    await db.execute(
                        text(
                            "ALTER TABLE agent_executions ADD COLUMN IF NOT EXISTS latency INTEGER DEFAULT 0"
                        )
                    )
                    await db.commit()
            except Exception as ex:
                logger.warning("failed_altering_agent_executions_columns", error=str(ex))

            self._backend = "postgres"
            logger.info("postgres_connected")
        except Exception as e:
            logger.warning("postgres_unavailable_using_memory", error=str(e))
            self._backend = "memory"
            self._using_fallback = True
            self._memory = InMemoryMetadataBackend()

    async def disconnect(self):
        if self._backend == "postgres":
            await self._engine.dispose()
        elif self._backend == "memory":
            await self._memory.disconnect()

    async def get_active_session_ids(self) -> list[str]:
        await self._ensure_backend()
        if self._using_fallback:
            return await self._memory.get_active_session_ids()

        from sqlalchemy import text

        async with self._session_factory() as db:
            result = await db.execute(
                text("""
                    SELECT id FROM research_sessions
                    WHERE status NOT IN ('completed', 'failed')
                """)
            )
            rows = result.mappings().all()
            return [str(row["id"]) for row in rows]

    async def create_session(self, session_id: str, prompt: str) -> dict:
        await self._ensure_backend()
        if self._using_fallback:
            return await self._memory.create_session(session_id, prompt)

        from sqlalchemy import text

        async with self._session_factory() as db:
            result = await db.execute(
                text("""
                    INSERT INTO research_sessions (id, prompt, status)
                    VALUES (:id, :prompt, 'pending')
                    RETURNING id, prompt, status, created_at
                """),
                {"id": session_id, "prompt": prompt},
            )
            await db.commit()
            row = result.mappings().one()
            return dict(row)

    async def update_session_status(self, session_id: str, status: str, error: str | None = None):
        await self._ensure_backend()
        if self._using_fallback:
            return await self._memory.update_session_status(session_id, status, error)

        from sqlalchemy import text

        async with self._session_factory() as db:
            if error:
                await db.execute(
                    text("""
                        UPDATE research_sessions
                        SET status = :status, error = :error
                        WHERE id = :id
                    """),
                    {"id": session_id, "status": status, "error": error},
                )
            else:
                await db.execute(
                    text("""
                        UPDATE research_sessions SET status = :status WHERE id = :id
                    """),
                    {"id": session_id, "status": status},
                )
            await db.commit()

    async def get_session(self, session_id: str) -> dict | None:
        await self._ensure_backend()
        if self._using_fallback:
            return await self._memory.get_session(session_id)

        from sqlalchemy import text

        async with self._session_factory() as db:
            result = await db.execute(
                text("SELECT * FROM research_sessions WHERE id = :id"),
                {"id": session_id},
            )
            row = result.mappings().first()
            return dict(row) if row else None

    async def store_source(
        self,
        session_id: str,
        url: str,
        title: str,
        source_type: str,
        content: str,
        content_hash: str,
        metadata: dict | None = None,
    ) -> str:
        await self._ensure_backend()
        if self._using_fallback:
            return await self._memory.store_source(
                session_id, url, title, source_type, content, content_hash, metadata
            )

        from sqlalchemy import text

        async with self._session_factory() as db:
            result = await db.execute(
                text("""
                    INSERT INTO sources (session_id, url, title, source_type, content, content_hash, metadata)
                    VALUES (:session_id, :url, :title, :source_type, :content, :content_hash, CAST(:metadata AS jsonb))
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """),
                {
                    "session_id": session_id,
                    "url": url,
                    "title": title,
                    "source_type": source_type,
                    "content": content[:50000],
                    "content_hash": content_hash,
                    "metadata": "{}",
                },
            )
            await db.commit()
            row = result.mappings().first()
            return str(row["id"]) if row else ""

    async def store_claim(
        self,
        session_id: str,
        claim_text: str,
        evidence: str,
        source_id: str | None,
        confidence: float,
    ) -> str:
        await self._ensure_backend()
        if self._using_fallback:
            return await self._memory.store_claim(
                session_id, claim_text, evidence, source_id, confidence
            )

        from sqlalchemy import text

        async with self._session_factory() as db:
            result = await db.execute(
                text("""
                    INSERT INTO claims (session_id, source_id, claim_text, evidence, confidence)
                    VALUES (:session_id, :source_id, :claim_text, :evidence, :confidence)
                    RETURNING id
                """),
                {
                    "session_id": session_id,
                    "source_id": source_id,
                    "claim_text": claim_text,
                    "evidence": evidence,
                    "confidence": confidence,
                },
            )
            await db.commit()
            row = result.mappings().one()
            return str(row["id"])

    async def store_paper(
        self,
        session_id: str,
        title: str,
        abstract: str,
        sections: list,
        references: list,
        content_md: str,
        layout: str = "2 Column",
        font: str = "Times New Roman",
    ) -> str:
        await self._ensure_backend()
        if self._using_fallback:
            return await self._memory.store_paper(
                session_id, title, abstract, sections, references, content_md, layout, font
            )

        from sqlalchemy import text

        async with self._session_factory() as db:
            # Check if layout and font columns exist, otherwise add them dynamically
            try:
                await db.execute(
                    text("ALTER TABLE papers ADD COLUMN IF NOT EXISTS layout VARCHAR(50)")
                )
                await db.execute(
                    text("ALTER TABLE papers ADD COLUMN IF NOT EXISTS font VARCHAR(50)")
                )
                await db.commit()
            except Exception:
                pass

            result = await db.execute(
                text("""
                    INSERT INTO papers (session_id, title, abstract, sections, "references", content_md, layout, font)
                    VALUES (:session_id, :title, :abstract, CAST(:sections AS jsonb), CAST(:references AS jsonb), :content_md, :layout, :font)
                    RETURNING id
                """),
                {
                    "session_id": session_id,
                    "title": title,
                    "abstract": abstract,
                    "sections": json.dumps(sections),
                    "references": json.dumps(references),
                    "content_md": content_md,
                    "layout": layout,
                    "font": font,
                },
            )
            await db.commit()
            row = result.mappings().one()
            return str(row["id"])

    async def log_agent_execution(
        self,
        session_id: str,
        agent_name: str,
        status: str,
        input_data: dict | None = None,
        output_data: dict | None = None,
        tokens_used: int = 0,
        duration_ms: int = 0,
        error: str | None = None,
        model_name: str | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost: float = 0.0,
        latency: int = 0,
    ):
        await self._ensure_backend()
        if self._using_fallback:
            return await self._memory.log_agent_execution(
                session_id,
                agent_name,
                status,
                input_data,
                output_data,
                tokens_used,
                duration_ms,
                error,
                model_name,
                tokens_in,
                tokens_out,
                cost,
                latency,
            )

        from sqlalchemy import text

        async with self._session_factory() as db:
            await db.execute(
                text("""
                    INSERT INTO agent_executions
                    (session_id, agent_name, status, input_data, output_data, tokens_used, duration_ms, error,
                     model_name, tokens_in, tokens_out, cost, latency)
                    VALUES (:session_id, :agent_name, :status, CAST(:input AS jsonb), CAST(:output AS jsonb),
                            :tokens, :duration, :error, :model_name, :tokens_in, :tokens_out, :cost, :latency)
                """),
                {
                    "session_id": session_id,
                    "agent_name": agent_name,
                    "status": status,
                    "input": json.dumps(input_data) if input_data else "{}",
                    "output": json.dumps(output_data) if output_data else "{}",
                    "tokens": tokens_used,
                    "duration": duration_ms,
                    "error": error,
                    "model_name": model_name,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost": cost,
                    "latency": latency,
                },
            )
            await db.commit()

    async def clear(self):
        """Clear all metadata database records or in-memory backend."""
        await self._ensure_backend()
        if self._using_fallback:
            self._memory._sessions.clear()
            self._memory._sources.clear()
            self._memory._claims.clear()
            self._memory._papers.clear()
            self._memory._executions.clear()
            self._memory._counter = 0
        else:
            from sqlalchemy import text

            async with self._session_factory() as db:
                try:
                    await db.execute(text("TRUNCATE TABLE agent_executions CASCADE"))
                    await db.execute(text("TRUNCATE TABLE papers CASCADE"))
                    await db.execute(text("TRUNCATE TABLE claims CASCADE"))
                    await db.execute(text("TRUNCATE TABLE sources CASCADE"))
                    await db.execute(text("TRUNCATE TABLE research_sessions CASCADE"))
                    await db.commit()
                    logger.info("postgres_metadata_cleared")
                except Exception as e:
                    logger.error("failed_clearing_postgres_metadata", error=str(e))

    async def get_paper_by_session(self, session_id: str) -> dict | None:
        """Get paper by session_id from either backend."""
        await self._ensure_backend()
        if self._using_fallback:
            return await self._memory.get_paper_by_session(session_id)

        from sqlalchemy import text

        try:
            async with self._session_factory() as db:
                result = await db.execute(
                    text("SELECT * FROM papers WHERE session_id = :sid ORDER BY id DESC LIMIT 1"),
                    {"sid": session_id},
                )
                row = result.mappings().first()
                if row:
                    paper_dict = dict(row)
                    if "content_md" in paper_dict and "content_markdown" not in paper_dict:
                        paper_dict["content_markdown"] = paper_dict["content_md"]
                    return paper_dict
        except Exception as e:
            logger.error("get_paper_by_session_failed", session_id=session_id, error=str(e))
        return None


_metadata_store: MetadataStore | None = None


def get_metadata_store() -> MetadataStore:
    global _metadata_store
    if _metadata_store is None:
        _metadata_store = MetadataStore()
    return _metadata_store
