"""
Research API Routes
POST /api/research — Start a new research session
GET /api/research/{session_id} — Get research session status
GET /api/research/{session_id}/paper — Get generated paper
GET /api/research — List recent sessions
"""

import asyncio
import uuid

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Response
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from graph.workflow import get_research_workflow
from memory.metadata import get_metadata_store
from memory.session import get_session_memory
from schemas.research import ResearchRequest, ResearchResponse, ResearchStatus

logger = structlog.get_logger()
router = APIRouter(prefix="/api/research", tags=["research"])

# Active research tasks
_active_tasks: dict[str, asyncio.Task] = {}


async def _run_research_pipeline(session_id: str, request: ResearchRequest):
    """Execute the full research pipeline in the background.
    Includes timing telemetry and hard 10-minute deadline."""
    import time

    session_mem = get_session_memory()
    metadata = get_metadata_store()
    pipeline_start = time.monotonic()
    MAX_DURATION_SECONDS = 600  # 10 minutes

    from config.settings import active_session_id_var, active_topic_var
    from services.mock_llm import extract_topic

    topic = extract_topic(request.prompt)
    active_topic_var.set(topic)
    active_session_id_var.set(session_id)

    # Node-to-metric mapping for timing telemetry
    PHASE_MAP = {
        "planner": "planner_ms",
        "search": "search_ms",
        "firecrawl_extract": "firecrawl_ms",
        "reader": "reader_ms",
        "claim_extractor": "claim_extractor_ms",
        "critic": "critic_ms",
        "citation_novelty": "citation_ms",
        "writer": "writer_ms",
        "critic_paper": "critic_paper_ms",
        "writer_revision": "writer_revision_ms",
        "ieee_formatter": "ieee_formatter_ms",
        "humanizer": "humanizer_ms",
        "page_validator": "pdf_ms",
    }
    phase_timings: dict[str, int] = {}

    try:
        # Update status
        await metadata.update_session_status(session_id, "planning")
        await session_mem.set_state(session_id, {"status": "planning", "topic": topic})

        # Get compiled workflow
        workflow = get_research_workflow()

        # Initial state
        initial_state = {
            "session_id": session_id,
            "prompt": request.prompt,
            "topic": topic,
            "sources": [],
            "validation": {},
            "depth": request.depth,
            "max_sources": request.max_sources,
            "pages": request.pages,
            "layout": request.layout,
            "font": request.font,
            "visual_mode": request.visual_mode,
            "page_budget": {},
            "target_word_count": 0,
            "expansion_round": 0,
            "status": "planning",
            "current_agent": "planner",
            "events": [],
            "firecrawl_requests": 0,
            "firecrawl_success": 0,
            "firecrawl_failed": 0,
            "firecrawl_latency_ms": 0,
            "pipeline_start_time": pipeline_start,
            "timing": {},
        }

        # Run the workflow
        final_state = None
        paper_finalized = False
        async for state in workflow.astream(initial_state):
            now = time.monotonic()
            elapsed = now - pipeline_start

            # ── Hard stop: if over 10 minutes, finalize current state ──
            if elapsed > MAX_DURATION_SECONDS:
                logger.warning(
                    "HARD_DEADLINE_REACHED",
                    session_id=session_id,
                    elapsed_seconds=round(elapsed, 1),
                )
                # Take whatever state we have and finalize
                final_node_output = None
                for node_name, node_output in state.items():
                    final_node_output = node_output
                if final_node_output and not paper_finalized:
                    # Try to finalize with whatever paper we have
                    await _finalize_paper(
                        session_id,
                        final_node_output,
                        request,
                        final_state,
                        phase_timings,
                        pipeline_start,
                    )
                    paper_finalized = True
                break

            # state is a dict with node name -> output
            for node_name, node_output in state.items():
                status = node_output.get("status", "")
                current_agent = node_output.get("current_agent", "")

                # ── Timing: record phase completion ──
                if node_name in PHASE_MAP:
                    metric = PHASE_MAP[node_name]
                    phase_timings[metric] = int((now - pipeline_start) * 1000)

                # Push events to session memory
                for event in node_output.get("events", []):
                    event["session_id"] = session_id
                    await session_mem.push_event(session_id, event)

                # If this node completed the pipeline, finalize paper BEFORE marking status completed
                if status == "completed" and node_output.get("final_paper") and not paper_finalized:
                    await _finalize_paper(
                        session_id, node_output, request, node_output, phase_timings, pipeline_start
                    )
                    paper_finalized = True
                else:
                    # Update status for intermediate nodes
                    if status:
                        await session_mem.set_state(
                            session_id,
                            {
                                "status": status,
                                "current_agent": current_agent,
                            },
                        )
                        await metadata.update_session_status(session_id, status)

                final_state = node_output

        # Store final paper if not already finalized (e.g., hard deadline or partial completion)
        if final_state and final_state.get("status") == "completed" and not paper_finalized:
            await _finalize_paper(
                session_id, final_state, request, final_state, phase_timings, pipeline_start
            )
        elif not paper_finalized:
            # Report timing even on partial completion
            timing_report = _build_timing_report(phase_timings, pipeline_start)
            logger.info("research_timing_report", session_id=session_id, timing=timing_report)

    except Exception as e:
        logger.error("research_failed", session_id=session_id, error=str(e))
        await metadata.update_session_status(session_id, "failed", error=str(e))
        await session_mem.set_state(session_id, {"status": "failed", "error": str(e)})
        # Report timing on failure too
        timing_report = _build_timing_report(phase_timings, pipeline_start)
        logger.info(
            "research_timing_report_on_failure", session_id=session_id, timing=timing_report
        )

    finally:
        _active_tasks.pop(session_id, None)


