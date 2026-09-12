"""
Knowledge Base Document Loader & Chunker for MY_ISSB_Evaluator (V2 Architecture).
Extracts text with explicit multi-tier authority metadata (YAML frontmatter + JSON dossiers).
Supports header-based splitting and sliding-window chunking with configurable overlap.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    source_type: str  # 'official', 'academic', 'evaluation', 'preparation', 'current_affairs'
    dimension: str    # 'deputy_president', 'psychologist', 'gto', 'general_knowledge', 'general'
    topic: str        # 'leadership', 'communication', 'stress', 'fourteen_olqs', etc.
    title: str
    source_file: str
    authority_level: int  # 1 = highest (official), 2 = academic, 3 = prep/evaluation, 4 = current affairs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_type": self.source_type,
            "dimension": self.dimension,
            "topic": self.topic,
            "title": self.title,
            "source_file": self.source_file,
            "authority_level": self.authority_level,
        }


class KnowledgeBaseLoader:
    def __init__(
        self,
        base_dir: Optional[Path] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        min_chunk_length: int = 50,
        chunking_strategy: str = "header",
    ):
        """
        Args:
            base_dir: Root directory of the knowledge base.
            chunk_size: Maximum character length per chunk (used in sliding-window mode).
            chunk_overlap: Character overlap between consecutive chunks (sliding-window mode).
            min_chunk_length: Discard chunks shorter than this many characters.
            chunking_strategy: 'header' (split on ## headers) or 'sliding' (sliding window).
        """
        if base_dir is None:
            self.base_dir = Path(__file__).resolve().parent.parent.parent / "knowledge_base"
        else:
            self.base_dir = Path(base_dir)
        self.chunk_size = max(100, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, chunk_size // 2))
        self.min_chunk_length = max(20, min_chunk_length)
        self.chunking_strategy = chunking_strategy

    def _parse_frontmatter(self, raw_text: str) -> Tuple[Dict[str, Any], str]:
        """Extract YAML frontmatter key-value pairs and return remaining body text."""
        meta: Dict[str, Any] = {}
        body = raw_text.strip()
        if body.startswith("---"):
            parts = body.split("---", 2)
            if len(parts) >= 3:
                yaml_block = parts[1].strip()
                body = parts[2].strip()
                for line in yaml_block.splitlines():
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        k, v = line.split(":", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if v.isdigit():
                            meta[k] = int(v)
                        else:
                            meta[k] = v
        return meta, body

    def load_all_chunks(self) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        if not self.base_dir.exists():
            return chunks

        # 1. Official material (Level 1)
        official_dir = self.base_dir / "official"
        if official_dir.exists():
            for p in official_dir.glob("*.txt"):
                chunks.extend(self._process_file_with_frontmatter(p, default_source="official", default_auth=1))

        # 2. Academic research (Level 2)
        academic_dir = self.base_dir / "academic"
        if academic_dir.exists():
            for p in academic_dir.glob("*.md"):
                chunks.extend(self._process_file_with_frontmatter(p, default_source="academic", default_auth=2))

        # 3. Evaluation rubrics (Level 3 - Internal Standard)
        eval_dir = self.base_dir / "evaluation"
        if eval_dir.exists():
            for p in eval_dir.glob("*.md"):
                chunks.extend(self._process_file_with_frontmatter(p, default_source="evaluation", default_auth=3))

        # 4. Preparation material (Level 3 - Coaching guidance)
        prep_dir = self.base_dir / "preparation"
        if prep_dir.exists():
            for p in prep_dir.glob("*.txt"):
                chunks.extend(self._process_file_with_frontmatter(p, default_source="preparation", default_auth=3))

        # 5. Current affairs (Dated JSON dossiers)
        ca_dir = self.base_dir / "current_affairs"
        if ca_dir.exists():
            for p in ca_dir.glob("*.json"):
                chunks.extend(self._process_current_affairs_json(p))

        return chunks

    def _sliding_window_chunks(
        self, text: str, file_stem: str, source_type: str, dimension: str,
        file_topic: str, source_file: str, authority_level: int, parent_title: str,
    ) -> List[DocumentChunk]:
        """Split text into overlapping sliding-window chunks."""
        chunks: List[DocumentChunk] = []
        step = self.chunk_size - self.chunk_overlap
        if step <= 0:
            step = self.chunk_size

        idx = 0
        chunk_num = 0
        while idx < len(text):
            end = min(idx + self.chunk_size, len(text))
            segment = text[idx:end].strip()

            if len(segment) >= self.min_chunk_length:
                first_line = segment.splitlines()[0].lstrip("#").strip()[:80] if segment.splitlines() else parent_title
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{file_stem}_sw_{chunk_num}",
                        text=segment,
                        source_type=source_type,
                        dimension=dimension,
                        topic=file_topic,
                        title=first_line or parent_title,
                        source_file=source_file,
                        authority_level=authority_level,
                    )
                )
                chunk_num += 1

            idx += step
            if end >= len(text):
                break

        return chunks

    def _process_file_with_frontmatter(
        self, path: Path, default_source: str, default_auth: int
    ) -> List[DocumentChunk]:
        raw_text = path.read_text(encoding="utf-8")
        meta, body = self._parse_frontmatter(raw_text)

        source_type = str(meta.get("source_type", default_source))
        dimension = str(meta.get("dimension", "general"))
        topic = str(meta.get("topic", path.stem.replace("_", " ").lower()))
        authority_level = int(meta.get("authority_level", default_auth))
        file_title = str(meta.get("title", path.stem.replace("_", " ").title()))

        if self.chunking_strategy == "sliding":
            return self._sliding_window_chunks(
                text=body, file_stem=path.stem, source_type=source_type,
                dimension=dimension, file_topic=topic, source_file=path.name,
                authority_level=authority_level, parent_title=file_title,
            )

        # Default: header-based splitting
        sections = re.split(r"\n(?=##?\s+)", body)
        chunks: List[DocumentChunk] = []

        for idx, section in enumerate(sections):
            clean_text = section.strip()
            if len(clean_text) < self.min_chunk_length:
                continue

            first_line = clean_text.splitlines()[0].lstrip("#").strip()

            # If a single section is very large, apply sliding window within it
            if len(clean_text) > self.chunk_size * 2 and self.chunking_strategy == "header":
                sub_chunks = self._sliding_window_chunks(
                    text=clean_text, file_stem=f"{path.stem}_{idx}",
                    source_type=source_type, dimension=dimension,
                    file_topic=topic, source_file=path.name,
                    authority_level=authority_level, parent_title=first_line or file_title,
                )
                chunks.extend(sub_chunks)
            else:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{path.stem}_{idx}",
                        text=clean_text,
                        source_type=source_type,
                        dimension=dimension,
                        topic=topic,
                        title=first_line or file_title,
                        source_file=path.name,
                        authority_level=authority_level,
                    )
                )
        return chunks

    def _process_current_affairs_json(self, path: Path) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                category = data.get("category", path.stem)
                dimension = data.get("dimension", "general_knowledge")
                auth_level = data.get("authority_level", 4)
                topics = data.get("topics", [])
                for idx, t in enumerate(topics):
                    title = t.get("title", "")
                    summary = t.get("summary", "")
                    key_facts = "\n- ".join(t.get("key_facts", []))
                    date = t.get("date", "")
                    text = f"Title: {title}\nDate: {date}\nSummary: {summary}\nKey Facts:\n- {key_facts}"

                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"ca_{category}_{idx}",
                            text=text,
                            source_type="current_affairs",
                            dimension=dimension,
                            topic=category.replace("_", " "),
                            title=title,
                            source_file=path.name,
                            authority_level=auth_level,
                        )
                    )
        except Exception as e:
            print(f"Error reading {path}: {e}")
        return chunks
