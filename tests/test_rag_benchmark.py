"""
Pytest integration for RAG Quality Benchmark Suite.
Ensures retrieval accuracy and abstention quality gates pass automatically in CI/CD.
"""

import pytest
from src.rag.benchmark import run_rag_benchmark


def test_rag_quality_benchmark():
    """Runs the 30-query gold-standard benchmark and asserts quality gates."""
    summary = run_rag_benchmark(verbose=False)
    assert summary["recall_at_3"] >= 85.0, f"Recall@3 was {summary['recall_at_3']}%, expected >= 85%"
    assert summary["mean_reciprocal_rank_mrr"] >= 0.80, f"MRR was {summary['mean_reciprocal_rank_mrr']}, expected >= 0.80"
    assert summary["abstention_accuracy"] >= 90.0, f"Abstention was {summary['abstention_accuracy']}%, expected >= 90%"
    assert summary["citation_provenance_accuracy"] >= 85.0, f"Citation was {summary['citation_provenance_accuracy']}%, expected >= 85%"
    assert summary["status"] == "PASSED"