async def _finalize_paper(
    session_id: str,
    final_state: dict,
    request: ResearchRequest,
    final_state_override: dict | None = None,
    phase_timings: dict | None = None,
    pipeline_start: float | None = None,
):
    """Store the final paper and timing report."""
    session_mem = get_session_memory()
    metadata = get_metadata_store()

    paper = final_state.get("final_paper", {})
    validation = final_state.get("validation", {})
    if not paper:
        logger.warning("finalize_no_paper_data", session_id=session_id)
        return

    await metadata.store_paper(
        session_id=session_id,
        title=paper.get("title", ""),
        abstract=paper.get("abstract", ""),
        sections=paper.get("sections", []),
        references=paper.get("references", []),
        content_md=paper.get("content_markdown", ""),
        layout=request.layout,
        font=request.font,
    )
    # Also cache paper in session memory for the /paper endpoint
    paper["layout"] = request.layout
    paper["font"] = request.font
    paper["visual_mode"] = request.visual_mode
    await session_mem.set_agent_output(session_id, "ieee_formatter", paper)

    # ── Timing Report ──
    timing_report = _build_timing_report(phase_timings, pipeline_start)
    paper["timing_report"] = timing_report

    logger.info(
        "paper_save_log",
        session_id=session_id,
        final_paper_length=len(paper.get("content_markdown", "")),
        output_path=f"/api/research/{session_id}/paper",
        save_status="success",
        timing=timing_report,
    )

    await metadata.update_session_status(session_id, "completed")
    await session_mem.set_state(
        session_id,
        {
            "status": "completed",
            "validation": validation,
            "timing_report": timing_report,
        },
    )
    logger.info("research_completed_with_timing", session_id=session_id, timing=timing_report)


def _build_timing_report(
    phase_timings: dict[str, int] | None,
    pipeline_start: float | None,
) -> dict:
    """Build the timing telemetry report."""
    import time

    total_ms = (
        int((time.monotonic() - (pipeline_start or time.monotonic())) * 1000)
        if pipeline_start
        else 0
    )

    return {
        "total_ms": total_ms,
        "total_seconds": round(total_ms / 1000, 1),
        "planner_ms": (phase_timings or {}).get("planner_ms", 0),
        "search_ms": (phase_timings or {}).get("search_ms", 0),
        "reader_ms": (phase_timings or {}).get("reader_ms", 0),
        "writer_ms": (phase_timings or {}).get("writer_ms", 0),
        "citation_ms": (phase_timings or {}).get("citation_ms", 0),
        "humanizer_ms": (phase_timings or {}).get("humanizer_ms", 0),
        "pdf_ms": (phase_timings or {}).get("pdf_ms", 0),
    }


