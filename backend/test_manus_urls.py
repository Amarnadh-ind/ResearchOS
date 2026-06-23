import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('MANUS_API_KEY', '')

# Test multiple URL variations
urls = [
    'https://api.manus.im/v1/chat/completions',
    'https://api.manus.im/chat/completions',
    'https://api.manus.ai/v1/chat/completions',
    'https://manus.ai/api/v1/chat/completions',
]

async def test(url):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(url, headers={'API_KEY': key, 'Content-Type': 'application/json'}, json={'model': 'manus', 'messages': [{'role': 'user', 'content': 'Hello'}], 'max_tokens': 10})
            print(f'{url} -> {r.status_code}: {r.text[:300]}')
    except Exception as e:
        print(f'{url} -> ERROR: {type(e).__name__}: {e}')

async def main():
    for url in urls:
        await test(url)

asyncio.run(main())
