"""
Unit tests for KnowledgeBaseLoader and KnowledgeRetriever.
"""

import pytest
from src.rag.document_loader import KnowledgeBaseLoader
from src.rag.retriever import KnowledgeRetriever


@pytest.fixture
def retriever():
    # Test with local vectorizer (use_chroma=False for test isolation)
    return KnowledgeRetriever(use_chroma=False)


def test_knowledge_base_loads_chunks():
    loader = KnowledgeBaseLoader()
    chunks = loader.load_all_chunks()
    assert len(chunks) > 0

    source_types = {c.source_type for c in chunks}
    assert "official" in source_types
    assert "academic" in source_types
    assert "evaluation" in source_types
    assert "current_affairs" in source_types


def test_retriever_queries(retriever):
    results = retriever.retrieve("leadership under stress", top_k=3)
    assert len(results) > 0
    assert "text" in results[0]
    assert "citation" in results[0]
    assert "authority_level" in results[0]


def test_retriever_metadata_filtering(retriever):
    official_results = retriever.retrieve("guidelines for selection", top_k=2, source_type="official")
    for r in official_results:
        assert r["source_type"] == "official"
        assert "Official ISSB" in r["citation"]

    academic_results = retriever.retrieve("emotional regulation", top_k=2, source_type="academic")
    for r in academic_results:
        assert r["source_type"] == "academic"