async def clean_session():
    """Clear all settings, cache, memory stores, and database states."""
    # 1. Flush Redis (session cache)
    try:
        from memory.session import get_session_memory

        await get_session_memory().clear()
    except Exception as e:
        logger.warning("failed_cleaning_session_mem", error=str(e))

    # 2. Clear Qdrant collections (retrieval cache)
    try:
        from memory.retrieval_mem import get_retrieval_memory

        await get_retrieval_memory().clear()
    except Exception as e:
        logger.warning("failed_cleaning_retrieval_mem", error=str(e))

    # 3. Reset Neo4j memory graph (knowledge store)
    try:
        from memory.knowledge_graph import get_knowledge_graph

        await get_knowledge_graph().clear()
    except Exception as e:
        logger.warning("failed_cleaning_knowledge_graph", error=str(e))

    # 4. Clear local metadata memory store
    try:
        from memory.metadata import get_metadata_store

        await get_metadata_store().clear()
    except Exception as e:
        logger.warning("failed_cleaning_metadata_store", error=str(e))


@router.post("", response_model=ResearchResponse)
async def start_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
):
    """Start a new research session."""
    session_id = str(uuid.uuid4())
    metadata = get_metadata_store()

    # Create session in DB
    try:
        await metadata.create_session(session_id, request.prompt)
    except Exception as e:
        logger.warning("db_unavailable", error=str(e))
        # Continue without DB — session memory only

    # Start pipeline in background
    task = asyncio.create_task(_run_research_pipeline(session_id, request))
    _active_tasks[session_id] = task

    return ResearchResponse(
        session_id=uuid.UUID(session_id),
        status=ResearchStatus.PENDING,
        message="Research pipeline initiated. Connect to WebSocket for live updates.",
    )


@router.get("/{session_id}")
async def get_research_status(session_id: str):
    """Get the current status of a research session."""
    session_mem = get_session_memory()
    metadata = get_metadata_store()

    # Try session memory first (faster)
    state = await session_mem.get_state(session_id)
    if state:
        events = await session_mem.get_events(session_id)
        return {
            "session_id": session_id,
            **state,
            "events": events[-20:],  # Last 20 events
        }

    # Fallback to DB
    try:
        session = await metadata.get_session(session_id)
        if session:
            return session
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/{session_id}/paper")
async def get_paper(session_id: str):
    """Get the generated paper for a completed session."""
    session_mem = get_session_memory()
    metadata = get_metadata_store()

    # Prefer active session state, but do not require Redis/session memory for
    # persisted papers. Session cache can expire or be cleared independently.
    state = await session_mem.get_state(session_id)
    if state and state.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Session status: {state.get('status', 'unknown')}. Paper not ready.",
        )

    # Get paper from agent output cache (session memory)
    paper_data = await session_mem.get_agent_output(session_id, "ieee_formatter")
    if paper_data:
        return paper_data

    # Fallback: retrieve from metadata store
    try:
        if metadata._using_fallback:
            for pid, paper in metadata._memory._papers.items():
                if paper.get("session_id") == session_id:
                    paper_dict = dict(paper)
                    if "content_md" in paper_dict and "content_markdown" not in paper_dict:
                        paper_dict["content_markdown"] = paper_dict["content_md"]
                    return paper_dict
        else:
            from sqlalchemy import text

            async with metadata._session_factory() as db:
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
    except Exception:
        pass

    try:
        session = await metadata.get_session(session_id)
        if session and session.get("status") != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Session status: {session.get('status', 'unknown')}. Paper not ready.",
            )
    except HTTPException:
        raise
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="Paper not found")


