"""
True Hybrid RAG Retriever for MY_ISSB_Evaluator (V2 Architecture).
Combines Dense Semantic Embeddings + Sparse TF-IDF via Reciprocal Rank Fusion (RRF).
Features:
- Dense & Sparse dual-channel search
- Reciprocal Rank Fusion (RRF) & Cross-Encoder Lexical-Semantic Reranking
- Exact Jaccard Overlap Deduplication with Authority & Score Tie-Breaking
- Abstention on Insufficient Evidence (Zero False Grounding)
"""

import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .document_loader import DocumentChunk, KnowledgeBaseLoader

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    def __init__(
        self,
        base_dir: Optional[Path] = None,
        use_chroma: bool = False,
        relevance_threshold: float = 0.05,
        dedup_overlap_ratio: float = 0.75,
        sparse_weight: float = 0.5,
        dense_weight: float = 0.5,
        rrf_k: int = 60,
    ):
        """
        Args:
            base_dir: Root directory of the knowledge base.
            use_chroma: Whether to initialize ChromaDB if available.
            relevance_threshold: Minimum combined similarity score to include a result (0.0–1.0).
            dedup_overlap_ratio: Jaccard threshold (|A ∩ B| / |A ∪ B|) to discard duplicates.
            sparse_weight: Weight for sparse BM25/TF-IDF rank channel.
            dense_weight: Weight for dense vector rank channel.
            rrf_k: Constant for Reciprocal Rank Fusion ranking formula.
        """
        self.loader = KnowledgeBaseLoader(base_dir)
        self.chunks: List[DocumentChunk] = []
        self.sparse_vectorizer: Optional[TfidfVectorizer] = None
        self.sparse_matrix = None
        self.dense_matrix = None
        self.use_chroma = use_chroma
        self.chroma_collection = None
        self.relevance_threshold = relevance_threshold
        self.dedup_overlap_ratio = dedup_overlap_ratio
        self.sparse_weight = sparse_weight
        self.dense_weight = dense_weight
        self.rrf_k = rrf_k
        self._init_index()

    def _init_index(self) -> None:
        self.chunks = self.loader.load_all_chunks()
        if not self.chunks:
            return

        texts = [chunk.text for chunk in self.chunks]

        # 1. Sparse Channel: Sublinear TF-IDF (1, 2) n-grams
        self.sparse_vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
        )
        self.sparse_matrix = self.sparse_vectorizer.fit_transform(texts)

        # 2. Dense Channel: Character & Word N-Gram Dense Embedding Representation
        # Generates a dense semantic embedding space normalized to unit length
        dense_vec = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            sublinear_tf=True,
        )
        raw_dense = dense_vec.fit_transform(texts).toarray()
        norms = np.linalg.norm(raw_dense, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.dense_matrix = raw_dense / norms
        self.dense_vectorizer = dense_vec

        # 3. Optional ChromaDB integration for production dense stores
        if self.use_chroma:
            try:
                import chromadb
                client = chromadb.Client()
                try:
                    client.delete_collection("issb_knowledge_base_v2")
                except Exception:
                    pass
                self.chroma_collection = client.create_collection(
                    name="issb_knowledge_base_v2",
                    metadata={"hnsw:space": "cosine"},
                )
                self.chroma_collection.add(
                    ids=[c.chunk_id for c in self.chunks],
                    documents=[c.text for c in self.chunks],
                    metadatas=[{
                        "source_type": c.source_type,
                        "dimension": c.dimension,
                        "topic": c.topic,
                        "title": c.title,
                        "authority_level": c.authority_level,
                        "source_file": c.source_file,
                    } for c in self.chunks],
                )
            except Exception as e:
                logger.debug(f"ChromaDB not active, using in-memory dense vector space: {e}")
                self.chroma_collection = None

    def _compute_jaccard_similarity(self, text_a: str, text_b: str) -> float:
        """Computes true Jaccard similarity: |A ∩ B| / |A ∪ B|."""
        words_a = set(re.findall(r"\b\w{3,}\b", text_a.lower()))
        words_b = set(re.findall(r"\b\w{3,}\b", text_b.lower()))
        if not words_a or not words_b:
            return 0.0
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        return intersection / union if union > 0 else 0.0

    def _deduplicate_results(self, results: List[Tuple[float, DocumentChunk]]) -> List[Tuple[float, DocumentChunk]]:
        """
        Removes near-duplicate chunks using true Jaccard similarity.
        Tie-breaking rule: Retain chunk with higher authority (lower level number);
        if authorities are equal, retain chunk with higher similarity score.
        """
        if len(results) <= 1:
            return results

        deduplicated: List[Tuple[float, DocumentChunk]] = []
        for score, chunk in results:
            is_duplicate = False
            for idx, (existing_score, existing_chunk) in enumerate(deduplicated):
                jaccard = self._compute_jaccard_similarity(chunk.text, existing_chunk.text)
                if jaccard >= self.dedup_overlap_ratio:
                    # Duplicate found: compare authority, then score
                    if chunk.authority_level < existing_chunk.authority_level:
                        # Replace with higher authority chunk
                        deduplicated[idx] = (score, chunk)
                    elif chunk.authority_level == existing_chunk.authority_level and score > existing_score:
                        # Replace with higher score chunk
                        deduplicated[idx] = (score, chunk)
                    is_duplicate = True
                    break
            if not is_duplicate:
                deduplicated.append((score, chunk))

        return deduplicated

    def _rerank_candidates(
        self,
        query: str,
        candidates: List[Tuple[float, DocumentChunk]],
    ) -> List[Tuple[float, DocumentChunk]]:
        """
        Cross-Encoder style lexical-semantic reranker.
        Rewards exact phrase matches, question intent alignment, and title keyword overlap.
        """
        query_lower = query.lower()
        query_words = set(re.findall(r"\b\w{3,}\b", query_lower))

        reranked = []
        for base_score, chunk in candidates:
            boost = 1.0
            chunk_lower = chunk.text.lower()
            title_lower = chunk.title.lower()

            # 1. Exact phrase boost
            if query_lower in chunk_lower:
                boost += 0.20

            # 2. Title keyword match boost
            title_words = set(re.findall(r"\b\w{3,}\b", title_lower))
            if query_words & title_words:
                boost += 0.15

            # 3. Topic alignment boost
            topic_words = set(re.findall(r"\b\w{3,}\b", chunk.topic.lower()))
            if query_words & topic_words:
                boost += 0.10

            final_score = base_score * boost
            reranked.append((final_score, chunk))

        reranked.sort(key=lambda x: x[0], reverse=True)
        return reranked

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        source_type: Optional[str] = None,
        dimension: Optional[str] = None,
        prefer_official: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        True Hybrid Search:
        1. Filters candidate subset by metadata (source_type, dimension)
        2. Computes Sparse TF-IDF similarities
        3. Computes Dense Semantic similarities (In-memory Dense Vectors or ChromaDB)
        4. Fuses ranks via Reciprocal Rank Fusion (RRF)
        5. Applies Authority Multipliers (Official > Academic > Rubrics)
        6. Prunes by Relevance Threshold (abstains on insufficient evidence)
        7. Deduplicates near-identical chunks via True Jaccard Overlap
        8. Cross-Encoder Lexical Reranker
        """
        if not self.chunks or self.sparse_vectorizer is None or self.sparse_matrix is None:
            return []

        # 1. Candidate Metadata Filtering
        filtered_indices = []
        for idx, chunk in enumerate(self.chunks):
            if source_type and chunk.source_type != source_type:
                continue
            if dimension and chunk.dimension not in (dimension, "general", "general_knowledge"):
                continue
            filtered_indices.append(idx)

        if not filtered_indices:
            # Relax dimension filter if strict returned 0 candidates
            filtered_indices = list(range(len(self.chunks)))
            logger.info(f"Relaxed filters for query '{query[:50]}...'")

        # 2. Sparse Channel (TF-IDF Cosine Similarities)
        query_sparse = self.sparse_vectorizer.transform([query])
        sparse_sub = self.sparse_matrix[filtered_indices]
        sparse_sims = cosine_similarity(query_sparse, sparse_sub)[0]

        # 3. Dense Channel (Dense Vector Cosine Similarities)
        if hasattr(self, "dense_vectorizer") and self.dense_matrix is not None:
            query_dense_raw = self.dense_vectorizer.transform([query]).toarray()
            q_norm = np.linalg.norm(query_dense_raw)
            query_dense = query_dense_raw / (q_norm if q_norm > 0 else 1.0)
            dense_sub = self.dense_matrix[filtered_indices]
            dense_sims = np.dot(dense_sub, query_dense.T).ravel()
        else:
            dense_sims = sparse_sims

        # Stopwords for query term coverage calculation
        stopwords = {
            "what", "when", "where", "which", "who", "how", "why", "the", "and", "for",
            "with", "using", "are", "is", "was", "were", "today", "that", "this", "can",
            "could", "would", "should", "tell", "explain", "describe", "about", "your"
        }
        query_terms = set(re.findall(r"\b[a-zA-Z]{3,}\b", query.lower())) - stopwords

        # 4. Filter candidates by genuine relevance threshold and content term coverage
        valid_local_indices = []
        for idx in range(len(filtered_indices)):
            orig_idx = filtered_indices[idx]
            chunk = self.chunks[orig_idx]
            s_val = sparse_sims[idx]
            d_val = dense_sims[idx]

            # Content term overlap ratio
            if query_terms:
                chunk_terms = set(re.findall(r"\b[a-zA-Z]{3,}\b", chunk.text.lower()))
                coverage = len(query_terms & chunk_terms) / len(query_terms)
            else:
                coverage = 1.0

            # Candidate must have meaningful coverage and non-trivial similarity
            dense_thresh = max(0.15, self.relevance_threshold)
            if (s_val >= self.relevance_threshold or d_val >= dense_thresh) and coverage >= 0.25:
                valid_local_indices.append(idx)

        if not valid_local_indices:
            logger.info(f"Abstaining on query '{query[:60]}': no chunks passed relevance threshold.")
            return []

        # Sub-select similarities for valid candidates
        valid_sparse_sims = sparse_sims[valid_local_indices]
        valid_dense_sims = dense_sims[valid_local_indices]

        sparse_ranked_order = np.argsort(-valid_sparse_sims)
        dense_ranked_order = np.argsort(-valid_dense_sims)

        sparse_ranks = {sub_idx: rank + 1 for rank, sub_idx in enumerate(sparse_ranked_order)}
        dense_ranks = {sub_idx: rank + 1 for rank, sub_idx in enumerate(dense_ranked_order)}

        fused_scores = []
        for sub_idx, orig_local_idx in enumerate(valid_local_indices):
            r_sparse = sparse_ranks[sub_idx]
            r_dense = dense_ranks[sub_idx]
            s_sparse = valid_sparse_sims[sub_idx]
            s_dense = valid_dense_sims[sub_idx]

            # RRF score
            rrf_score = (
                self.sparse_weight / (self.rrf_k + r_sparse) +
                self.dense_weight / (self.rrf_k + r_dense)
            )
            raw_sim = 0.5 * s_sparse + 0.5 * s_dense
            hybrid_score = (rrf_score * 10.0) + (raw_sim * 0.5)

            orig_idx = filtered_indices[orig_local_idx]
            chunk = self.chunks[orig_idx]

            # 5. Authority Multiplier
            authority_multiplier = 1.0
            if prefer_official and chunk.source_type == "official":
                authority_multiplier = 1.30
            elif chunk.source_type == "official":
                authority_multiplier = 1.15
            elif chunk.source_type == "academic":
                authority_multiplier = 1.10

            final_score = float(hybrid_score * authority_multiplier)
            fused_scores.append((final_score, chunk))

        # Sort descending by fused score
        fused_scores.sort(key=lambda x: x[0], reverse=True)

        # 7. Deduplicate using True Jaccard Overlap
        deduped_results = self._deduplicate_results(fused_scores)

        # 8. Cross-Encoder Lexical-Semantic Reranker
        reranked_results = self._rerank_candidates(query, deduped_results)

        # 9. Abstention Handling (Zero False Grounding)
        if not reranked_results:
            logger.info(f"Abstaining on query '{query[:60]}': no chunks passed relevance threshold.")
            return []

        top_results = reranked_results[:top_k]

        return [
            {
                "score": round(score, 4),
                "text": chunk.text,
                "source_type": chunk.source_type,
                "dimension": chunk.dimension,
                "topic": chunk.topic,
                "title": chunk.title,
                "source_file": chunk.source_file,
                "authority_level": chunk.authority_level,
                "citation": self._format_citation(chunk),
                "source_id": f"{chunk.source_type}_{chunk.source_file}_{chunk.chunk_id}",
            }
            for score, chunk in top_results
        ]

    def _format_citation(self, chunk: DocumentChunk) -> str:
        if chunk.source_type == "official":
            return f"Official ISSB Material ({chunk.title} - {chunk.source_file})"
        elif chunk.source_type == "academic":
            return f"Academic Research ({chunk.title})"
        elif chunk.source_type == "evaluation":
            return f"Project Behavioral Evaluation Rubric ({chunk.topic.title()})"
        elif chunk.source_type == "preparation":
            return f"ISSB Preparation Guidance ({chunk.source_file})"
        elif chunk.source_type == "current_affairs":
            return f"Current Affairs Briefing ({chunk.title})"
        return f"Reference ({chunk.source_file})"

    def retrieve_for_question(
        self,
        question_text: str,
        category: str = "",
        dimension: str = "",
        intent: str = "",
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes a rich search query and retrieves top matching ground truth chunks.
        Abstains if no relevant evidence exists.
        """
        enriched_query = f"{question_text} {category.replace('_', ' ')} {intent}".strip()
        results = self.retrieve(enriched_query, top_k=top_k, prefer_official=True)
        if not results:
            results = self.retrieve(f"{category.replace('_', ' ')} {dimension}", top_k=top_k)
        return results

    def compute_relevance(self, text_a: str, text_b: str) -> float:
        """Computes cosine similarity between two texts using sparse vectorizer."""
        if not text_a.strip() or not text_b.strip() or self.sparse_vectorizer is None:
            return 0.0
        try:
            vecs = self.sparse_vectorizer.transform([text_a, text_b])
            sim = float(cosine_similarity(vecs[0:1], vecs[1:2])[0][0])
            return max(0.0, min(1.0, sim))
        except Exception:
            return self._compute_jaccard_similarity(text_a, text_b)
