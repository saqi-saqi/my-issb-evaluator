# Comprehensive System Dossier: Knowledge Base & RAG Implementation (V2 Architecture)
**Project**: MY_ISSB_Evaluator — Multi-Tier True Hybrid RAG & Evidence-Grounded Behavioral Assessment System  
**Version**: 2.0.0 (Defensible Evidence-First Architecture)

---

## 📋 Executive Summary

The **MY_ISSB_Evaluator** is an AI-assisted behavioral interview simulation and evaluation system designed for candidates preparing for the **Pakistan Inter Services Selection Board (ISSB)**. 

To prevent hallucinations, ensure strict source provenance, and eliminate the risk of ungrounded candidate claims, the system enforces a strict architectural boundary:
$$\mathbf{\text{Question Bank}} \neq \mathbf{\text{RAG Knowledge Base}}$$

- **Question Bank (`question_bank/`)**: 47 Structured JSON items controlling *what* the interviewer asks across 13 calibrated progression categories (Biographical $\to$ Academic $\to$ Situational $\to$ Strategic).
- **RAG Knowledge Base (`knowledge_base/`)**: A 5-tier grounded repository with explicit YAML frontmatter metadata controlling *what benchmarks, behavioral indicators, and official standards* are retrieved to evaluate candidate responses.
- **True Hybrid Retrieval Pipeline**: Dual-channel Dense Semantic Embeddings + Sparse Sublinear TF-IDF bi-grams fused via **Reciprocal Rank Fusion (RRF)**, Cross-Encoder Lexical-Semantic Reranking, True Jaccard Deduplication ($|A \cap B| / |A \cup B|$), and **Abstention on Insufficient Evidence (Zero False Grounding)**.
- **3-Tier Scoring & 14-OLQ Layer**: Evidence Score $\to$ 14 Officer Like Qualities (OLQ) Layer $\to$ 5 Derived Executive Dashboard Dimensions.
- **Answer Adequacy over Length**: Evaluates Relevance, Completeness, Specificity, Evidence, Reasoning, Ownership, and Clarity without arbitrary length penalties. Short answers with direct ownership are evaluated positively.
- **Claim-Level Evidence Grounding**: Every substantive conclusion traces:
  $$\text{Feedback} \longrightarrow \text{Claim} \longrightarrow \text{Evidence ID} \longrightarrow \text{Transcript Excerpt} \longrightarrow \text{Rubric ID} \longrightarrow \text{Source ID}$$

---

## 🏛️ System Architecture: True Hybrid RAG & Evidence-First Flow

```mermaid
graph TD
    subgraph Candidate Interaction
        QB[Question Bank: 47 Questions] -->|Pulls Target Q| INT[Interviewer / Follow-up Agent]
        INT -->|Direct Interview Prompt| CAND[Candidate Response]
    end

    subgraph True Hybrid Retrieval Pipeline
        KB[5-Tier Knowledge Base with YAML Frontmatter] --> DL[KnowledgeBaseLoader & Chunker]
        DL --> SP_IDX[Sparse TF-IDF Bi-Gram Index]
        DL --> DN_IDX[Dense Semantic Vector Space / ChromaDB]
        
        CAND -->|Enriched Query + Intent| RET[KnowledgeRetriever Engine]
        SP_IDX -->|Sparse Scores| RRF[Reciprocal Rank Fusion RRF]
        DN_IDX -->|Dense Similarities| RRF
        RET --> RRF
        RRF --> RERANK[Cross-Encoder Lexical-Semantic Reranker]
        RERANK --> JACCARD[True Jaccard Deduplication |A∩B| / |A∪B|]
        JACCARD --> ABSTAIN{Relevance & Term Coverage Filter}
        ABSTAIN -->|Insufficient Evidence| ABST_OUT[Abstain: context_status: INSUFFICIENT_EVIDENCE]
        ABSTAIN -->|Pass Threshold| RAG_OUT[Ranked Chunks with Claim-Level Source IDs]
    end

    subgraph Defensible 3-Tier Scoring Engine
        CAND --> EVAL[Rubric Evaluation Engine]
        RAG_OUT --> EVAL
        EVAL -->|Pass 1: Answer Adequacy| TIER1[Tier 1: Per-Answer Evidence & Confidence HIGH/MED/LOW/NONE]
        TIER1 -->|Pass 2: 14 OLQ Aggregation| TIER2[Tier 2: 14 Officer Like Qualities Layer]
        TIER2 -->|Pass 3: Matrix Mapping| TIER3[Tier 3: 5 Derived Dashboard Dimensions]
        TIER3 -->|Pass 4: Qualitative Synthesis| REP[15-Section Report with Claim-Level Provenance Tree]
    end
```

