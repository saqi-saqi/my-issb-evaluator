"""
RAG Benchmark Evaluation Suite for MY_ISSB_Evaluator (Consolidated Architecture).
Measures Recall@K, Precision@K, MRR, Citation Accuracy, and Abstention Accuracy
against the gold-standard evaluation dataset using core.rag.KnowledgeRetriever.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from core.rag import KnowledgeRetriever


def run_rag_benchmark(
    dataset_path: Optional[Path] = None,
    top_k: int = 4,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Executes full evaluation on gold-standard dataset.
    Returns quantitative metric summary.
    """
    if dataset_path is None:
        dataset_path = Path(__file__).resolve().parent.parent / "data" / "rag_eval_dataset.json"

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    retriever = KnowledgeRetriever()

    total_queries = len(dataset)
    in_domain_queries = [q for q in dataset if not q.get("should_abstain", False)]
    abstention_queries = [q for q in dataset if q.get("should_abstain", False)]

    recall_at_1_count = 0
    recall_at_3_count = 0
    recall_at_5_count = 0
    reciprocal_ranks = []
    precision_scores = []
    citation_accuracy_count = 0
    correct_abstentions = 0

    # 1. Evaluate In-Domain Queries
    for item in in_domain_queries:
        query = item["query"]
        expected_src = item.get("expected_source_type")
        expected_topics = item.get("expected_topics", [])
        relevant_terms = item.get("relevant_terms", [])

        results = retriever.retrieve(query, top_k=max(top_k, 5))

        if not results:
            reciprocal_ranks.append(0.0)
            precision_scores.append(0.0)
            continue

        # Check hits at rank 1, 3, 5
        hit_rank = 0
        relevant_in_results = 0

        for rank, res in enumerate(results, 1):
            is_match = False
            if isinstance(expected_src, list):
                src_match = (res.get("source_type") in expected_src or res.get("tier") in expected_src)
            else:
                src_match = (
                    expected_src is None
                    or res.get("source_type") == expected_src
                    or res.get("tier") == expected_src
                )

            topic_match = any(
                t in res.get("topic", "").lower()
                or t in res.get("source_file", "").lower()
                or t in res.get("title", "").lower()
                for t in expected_topics
            )
            text_match = any(term.lower() in res.get("text", "").lower() for term in relevant_terms)

            if src_match and (topic_match or text_match):
                is_match = True
                relevant_in_results += 1
                if hit_rank == 0:
                    hit_rank = rank

        if hit_rank == 1:
            recall_at_1_count += 1
        if 1 <= hit_rank <= 3:
            recall_at_3_count += 1
        if 1 <= hit_rank <= 5:
            recall_at_5_count += 1

        rr = (1.0 / hit_rank) if hit_rank > 0 else 0.0
        reciprocal_ranks.append(rr)

        prec = relevant_in_results / len(results) if results else 0.0
        precision_scores.append(prec)

        # Check citation accuracy for top result
        top_res = results[0]
        if "citation" in top_res and len(top_res["citation"]) > 5:
            if expected_src is None:
                citation_accuracy_count += 1
            elif isinstance(expected_src, list) and (
                top_res.get("source_type") in expected_src or top_res.get("tier") in expected_src
            ):
                citation_accuracy_count += 1
            elif isinstance(expected_src, str) and (
                expected_src in top_res.get("source_type", "") or expected_src in top_res.get("tier", "")
            ):
                citation_accuracy_count += 1

    # 2. Evaluate Abstention Queries
    for item in abstention_queries:
        query = item["query"]
        results = retriever.retrieve(query, top_k=top_k)
        if len(results) == 0:
            correct_abstentions += 1

    # Aggregate Metrics
    n_in_domain = max(len(in_domain_queries), 1)
    n_abstain = max(len(abstention_queries), 1)

    r_at_1 = recall_at_1_count / n_in_domain
    r_at_3 = recall_at_3_count / n_in_domain
    r_at_5 = recall_at_5_count / n_in_domain
    mrr = float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0
    mean_precision = float(np.mean(precision_scores)) if precision_scores else 0.0
    citation_acc = citation_accuracy_count / n_in_domain
    abstention_acc = correct_abstentions / n_abstain

    summary = {
        "total_benchmark_queries": total_queries,
        "in_domain_queries": len(in_domain_queries),
        "abstention_queries": len(abstention_queries),
        "recall_at_1": round(r_at_1 * 100, 2),
        "recall_at_3": round(r_at_3 * 100, 2),
        "recall_at_5": round(r_at_5 * 100, 2),
        "mean_reciprocal_rank_mrr": round(mrr, 4),
        "mean_precision_at_k": round(mean_precision * 100, 2),
        "citation_provenance_accuracy": round(citation_acc * 100, 2),
        "abstention_accuracy": round(abstention_acc * 100, 2),
        "status": "PASSED" if (r_at_3 >= 0.80 and mrr >= 0.70) else "NEEDS_IMPROVEMENT",
    }

    if verbose:
        print("\n" + "=" * 60)
        print("MY_ISSB_Evaluator -- RAG Quality Benchmark Results")
        print("=" * 60)
        print(f"Total Benchmark Queries:    {total_queries}")
        print(f"Recall@1:                   {summary['recall_at_1']}%")
        print(f"Recall@3:                   {summary['recall_at_3']}%")
        print(f"Recall@5:                   {summary['recall_at_5']}%")
        print(f"Mean Reciprocal Rank (MRR): {summary['mean_reciprocal_rank_mrr']}")
        print(f"Precision@K:                {summary['mean_precision_at_k']}%")
        print(f"Citation Provenance:        {summary['citation_provenance_accuracy']}%")
        print(f"Abstention on Out-of-Domain:{summary['abstention_accuracy']}%")
        print(f"Overall Quality Gate:       {summary['status']}")
        print("=" * 60 + "\n")

    return summary


if __name__ == "__main__":
    run_rag_benchmark()
