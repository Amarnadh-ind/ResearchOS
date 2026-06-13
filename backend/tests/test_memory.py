import sys
import os
import pytest
import uuid

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from memory.session import SessionMemory, InMemorySessionBackend
from memory.metadata import MetadataStore, InMemoryMetadataBackend

@pytest.mark.asyncio
async def test_in_memory_session_backend():
    backend = InMemorySessionBackend()
    
    # Test set & get
    await backend.set("test_key", "test_value")
    assert await backend.get("test_key") == "test_value"
    
    # Test rpush & lrange
    await backend.rpush("list_key", "item1")
    await backend.rpush("list_key", "item2")
    items = await backend.lrange("list_key", 0, -1)
    assert items == ["item1", "item2"]
    
    # Test hset & hget
    await backend.hset("hash_key", "field1", "val1")
    assert await backend.hget("hash_key", "field1") == "val1"

@pytest.mark.asyncio
async def test_session_memory():
    # Use SessionMemory with fallback forced
    memory = SessionMemory()
    await memory.connect()
    
    session_id = str(uuid.uuid4())
    state = {"status": "planning", "topic": "AI"}
    
    await memory.set_state(session_id, state)
    retrieved = await memory.get_state(session_id)
    assert retrieved == state

    event = {"agent": "planner", "type": "progress", "msg": "Planning..."}
    await memory.push_event(session_id, event)
    events = await memory.get_events(session_id)
    assert len(events) == 1
    assert events[0]["agent"] == "planner"

@pytest.mark.asyncio
async def test_in_memory_metadata_backend():
    backend = InMemoryMetadataBackend()
    session_id = str(uuid.uuid4())
    
    # Create session
    session = await backend.create_session(session_id, "test prompt")
    assert session["id"] == session_id
    assert session["status"] == "pending"
    
    # Update status
    await backend.update_session_status(session_id, "completed")
    updated = await backend.get_session(session_id)
    assert updated["status"] == "completed"
    assert updated["completed_at"] is not None

    # Store source
    source_id = await backend.store_source(session_id, "http://url.com", "Title", "web", "content", "hash")
    assert source_id == "1"

    # Store claim
    claim_id = await backend.store_claim(session_id, "claim text", "evidence", source_id, 0.95)
    assert claim_id == "2"

    # Store paper
    paper_id = await backend.store_paper(session_id, "Paper Title", "Abstract", [], [], "content md")
    assert paper_id == "3"

@pytest.mark.asyncio
async def test_metadata_store():
    store = MetadataStore()
    session_id = str(uuid.uuid4())
    
    # MetadataStore dynamically connects (gracefully falls back to memory if DB not running)
    session = await store.create_session(session_id, "Test prompt")
    assert str(session["id"]) == session_id
    
    await store.update_session_status(session_id, "running")
    updated = await store.get_session(session_id)
    assert updated["status"] == "running"
    
    # Clean up
    await store.disconnect()
