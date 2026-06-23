import asyncio
import sys
sys.path.insert(0, r'D:\research os\backend')
from agents.firecrawl_extract import FirecrawlExtractAgent

async def test():
    agent = FirecrawlExtractAgent()
    result = await agent.run(
        input_data={
            'topic': 'Transformer Architectures',
            'results': [
                {'url': 'https://arxiv.org/abs/1706.03762', 'title': 'Attention Is All You Need'},
                {'url': 'https://arxiv.org/abs/1810.04805', 'title': 'BERT'},
            ],
            'max_pages': 2
        },
        context={}
    )
    print('Status:', result['status'])
    print('Pages:', len(result['data'].get('pages', [])))
    for p in result['data'].get('pages', []):
        print(f'  - {p["url"]}: {p["word_count"]} words')

asyncio.run(test())
