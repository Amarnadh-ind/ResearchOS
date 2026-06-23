import asyncio
import sys
sys.path.insert(0, r'D:\research os\backend')
from graph.nodes import search_node, firecrawl_extract_node

async def test():
    state = {
        'topic': 'Transformer Architectures',
        'search_queries': [
            'Transformer architecture self-attention',
            'BERT architecture',
        ],
        'max_sources': 5
    }
    
    # Run search first
    search_result = await search_node(state)
    print('Search result keys:', search_result.keys())
    print('Search results:', len(search_result.get('search_results', [])))
    
    # Now run firecrawl with search results
    state.update(search_result)
    firecrawl_result = await firecrawl_extract_node(state)
    print('Firecrawl result keys:', firecrawl_result.keys())
    print('Browsed pages:', len(firecrawl_result.get('browsed_pages', [])))
    for p in firecrawl_result.get('browsed_pages', []):
        print('  -', p['url'], ':', p['word_count'], 'words')

asyncio.run(test())
