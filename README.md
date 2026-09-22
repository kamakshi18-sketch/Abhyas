# 🎯 Abhyas (अभ्यास) — AI Interviewer & Coach

**Abhyas** is a production-grade, stateful AI Interview Platform designed for realistic technical, behavioral (STAR), and HR interview simulation. Built with **Python 3.12+**, **Streamlit**, **SQLAlchemy**, **SQLite**, and **Pydantic**, Abhyas supports multi-provider LLM inference (**Google Gemini**, **NVIDIA Nemotron NIM**, **Local Ollama**, and **Offline Mock Simulation**).

---

## 🌟 Key Features

- **🎯 Advanced Interview Configuration (Phase 2)**:
  - Custom roles, experience levels (Fresher to 5+ Years), difficulty steering (Easy, Medium, Hard, Adaptive).
  - Multi-topic matrix selection (Python, System Design, SQL, Algorithms, Cloud, DevOps, etc.).
  - Specialized coaching personas (Professional, Friendly Coach, Rigorous FAANG, Technical Deep-Diver).
  - Multilingual interview support (English, Hindi, Spanish, French, German, Japanese, and more).

- **🧠 Dedicated Question Strategy & Generation Engine (Phase 3)**:
  - Pedagogy-aligned question sequence planner across 8 distinct question types: `Technical`, `Behavioral`, `HR`, `Situational`, `Conceptual`, `Problem Solving`, `Project`, and `Role Specific`.
  - Token-level anti-duplication filter and deterministic fallback heuristics.

- **📊 Dedicated Answer Evaluation Engine (Phase 4)**:
  - Type-specific rubric scoring:
    - **Technical**: Correctness, Concepts, Reasoning, Implementation.
    - **Behavioral**: STAR framework (Situation, Task, Action, Result), Ownership, Specificity.
    - **HR**: Relevance, Communication, Clarity, Completeness.
  - Textual grounding evidence extraction directly from candidate responses.
  - Transparent subjectivity disclaimers for pedagogical coaching.

- **🔌 Multi-Provider Support**:
  - **Google Gemini API** (`gemini-3.1-flash-lite`, `gemini-3.7-flash`, etc.)
  - **NVIDIA Nemotron NIM** (`nvidia/llama-3.1-nemotron-70b-instruct`)
  - **Local Ollama** (`qwen2.5:7b`, `nemotron-mini:latest`)
  - **Offline Simulation** (zero setup required)

---

## 🚀 Quick Start

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/kamakshi18-sketch/Abhyas.git
cd Abhyas
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and insert your preferred provider key:

```bash
cp .env.example .env
```

Example `.env`:
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite

DATABASE_URL=sqlite:///./data/interviews.db
LOG_LEVEL=INFO
```

*(You can also leave `.env` blank and configure your API key directly inside the Streamlit Setup UI!)*

### 3. Run Application

```bash
streamlit run main.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🧪 Testing

Run the automated test suite covering all services, schemas, and persistence:

```bash
pytest -v tests/
```

---

## 🛡️ Privacy & Security Note

- API keys and private environment variables must be stored exclusively in `.env` (ignored by git).
- Local session data and SQLite databases (`data/interviews.db`) are ignored by default.
