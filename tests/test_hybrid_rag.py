"""
Unit tests for True Hybrid RAG Retriever (Dense + Sparse RRF, Deduplication, Metadata).
"""

import pytest
from src.rag.document_loader import KnowledgeBaseLoader
from src.rag.retriever import KnowledgeRetriever


@pytest.fixture
def retriever():
    return KnowledgeRetriever(use_chroma=False)


def test_hybrid_search_fusion(retriever):
    """Verifies that both dense and sparse channels participate in hybrid retrieval."""
    results = retriever.retrieve("Full Spectrum Deterrence strategic command", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert "score" in top
    assert "citation" in top
    assert "source_id" in top
    assert "defence" in top["source_id"] or "official" in top["source_id"] or "current_affairs" in top["source_type"]


def test_jaccard_deduplication(retriever):
    """Tests exact Jaccard deduplication logic."""
    text_a = "The candidate demonstrated strong leadership and organizing ability under stress."
    text_b = "The candidate demonstrated strong leadership and organizing ability under stress and pressure."
    jaccard = retriever._compute_jaccard_similarity(text_a, text_b)
    assert jaccard > 0.60

    # Disjoint text should have zero jaccard
    jaccard_zero = retriever._compute_jaccard_similarity("Apples and oranges", "Strategic naval warfare doctrine")
    assert jaccard_zero == 0.0


def test_authority_multiplier(retriever):
    """Tests that official sources receive authority multipliers."""
    official_results = retriever.retrieve("14 officer like qualities", top_k=2, prefer_official=True)
    assert len(official_results) > 0
    assert official_results[0]["source_type"] == "official"
    assert official_results[0]["authority_level"] == 1
