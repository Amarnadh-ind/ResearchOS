import os
import sys
import time

import httpx
import pytest
from dotenv import load_dotenv

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# This test requires real API keys - only run when explicitly requested
# Run with: pytest tests/test_llm_connectivity.py -m integration
pytestmark = pytest.mark.integration

def test_llm_connectivity():
    # Load .env at test runtime (not module load time) to avoid fixture interference
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
    
    key = os.getenv("GEMINI_API_KEY", "")
    
    # Skip if key is placeholder or not set
    if not key or key == "your_gemini_api_key_here":
        pytest.skip("GEMINI_API_KEY not configured (placeholder or missing)")
    key = os.getenv("GEMINI_API_KEY", "")
    
    print("\n=== LLM Connectivity Test ===")
    
    # 1. API key exists
    assert key, "GEMINI_API_KEY is missing from environment"
    print("1. API Key Exists: YES")
    
    # 2. Endpoint reachable & 3. Authentication
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    print("Connecting to Gemini generateContent endpoint")
    
    start_time = time.monotonic()
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            url,
            json={
                "contents": [{"parts": [{"text": "Say hello in 5 words"}]}],
                "generationConfig": {"maxOutputTokens": 200, "temperature": 0.2}
            }
        )
        latency = time.monotonic() - start_time
        
        status_code = resp.status_code
        print(f"2. Endpoint status: {status_code}")
        
        # Log requirements
        print("--- Telemetry Log ---")
        print("Provider: Gemini")
        print("Model: gemini-2.5-flash")
        print(f"Status Code: {status_code}")
        print(f"Latency: {latency:.2f}s")
        
        # 3. Authentication succeeds
        assert status_code in (200, 429), f"Authentication/Request failed with status {status_code}: {resp.text}"
        print("3. Authentication: SUCCESS")
        
        if status_code == 429:
            print("3. Authentication: SUCCESS (but Quota Exceeded)")
            print("4. Completion content: 'Skipped due to 429 Quota Exceeded'")
            print("======================")
            return

        # 4. Response check
        data = resp.json()
        assert "candidates" in data, f"Invalid API response: {data}"
        candidates = data["candidates"]
        assert len(candidates) > 0
        parts = candidates[0]["content"]["parts"]
        assert len(parts) > 0
        content = parts[0]["text"]
        assert content, "Response has no content"
        print(f"4. Completion content: '{content}'")
        print("======================")
        
        assert len(content.split()) > 0

