import sys
import os
import pytest

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.relevance_checker import calculate_relevance, ensure_paragraph_relevance, get_domain_forbidden_terms

def test_ev_topic_forbidden_terms():
    # If the topic is Electric Vehicles, it should block CNN, Transformer, ResNet, etc.
    topic = "Optimal Charging Control for Electric Vehicles"
    forbidden = get_domain_forbidden_terms(topic)
    
    assert "cnn" in forbidden
    assert "resnet" in forbidden
    assert "vision transformer" in forbidden
    
    # If the topic itself is CNN, it should NOT block it
    topic_cnn = "Robust CNN Architecture for Edge Devices"
    forbidden_cnn = get_domain_forbidden_terms(topic_cnn)
    assert "cnn" not in forbidden_cnn

def test_calculate_relevance_ev_blocks_ml():
    topic = "Advanced Battery Management Systems in EVs"
    
    # Paragraph describing battery states is fine
    good_p = "The battery management system (BMS) monitors the cell state of charge (SoC) and state of health (SoH) to optimize charging profile."
    assert calculate_relevance(good_p, topic) >= 0.85
    
    # Paragraph mentioning convolutional networks or CNNs in the context of battery is forbidden (unless requested)
    bad_p = "We propose using a CNN VGG-16 network architecture to optimize the battery voltage curves."
    assert calculate_relevance(bad_p, topic) == 0.0

@pytest.mark.asyncio
async def test_ensure_paragraph_relevance_rewrite(monkeypatch):
    # Mock embeddings to make it run fast
    def mock_embed(query):
        return [0.1] * 384
    def mock_cos_sim(a, b):
        return 0.90
        
    monkeypatch.setattr("retrieval.embeddings.embed_query_sync", mock_embed)
    monkeypatch.setattr("retrieval.embeddings.cosine_similarity", mock_cos_sim)
    
    topic = "Electric Vehicle Grid Integration"
    
    # Bad paragraph containing convolutional network
    bad_p = "Vehicle-to-Grid integration is analyzed using a CNN convolutional neural network to handle bidirectional power flow."
    
    # Rewrite should replace the forbidden term or ground it
    res = await ensure_paragraph_relevance(bad_p, topic)
    assert "cnn" not in res.lower()
    assert "convolutional" not in res.lower()