---

## 📚 Multi-Tier Knowledge Base Inventory & Taxonomy

All documents feature **explicit YAML frontmatter metadata** eliminating brittle keyword guessing:

```yaml
---
source_type: official | academic | evaluation | preparation | current_affairs
dimension: deputy_president | psychologist | gto | general_knowledge | general
topic: fourteen_olqs | emotional_regulation_stress | leadership | etc.
authority_level: 1 | 2 | 3 | 4
title: Document Canonical Title
---
```

### The 5 Knowledge Tiers

| Tier | Directory | Format | Authority Level | Content Focus | Primary Consumer |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **Tier 1: Official Standards** | `knowledge_base/official/` | `.txt` | **Level 1 (Highest)** | Official ISSB selection system, 14 Officer Like Qualities (OLQs), 4-day selection schedule, testing dimensions (Psychologist, GTO, Deputy President). | Official benchmarking, candidate guidelines, mandatory citation base. |
| **Tier 2: Academic & Scientific** | `knowledge_base/academic/` | `.md` | **Level 2** | Peer-reviewed military psychology, emotional regulation under stress (Gross, 2015), situational judgment theory, competency modeling. | Qualitative dimension evaluation, cognitive/affective behavioral reasoning. |
| **Tier 3: Evaluation Rubrics** | `knowledge_base/evaluation/` | `.md` | **Level 3** | 9 Behavioral rubrics detailing observable positive indicators vs. observable potential weaknesses. | Per-answer evidence extraction, anti-gaming detection, rubric scoring. |
| **Tier 4: Preparation Guidance** | `knowledge_base/preparation/` | `.txt` | **Level 3** | Practical dos & don'ts, interview etiquette, STAR technique guidance, authenticity coaching. | Actionable feedback, preparation recommendations generation. |
| **Tier 5: Current Affairs Dossiers** | `knowledge_base/current_affairs/` | `.json` | **Level 4** | Structured dossiers on Pakistan Defense, Economy, Geography/Water Disputes, and International Geopolitics. Mapped to `general_knowledge`. | General awareness scoring, factual alignment verification. |

---

## 🎖️ The 14 Officer Like Qualities (OLQs) & 3-Tier Scoring

The system preserves the **14 OLQ layer internally**, then produces the 5-dimension executive dashboard as a mathematically derived view:

$$\begin{aligned}
\text{EvidenceScore}_{i} &= \text{Relevance} \times \text{Specificity} \times \text{EvidenceQuality} \\
\text{OLQScore}_{j} &= \frac{\sum \text{EvidenceScore}_i \times \text{Confidence}_i}{\sum \text{Confidence}_i} \\
\text{DimensionScore}_{k} &= \sum_j \text{MappingWeight}_{jk} \times \text{OLQScore}_j
\end{aligned}$$

### Deterministic Mapping Matrix

```
14 Officer Like Qualities (Internal Layer)               5 Dashboard Dimensions
--------------------------------------------------       ---------------------------------------
Reasoning Ability (40%) ─────────────────────────┐
Organizing Ability (30%) ────────────────────────┼───►   Intellect & Reasoning (25%)
Practical Common Sense (30%) ────────────────────┘

Emotional Stability (50%) ───────────────────────┐
Courage (25%) ───────────────────────────────────┼───►   Emotional Composure (20%)
Stamina (25%) ───────────────────────────────────┘

Social Adaptability (40%) ───────────────────────┐
Cooperation (40%) ───────────────────────────────┼───►   Social Adaptability & Teamwork (20%)
Initiative (20%) ────────────────────────────────┘

Power of Expression (60%) ───────────────────────┐
Self-Confidence (40%) ───────────────────────────┴───►   Communication & Expression (20%)

Integrity (40%) ─────────────────────────────────┐
Determination (30%) ─────────────────────────────┼───►   Motivation & Integrity (15%)
Sense of Responsibility (30%) ───────────────────┘
```