async def _get_paper_data(session_id: str):
    """Shared helper to retrieve paper data from session memory or DB."""
    session_mem = get_session_memory()
    metadata = get_metadata_store()

    # Check session exists
    state = await session_mem.get_state(session_id)
    if not state:
        try:
            session = await metadata.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=404, detail="Session not found")

    # Get paper data from agent output cache
    paper_data = await session_mem.get_agent_output(session_id, "ieee_formatter")
    if not paper_data:
        # Fallback to metadata store (handles both in-memory and postgres)
        paper_data = await _fetch_paper_from_metadata(metadata, session_id)

    if not paper_data:
        raise HTTPException(status_code=404, detail="Paper not found or not ready yet")

    paper_data = dict(paper_data)
    if "content_md" in paper_data and "content_markdown" not in paper_data:
        paper_data["content_markdown"] = paper_data["content_md"]

    return paper_data


async def _fetch_paper_from_metadata(metadata, session_id: str) -> dict | None:
    """Fetch paper from metadata store, handling both backends."""
    try:
        paper = await metadata.get_paper_by_session(session_id)
        if paper:
            return paper
    except Exception:
        pass

    # Direct fallback for in-memory backend
    try:
        if hasattr(metadata, "_using_fallback") and metadata._using_fallback:
            for pid, paper in metadata._memory._papers.items():
                if paper.get("session_id") == session_id:
                    return paper
    except Exception:
        pass

    return None


@router.get("/{session_id}/preview")
async def get_paper_preview(
    session_id: str, layout: str = "2 Column", font: str = "Times New Roman"
):
    """Return the IEEE-typeset paper as rendered HTML for instant iframe preview.

    This endpoint serves the same styled HTML used for PDF generation but returns
    it directly as text/html so the frontend iframe can display it without needing
    Playwright or any PDF rendering dependency.
    """
    paper_data = await _get_paper_data(session_id)

    from services.pdf_generator import (
        HTML_TEMPLATE,
        KATEX_AUTO_INLINE,
        KATEX_CSS_INLINE,
        KATEX_JS_INLINE,
        _build_sections_html,
        _escape_html,
        _font_css_from_name,
    )

    title = _escape_html(paper_data.get("title", "Research Paper"))
    abstract = _escape_html(paper_data.get("abstract", ""))
    keywords_list = paper_data.get("keywords", [])
    keywords = (
        ", ".join(str(k) for k in keywords_list)
        if isinstance(keywords_list, list)
        else str(keywords_list)
    )
    keywords = _escape_html(keywords)
    authors_list = paper_data.get("authors", ["ResearchOS Autonomous System"])
    authors = (
        ", ".join(str(a) for a in authors_list)
        if isinstance(authors_list, list)
        else str(authors_list)
    )
    authors = _escape_html(authors)

    # Column count
    column_count = "2"
    if layout == "1 Column":
        column_count = "1"
    elif layout == "Multi Column":
        column_count = "3"

    # Font CSS
    font_family = _font_css_from_name(font)

    sections = paper_data.get("sections", [])
    content_md = paper_data.get("content_markdown", "")
    if content_md and content_md.strip().startswith("<!DOCTYPE"):
        content_md = ""
    content_html = _build_sections_html(sections, content_md)

    references_html = ""
    for ref in paper_data.get("references", []):
        ref_clean = _escape_html(str(ref))
        references_html += f'<li class="reference-item">{ref_clean}</li>\n'

    affiliation = _escape_html(
        paper_data.get("affiliation", "ResearchOS Autonomous Research System")
    )
    email = paper_data.get("email", "")
    email_html = f'<div class="author-email">{_escape_html(email)}</div>' if email else ""

    full_html = HTML_TEMPLATE.format(
        title=title,
        authors=authors,
        affiliation=affiliation,
        email_html=email_html,
        abstract=abstract,
        keywords=keywords,
        font_css=font_family,
        column_count=column_count,
        content_html=content_html,
        references_html=references_html,
        katex_css_inline=KATEX_CSS_INLINE,
        katex_js_inline=KATEX_JS_INLINE,
        katex_auto_inline=KATEX_AUTO_INLINE,
    )

    return Response(content=full_html, media_type="text/html")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((RuntimeError, IOError, OSError)),
)
async def _compile_pdf_with_retry(paper_data: dict, layout: str, font: str) -> bytes:
    """Compile paper to PDF with endpoint-level retry."""
    from services.pdf_generator import PDFGenerator

    return await PDFGenerator.compile_paper_to_pdf(
        paper_data=paper_data,
        layout=layout,
        font=font,
    )


