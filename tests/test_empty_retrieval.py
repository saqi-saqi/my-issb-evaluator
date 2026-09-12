"""
Unit tests for empty retrieval handling, relevance thresholds, and abstention guarantees (V2).
Ensures the retriever abstains on out-of-domain/nonsense queries without false grounding.
"""

import pytest
from src.rag.retriever import KnowledgeRetriever


@pytest.fixture
def retriever():
    return KnowledgeRetriever(use_chroma=False, relevance_threshold=0.20)


def test_nonsense_query_abstention(retriever):
    """Test that a nonsensical query that produces no matches cleanly abstains (returns empty list)."""
    results = retriever.retrieve("xyzabc123456789_nonexistent_token_strictly_impossible", top_k=3)
    assert len(results) == 0, "Retriever must cleanly abstain on nonsense queries without false grounding"


def test_strict_filter_fallback(retriever):
    """Test filtering by nonexistent source_type falls back gracefully by relaxing strict filters."""
    results = retriever.retrieve("leadership", source_type="nonexistent_type", top_k=2)
    assert len(results) > 0
    assert "text" in results[0]


def test_relevance_threshold_filtering():
    """Test that retriever respects relevance_threshold."""
    # Low threshold returns matches
    low_thresh_retriever = KnowledgeRetriever(use_chroma=False, relevance_threshold=0.01)
    low_res = low_thresh_retriever.retrieve("officer cadet selection", top_k=4)
    assert len(low_res) > 0

    # Very high threshold triggers clean abstention without false grounding
    high_thresh_retriever = KnowledgeRetriever(use_chroma=False, relevance_threshold=0.99)
    high_res = high_thresh_retriever.retrieve("officer cadet selection", top_k=4)
    assert len(high_res) == 0
