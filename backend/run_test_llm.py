"""Quick LLM connectivity test."""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    key = os.getenv("OPENROUTER_API_KEY", "")
    base = os.getenv("OPENROUTER_BASE_URL", "")
    print(f"Key: {key[:12]}...{key[-6:]}")
    print(f"Base: {base}")

    async with httpx.AsyncClient(
        base_url=base,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        timeout=30.0,
    ) as client:
        resp = await client.post(
            "/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Say hello in 5 words"}],
                "max_tokens": 50,
            },
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        if resp.status_code == 200:
            content = data["choices"][0]["message"]["content"]
            print(f"Response: {content}")
            print("✅ LLM PIPELINE WORKING!")
        else:
            print(f"Error: {data}")
            print("❌ LLM PIPELINE FAILED")

asyncio.run(test())