---

## 🔍 True Hybrid Retrieval Engine Specifications

### 1. Dual-Channel Search & Reciprocal Rank Fusion (RRF)
$$\text{RRF}(d) = \frac{w_{\text{sparse}}}{k + \text{rank}_{\text{sparse}}(d)} + \frac{w_{\text{dense}}}{k + \text{rank}_{\text{dense}}(d)} \quad (k=60, w_{\text{sparse}}=0.5, w_{\text{dense}}=0.5)$$

### 2. Candidate Relevance & Query Term Coverage Gating
To prevent false grounding, candidates must pass both relevance thresholding and minimum content term coverage:
$$\text{Coverage}(q, d) = \frac{|\text{ContentTerms}(q) \cap \text{Terms}(d)|}{|\text{ContentTerms}(q)|} \ge 0.25$$
If no documents meet this threshold, the retriever **abstains completely** (`[]`), preventing irrelevant official fallback.

### 3. Exact Jaccard Overlap Deduplication
$$\text{Jaccard}(A, B) = \frac{|A \cap B|}{|A \cup B|}$$
If $\text{Jaccard}(A, B) \ge 0.75$, the duplicate is pruned. The system retains the chunk with **higher authority level** (lower level number); if authorities are tied, it retains the chunk with the **higher similarity score**.

### 4. Cross-Encoder Lexical-Semantic Reranking
Top candidates receive reranking boosts based on exact phrase containment ($+20\%$), canonical title keyword overlap ($+15\%$), and topic alignment ($+10\%$).

---

## 🧪 Quantitative Verification & Benchmark Results

### 1. Automated Test Suites (100% Passing)
```powershell
python -m pytest tests/ -v
# 41 passed in ~8.5 seconds
```
- `test_api.py` (5/5 passed)
- `test_duplicate_prevention.py` (3/3 passed)
- `test_empty_retrieval.py` (3/3 passed — verifies zero-result abstention)
- `test_evaluator.py` (2/2 passed)
- `test_follow_up_generation.py` (2/2 passed)
- `test_fourteen_olqs.py` (3/3 passed — verifies 14 OLQ layer and substance scoring)
- `test_hybrid_rag.py` (3/3 passed — verifies dual RRF and Jaccard deduplication)
- `test_interview_flow.py` (2/2 passed)
- `test_malformed_llm_output.py` (3/3 passed)
- `test_question_bank.py` (4/4 passed)
- `test_rag.py` (3/3 passed)
- `test_rag_benchmark.py` (1/1 passed — quality gate verified)
- `test_structured_evaluation.py` (3/3 passed)
- `test_unresponsive_evaluation.py` (4/4 passed)

### 2. RAG Quality Benchmark (`python -m src.rag.benchmark`)
Evaluated across 30 gold-standard queries (26 in-domain + 4 adversarial out-of-domain queries):

| Metric | Target Gate | Measured Result | Status |
| :--- | :---: | :---: | :---: |
| **Recall@1** | $\ge 70.0\%$ | **92.31%** | ✅ PASS |
| **Recall@3** | $\ge 85.0\%$ | **92.31%** | ✅ PASS |
| **Recall@5** | $\ge 85.0\%$ | **92.31%** | ✅ PASS |
| **Mean Reciprocal Rank (MRR)** | $\ge 0.80$ | **0.9231** | ✅ PASS |
| **Precision@K** | $\ge 40.0\%$ | **57.88%** | ✅ PASS |
| **Citation Provenance Accuracy** | $\ge 85.0\%$ | **100.0%** | ✅ PASS |
| **Abstention on Out-of-Domain** | $\ge 90.0\%$ | **100.0%** | ✅ PASS |
| **Overall Benchmark Gate** | PASSED | **PASSED** | ✅ PASS |

