# MY_ISSB_Evaluator

> **Defensible Multi-Tier RAG & Behavioral Interview Evaluation System for Pakistan Inter Services Selection Board (ISSB) Preparation**

---

## 🎖️ Architecture Overview

The system strictly adheres to the principle that **Question Bank ≠ RAG Knowledge Base**:
- **Question Bank (`question_bank/`)**: 47 Structured JSON questions controlling *what* the interviewer asks across 13 calibrated progression blueprints (Biographical/Rapport → Academics → Communication → Motivation → Teamwork → Leadership → Confidence → Stress → Responsibility → Situational → Decision Making → General Awareness).
- **RAG Knowledge Base (`knowledge_base/`)**: Multi-tiered repository with strict source provenance controlling *what benchmarks and criteria* are retrieved to evaluate responses.
- **Controlled Flow**:
  $$\text{Question Bank} \xrightarrow{\text{Retrieve Target Q}} \text{LLM / Orchestrator} \xrightarrow{\text{Ask Naturally}} \text{Candidate Answer} \xrightarrow{\text{Probing Follow-up}} \text{RAG Evaluation Rubric} \xrightarrow{\text{Python Engine}} \text{15-Section Performance Report}$$

```
MY_ISSB_Evaluator
│
├── frontend/                       # Modern Lovable-Style Web UI (React 18 + Vite + Tailwind CSS)
│   ├── src/components/
│   │   ├── Navbar.tsx              # Tactical header with insignia & LLM status badge
│   │   ├── InterviewRoom.tsx       # Live interrogation room with animated follow-up probe cards
│   │   ├── EvaluationReport.tsx    # 15-section report with radar chart & evidence table
│   │   ├── RadarChart.tsx          # High-fidelity SVG Polar Radar Assessment
│   │   ├── RagExplorer.tsx         # Multi-tier RAG search with provenance filters
│   │   ├── QuestionBankExplorer.tsx# 13-category question browser
│   │   └── SettingsModal.tsx       # Live LLM provider configuration & connectivity test
│   └── package.json
│
├── backend/                        # FastAPI REST API Backend
│   ├── api.py                      # REST endpoints for interview, RAG, questions, settings
│   └── __init__.py
│
├── question_bank/                  # 47 Structured Questions across 13 Categories (JSON)
│   ├── personal.json, education.json, family.json, motivation.json
│   ├── leadership.json, decision_making.json, stress.json, situational.json
│   ├── general_knowledge.json, teamwork.json, communication.json
│   ├── confidence.json, responsibility.json
│
├── knowledge_base/                 # Multi-Tier Grounded Knowledge Base
│   ├── official/                   # Level 1: Official ISSB Selection System & Guidelines
│   ├── academic/                   # Level 2: Peer-Reviewed Leadership & Stress Literature
│   ├── evaluation/                 # Level 3: Observable Indicators Rubrics
│   ├── preparation/                # Level 3: Prep Guidance & Practical Tips
│   └── current_affairs/            # Level 4: Dated Pakistan Economy, Defense & Geopolitics
│
├── prompts/                        # Isolated Markdown Prompt Templates
│   ├── interviewer.md              # Interviewer persona template
│   ├── follow_up.md                # Targeted probing follow-up template
│   └── evaluator.md                # Senior assessor rubric evaluation template
│
├── src/
│   ├── question_bank/              # Loader, schema validator & sequence builder
│   ├── rag/                        # Document chunker & metadata-filtered retriever
│   ├── evaluator/                  # Observable indicators rubric engine & scoring
│   ├── interview/                  # State machine & conversational orchestrator
│   ├── llm/                        # Multi-provider adapter (Gemini, Groq, Ollama, OpenAI)
│   └── prompts/                    # Template loader with fallback resilience
│
├── tests/                          # 30 comprehensive automated tests (100% passing)
├── app.py                          # Streamlit interactive application
├── cli.py                          # Terminal CLI interactive practice
├── run_web.bat / run_web.ps1       # One-click launcher for FastAPI + Lovable React UI
└── requirements.txt
```

---

## 🛡️ Defensible Evaluation & Ethical Guardrails

1. **No False Probabilities**: The system outputs a **Practice Performance Score (0–100%)** and performance bands. It explicitly rejects false claims like *"73% chance of passing ISSB"*.
2. **Observable Indicators**: Inferences are grounded strictly in observable indicators (e.g. directness, structured reasoning, personal accountability, collaborative language) rather than ungrounded trait attribution.
3. **Strict Citation Transparency**:
   - Quotes from Level 1 are marked: `According to official ISSB guidelines...`
   - Inferences from Level 2/3 are marked: `Based on the project's behavioral evaluation rubric...`
4. **Official Board Caveat**: The final recommendation at ISSB is made collectively by the Board Conference at official centres. This system is framed as formative practice coaching.

---

## 🚀 Running the Application

### Option 1: Modern Lovable Web UI (FastAPI + React 18) [Recommended]
Run the unified launcher:
```powershell
.\run_web.ps1
# or double-click run_web.bat
```
- **Backend API**: `http://localhost:8000/docs`
- **Frontend UI**: `http://localhost:5173`

### Option 2: Streamlit Interactive App
```powershell
python -m streamlit run app.py
```

### Option 3: Terminal CLI
```powershell
python cli.py
```

### Option 4: Run Automated Tests
```powershell
python -m pytest tests/ -v
```
*(All 30 tests pass in ~4 seconds)*

---

## 🎯 Evaluative Personas

- **Deputy President Dimension**: Conducts an in-depth dialogue evaluating cognitive agility, presence of mind, social adjustment, moral integrity, and current affairs awareness.
- **Psychologist Dimension**: Explores deep career motivation, self-concept, subconscious reactions, and emotional regulation under pressure.