@router.get("/{session_id}/pdf")
async def get_paper_pdf(session_id: str, layout: str = "2 Column", font: str = "Times New Roman"):
    """Generate and return a publication-quality PDF for the paper."""
    paper_data = await _get_paper_data(session_id)

    try:
        pdf_bytes = await _compile_pdf_with_retry(
            paper_data=paper_data,
            layout=layout,
            font=font,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=paper_{session_id}.pdf"},
        )
    except Exception as e:
        logger.error("pdf_generation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"PDF Generation failed: {str(e)}")


@router.post("/{session_id}/pdf")
async def compile_custom_pdf(session_id: str, paper_data: dict):
    """Compile a user-edited paper state directly to PDF."""
    try:
        layout = paper_data.get("layout", "2 Column")
        font = paper_data.get("font", "Times New Roman")
        pdf_bytes = await _compile_pdf_with_retry(
            paper_data=paper_data,
            layout=layout,
            font=font,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=paper_edited_{session_id}.pdf"},
        )
    except Exception as e:
        logger.error("custom_pdf_generation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"PDF Generation failed: {str(e)}")


@router.get("/{session_id}/diagnostics")
async def get_diagnostics(session_id: str):
    """Retrieve pipeline diagnostics and agent executions for a session."""
    metadata = get_metadata_store()
    await metadata._ensure_backend()

    executions = []
    if metadata._using_fallback:
        executions = [e for e in metadata._memory._executions if e.get("session_id") == session_id]
    else:
        from sqlalchemy import text

        async with metadata._session_factory() as db:
            result = await db.execute(
                text("""
                    SELECT id, agent_name, status, input_data, output_data, tokens_used, duration_ms, error, created_at,
                           model_name, tokens_in, tokens_out, cost, latency
                    FROM agent_executions
                    WHERE session_id = :sid
                    ORDER BY created_at ASC
                """),
                {"sid": session_id},
            )
            rows = result.mappings().all()
            executions = [dict(row) for row in rows]

    # Retrieve session info
    session = await metadata.get_session(session_id)
    topic = session.get("prompt") if session else "Unknown"

    # Retrieve claims, sources, etc.
    session_mem = get_session_memory()
    state = await session_mem.get_state(session_id) or {}

    return {
        "session_id": session_id,
        "topic": state.get("topic", topic),
        "search_queries": state.get("search_queries", []),
        "search_results": state.get("search_results", []),
        "browser_urls": [p.get("url") for p in state.get("browsed_pages", [])]
        if state.get("browsed_pages")
        else [],
        "reader_documents": state.get("documents", []),
        "claims_generated": state.get("claims", []),
        "citations_collected": state.get("citations", []),
        "writer_prompt": state.get("writer_prompt", ""),
        "raw_llm_output": state.get("raw_llm_output", ""),
        "final_paper": state.get("final_paper", {}),
        "citation_agent_input": state.get("citation_agent_input", {}),
        "citation_agent_output": state.get("citation_agent_output", {}),
        "citation_agent_error": state.get("citation_agent_error", ""),
        "firecrawl_requests": state.get("firecrawl_requests", 0),
        "firecrawl_success": state.get("firecrawl_success", 0),
        "firecrawl_failed": state.get("firecrawl_failed", 0),
        "firecrawl_latency_ms": state.get("firecrawl_latency_ms", 0),
        "executions": executions,
    }


@router.get("")
async def list_sessions():
    """List recent research sessions."""
    metadata = get_metadata_store()
    try:
        # In-memory backend has its own list method
        if metadata._using_fallback:
            return await metadata._memory.list_sessions()

        async with metadata._session_factory() as db:
            from sqlalchemy import text

            result = await db.execute(
                text("""
                    SELECT id, prompt, status, created_at, completed_at
                    FROM research_sessions
                    ORDER BY created_at DESC
                    LIMIT 20
                """)
            )
            rows = result.mappings().all()
            return [dict(row) for row in rows]
    except Exception:
        return []
