"""
Streamlined Multi-Tier RAG Knowledge Retriever for MY_ISSB_Evaluator.
Uses TF-IDF + Cosine Similarity with metadata filtering and strict source provenance citations.
Operates across all 5 tiers: official, academic, evaluation, preparation, and current_affairs.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

TIER_AUTHORITY = {
    "official": 1,
    "academic": 2,
    "evaluation": 3,
    "preparation": 3,
    "current_affairs": 4,
}

TIER_LABELS = {
    "official": "Official Guidelines",
    "academic": "Academic Literature",
    "evaluation": "Evaluation Rubric",
    "preparation": "Preparation Guide",
    "current_affairs": "Current Affairs Briefing",
}


@dataclass
class KnowledgeChunk:
    id: str
    text: str
    source_file: str
    tier: str
    title: str

    @property
    def citation(self) -> str:
        label = TIER_LABELS.get(self.tier, self.tier.title())
        return f"[{label} | {self.title}]"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "source_file": self.source_file,
            "tier": self.tier,
            "title": self.title,
            "citation": self.citation,
        }


class KnowledgeRetriever:
    """Lightweight, deterministic TF-IDF retriever across the 5-tier ISSB knowledge base."""

    def __init__(self, kb_dir: Optional[Path] = None):
        if kb_dir is None:
            self.kb_dir = Path(__file__).resolve().parent.parent / "knowledge_base"
        else:
            self.kb_dir = Path(kb_dir)

        self.chunks: List[KnowledgeChunk] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.matrix = None
        self._load_and_index()

    def _load_and_index(self) -> None:
        """Walks knowledge_base/ directories, chunks markdown files, and builds TF-IDF index."""
        if not self.kb_dir.exists():
            logger.warning("Knowledge base directory not found at %s", self.kb_dir)
            return

        self.chunks = []
        chunk_count = 0

        for tier_name in ["official", "academic", "evaluation", "preparation", "current_affairs"]:
            tier_dir = self.kb_dir / tier_name
            if not tier_dir.exists():
                continue

            for file_path in tier_dir.rglob("*.md"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    title = file_path.stem.replace("_", " ").title()

                    # Simple header-based or paragraph chunking
                    sections = re.split(r"\n(?=#{1,3}\s+)", content)
                    for sec in sections:
                        sec_clean = sec.strip()
                        if len(sec_clean) < 40:
                            continue
                        chunk_count += 1
                        self.chunks.append(
                            KnowledgeChunk(
                                id=f"{tier_name}_{chunk_count:04d}",
                                text=sec_clean,
                                source_file=str(file_path.relative_to(self.kb_dir)),
                                tier=tier_name,
                                title=title,
                            )
                        )
                except Exception as e:
                    logger.warning("Error reading %s: %s", file_path, e)

        if self.chunks:
            texts = [c.text for c in self.chunks]
            self.vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                sublinear_tf=True,
                max_features=15000,
            )
            self.matrix = self.vectorizer.fit_transform(texts)
            logger.info("Indexed %d chunks across 5 tiers in %s", len(self.chunks), self.kb_dir)

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        tier: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves top-k relevant knowledge chunks with source citations."""
        if not self.chunks or self.vectorizer is None or self.matrix is None or not query.strip():
            return []

        try:
            q_vec = self.vectorizer.transform([query])
            similarities = cosine_similarity(q_vec, self.matrix).flatten()

            # Rank by score
            ranked_indices = np.argsort(similarities)[::-1]

            results: List[Dict[str, Any]] = []
            for idx in ranked_indices:
                score = float(similarities[idx])
                if score <= 0.01:
                    break

                chunk = self.chunks[idx]
                if tier and chunk.tier != tier:
                    continue

                res = chunk.to_dict()
                res["score"] = round(score, 4)
                results.append(res)

                if len(results) >= top_k:
                    break

            return results
        except Exception as e:
            logger.warning("Retrieval error for query '%s': %s", query[:50], e)
            return []

    def compute_relevance(self, query: str, context: str) -> float:
        """Calculates TF-IDF cosine relevance between two texts."""
        if not query.strip() or not context.strip() or self.vectorizer is None:
            return 0.0
        try:
            vecs = self.vectorizer.transform([query, context])
            sim = cosine_similarity(vecs[0:1], vecs[1:2])[0][0]
            return float(sim)
        except Exception:
            return 0.0
