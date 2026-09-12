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
│   │   ├── Navbar.tsx              # Tactical header with insignia & Groq status badge
│   │   ├── InterviewRoom.tsx       # Live interrogation room with animated follow-up probe cards
│   │   ├── EvaluationReport.tsx    # Consolidated 6-section report with radar chart & evidence table
│   │   ├── RadarChart.tsx          # High-fidelity SVG Polar Radar Assessment (14 OLQs)
│   │   ├── LearningPhaseCard.tsx   # Practice techniques, retry evaluation & before/after delta
│   │   ├── RagExplorer.tsx         # Multi-tier RAG search with provenance filters (Dev Tools)
│   │   ├── QuestionBankExplorer.tsx# 13-category question browser (Dev Tools)
│   │   └── SettingsModal.tsx       # Live Groq API key & model connectivity test
│   └── package.json
│
├── backend/                        # FastAPI REST API Backend
│   ├── main.py                     # Streamlined 7-endpoint REST API
│   ├── api.py                      # Re-export compatibility layer
│   └── __init__.py
│
├── core/                           # Consolidated Python AI & Evaluation Engine
│   ├── ai.py                       # High-speed Groq inference client (generate_text, generate_json)
│   ├── questions.py                # QuestionBank loader & calibrated sequence builder
│   ├── rag.py                      # Multi-tier TF-IDF retriever with provenance citations
│   ├── scoring.py                  # Deterministic 14-OLQ & 5-dimension scoring engine
│   ├── evaluator.py                # 2-Pass rubric evaluator (evidence extraction + single narrative LLM call)
│   ├── interview.py                # InterviewService state machine with adaptive probing triggers
│   └── learning.py                 # LearningService for coaching feedback & before/after retry deltas
│
├── question_bank/                  # Curated Question Bank
│   └── questions.json              # 47 Structured Questions across 13 Categories in a unified JSON array
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
├── tests/                          # Automated tests covering core engine, RAG, and API
├── run_web.bat / run_web.ps1       # One-click launcher for FastAPI + Lovable React UI
└── requirements.txt                # Streamlined production dependencies
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

## 🚀 Quick Start Guide (Run on Any Laptop)

### 📋 Prerequisites
- **Python**: 3.10, 3.11, or 3.12 installed ([python.org](https://www.python.org/downloads/))
- **Node.js**: v18+ or v20+ with npm installed ([nodejs.org](https://nodejs.org/))
- **Git**: Installed on your system

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/saqi-saqi/my-issb-evaluator.git
cd my-issb-evaluator
```

---

### Step 2: Setup Python Backend
Create and activate a virtual environment, then install requirements:

**Windows (PowerShell / Command Prompt):**
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### Step 3: Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

---

### Step 4 (Optional): Configure LLM API Key
The simulator works **completely out of the box in offline mode** without any API key.
To enable live, dynamic LLM inference:
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   # On Windows: copy .env.example .env
   ```
2. Open `.env` and paste your free Groq API key:
   ```env
   GROQ_API_KEY=gsk_your_key_here
   ```
   *(You can get a free, ultra-fast Groq key in 30 seconds at [console.groq.com](https://console.groq.com))*

---

### Step 5: Launch the Application

#### Option A: One-Click Launcher (Windows)
```powershell
.\run_web.ps1
# or simply double-click run_web.bat
```

#### Option B: Manual Launch (Windows, macOS, Linux)
Open two terminal windows in the project root:

- **Terminal 1 (FastAPI Backend)**:
  ```bash
  python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
  ```
- **Terminal 2 (Lovable React Frontend)**:
  ```bash
  cd frontend
  npm run dev
  ```

Open your browser at: **`http://localhost:5173`**
*(Backend Swagger API docs available at `http://localhost:8000/docs`)*

---

### Alternative Interfaces
- **Streamlit App**: `python -m streamlit run app.py`
- **Terminal CLI**: `python cli.py`
- **Run Tests**: `python -m pytest tests/ -v` (56 automated tests pass in ~35s)

---

## 🎯 Evaluative Personas

- **Deputy President Dimension**: Conducts an in-depth dialogue evaluating cognitive agility, presence of mind, social adjustment, moral integrity, and current affairs awareness.
- **Psychologist Dimension**: Explores deep career motivation, self-concept, subconscious reactions, and emotional regulation under pressure.
