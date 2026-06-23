import os
import sys

import pytest

from services.relevance_checker import calculate_relevance, ensure_paragraph_relevance

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture(autouse=True)
def mock_embeddings(monkeypatch):
    def mock_embed(query):
        q_lower = query.lower()
        if "pasta" in q_lower or "cooking" in q_lower:
            return [1.0] + [0.0] * 383
        elif "cinema" in q_lower or "film" in q_lower or "bollywood" in q_lower or "parallel" in q_lower:
            return [0.0, 1.0] + [0.0] * 382
        else:
            return [0.0, 0.0, 1.0] + [0.0] * 381
            
    def mock_cos_sim(a, b):
        # Dot product because vectors are normalized
        import numpy as np
        return float(np.dot(a, b))

    monkeypatch.setattr("retrieval.embeddings.embed_query_sync", mock_embed)
    monkeypatch.setattr("retrieval.embeddings.cosine_similarity", mock_cos_sim)


def test_calculate_relevance_technical():
    # Technical topic
    topic = "ANFIS Control of Interleaved DC-DC Converter"
    paragraph = "The ANFIS controller regulates the duty cycle of the interleaved buck converter, reducing the transient response time and steady-state voltage ripple."
    assert calculate_relevance(paragraph, topic) >= 0.85

    # Paragraph with absolutely no related words
    irrelevant_p = "This is a paragraph about cooking delicious Italian pasta in Rome."
    assert calculate_relevance(irrelevant_p, topic) == 0.0

def test_calculate_relevance_non_technical_forbidden_terms():
    # Non-technical topic: Indian Cinema
    topic = "Narrative Shifts in modern Indian Cinema"
    
    # Paragraph containing forbidden technical terms like 'cnn' or 'kubernetes'
    bad_paragraph = "Indian cinema is evolving, but standard CNN architectures and Kubernetes clusters are needed to benchmark throughput."
    assert calculate_relevance(bad_paragraph, topic) == 0.0

    # Relevant paragraph without forbidden terms
    good_paragraph = "Indian cinema has seen a major shift, with regional parallel cinema challenging Bollywood's historic box office dominance."
    assert calculate_relevance(good_paragraph, topic) >= 0.90

@pytest.mark.asyncio
async def test_ensure_paragraph_relevance():
    os.environ["MOCK_LLM"] = "True"
    topic = "Indian Cinema"
    paragraph = "The parallel cinema movement in India emerged as a socio-political critique."
    
    # Should return paragraph as-is since it is already relevant
    res = await ensure_paragraph_relevance(paragraph, topic)
    assert res == paragraph

    # Should rewrite paragraph if it contains forbidden terms
    bad_p = "Indian cinema is great, but we need to run it on a CNN with GPUs and Kubernetes to measure latency."
    res2 = await ensure_paragraph_relevance(bad_p, topic)
    
    # Verify that forbidden terms have been replaced or paragraph grounded
    assert "cnn" not in res2.lower()
    assert "gpu" not in res2.lower()
    assert "kubernetes" not in res2.lower()