---

## 📝 Evidence-First Evaluator Prompt (`prompts/evaluator.md`)

```markdown
# MY_ISSB_Evaluator — Evidence-First Evaluation Prompt

You are the evidence-grounded practice evaluator for MY_ISSB_Evaluator.
Your task is to evaluate a candidate's interview performance using ONLY:
1. The candidate transcript.
2. Retrieved knowledge-base evidence benchmarks.
3. The supplied evaluation rubric.
4. The supplied question metadata and evaluation intent.

You are NOT an official ISSB assessor.
Never predict, guarantee, estimate, or imply the probability that a candidate will be selected by ISSB.

## 1. PRIMARY PRINCIPLE
Every substantive conclusion must be traceable to observable evidence in the transcript.
Classify evidence as:
- DIRECT_EVIDENCE (direct explicit statements)
- REASONABLE_INFERENCE (grounded inference from multiple statements)
- INSUFFICIENT_EVIDENCE (no meaningful evidence)

Never convert INSUFFICIENT_EVIDENCE into a negative personality judgment.
Do not infer personality traits, clinical diagnoses, subconscious characteristics, or hidden motivations without explicit evidence.

## 2. SOURCE HIERARCHY & ATTRIBUTION
Respect the supplied source metadata:
- Official sources: Establish official-system facts when supported by the text.
- Academic sources: Provide theoretical or scientific context.
- Evaluation rubrics: Define this project's operational behavioral criteria.
- Preparation sources: Support coaching recommendations.
- Current-affairs sources: Support dated factual questions.

Your detailed feedback MUST explicitly include the phrase: '**According to official ISSB guidelines**' and '**Based on the project's behavioral evaluation rubric**'.
If no retrieved evidence supports a factual claim, return INSUFFICIENT_EVIDENCE. Do NOT use an unrelated fallback source.

## 3. EVIDENCE EXTRACTION & ANSWER QUALITY
Evaluate substance over length:
- A short answer is strong when it is direct, specific, and shows clear ownership or structured reasoning (e.g. "Yes, I accept full responsibility for the team's missed deadline").
- A long answer is weak when it is evasive, repetitive, contradictory, or off-topic.
- Score criteria: Relevance, Completeness, Specificity, Evidence, Reasoning, Ownership/Accountability, Consistency, Clarity.

## 4. CONTRADICTION & ABSTENTION DETECTION
- Compare candidate statements across the session for internal consistency.
- If contradictory statements exist, note them neutrally without immediately assuming dishonesty.
- If candidate or knowledge base provides insufficient evidence for an evaluative conclusion, register an abstention.

## 5. REQUIRED JSON SCHEMA
Return valid JSON only.

{
  "dimension": "{dimension}",
  "dimension_score": 75.0,
  "evidence_confidence": "HIGH|MEDIUM|LOW|NONE",
  "evidence": [
    {
      "evidence_id": "EV1",
      "transcript_excerpt": "...",
      "evidence_type": "DIRECT_EVIDENCE|REASONABLE_INFERENCE|INSUFFICIENT_EVIDENCE",
      "strength": 0.85
    }
  ],
  "positive_indicators_observed": ["Observable positive indicator 1"],
  "weaknesses_observed": ["Observable weakness 1"],
  "contradictions": [],
  "grounded_claims": [
    {
      "claim": "Demonstrated personal ownership for project setback.",
      "evidence_ids": ["EV1"],
      "source_ids": ["evaluation_leadership"],
      "support_level": "direct"
    }
  ],
  "detailed_feedback": "**According to official ISSB guidelines**, ... **Based on the project's behavioral evaluation rubric**, ...",
  "improvement_actions": [
    {
      "action": "...",
      "reason": "...",
      "evidence_ids": ["EV1"]
    }
  ],
  "abstentions": [],
  "disclaimer": "This is a practice evaluation generated from the supplied transcript, rubric, and knowledge-base evidence. It is not an official ISSB assessment or a prediction of selection."
}
```
