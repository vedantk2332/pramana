# Pramana — AI Programming Tutor & Evidence-Backed Debugger

> **Tagline:** *"Don't just trust the answer. See the proof."*  
> **Origin & Meaning:** *Pramana* (प्रमाण) is a classical Sanskrit philosophical term signifying **valid knowledge, proof, and reliable means of knowing**. In an era where AI models often hallucinate answers and beginners blindly copy untested code, Pramana is built on an unwavering principle: **transparent, evidence-grounded programming education**.

---

## 1. Project Overview

Pramana is a full-stack, AI-powered programming tutor, debugging assistant, and interactive learning platform. It empowers students to understand code line-by-line, diagnose bugs with root-cause analysis, verify code via safe server-side static checks, and hone their skills through interactive coding games.

### Core Distinguishing Pillars:
1. **Evidence Trail (Real RAG Pipeline):** Unlike standard chatbots that invent claims, Pramana retrieves actual passages from official documentation (PDF/TXT) using **FAISS vector search** and embeddings, displaying exact citations with similarity scores.
2. **Bug DNA Diagnosis:** Clearly separates the **visible symptom** (what crashed or printed) from the **underlying root cause** (the structural or algorithmic error).
3. **Fix Confidence Static Check:** Employs safe, server-side Python **AST (Abstract Syntax Tree) parsing** to validate syntax without executing arbitrary code. It reports honest statuses: `CHECKS PASSED`, `CHECKS FAILED`, or `NOT VERIFIED`.
4. **Learn Mode (Line-by-Line Comprehension):** Lets students click any line to inspect what it does, why it is needed, how it connects to surrounding lines, and what breaks if removed.
5. **Game Arena:** Three interactive game formats (*Fix The Bug*, *Find The Error*, *Explain The Code*) across Beginner, Intermediate, and Advanced tiers with live XP and local progress saving.

---

## 2. Technology Stack

- **Backend Framework:** Python 3.14 & Django 6.1
- **Vector Search Engine:** FAISS (`faiss-cpu`) with L2-normalized cosine inner product (`IndexFlatIP`)
- **Embeddings & LLM:** Google Gemini API (`gemini-3.8-flash` for reasoning; `gemini-embedding-001` / `gemini-embedding-2` for embeddings) via the modern `google-genai` SDK
- **Document Processing:** `pypdf` for PDF page text extraction & custom text chunking with metadata preservation
- **Code Safety & AST:** Python native `ast` module for zero-execution static tree inspection
- **Frontend:** HTML5, Vanilla CSS3 (custom dark navy theme), Bootstrap 5.3, Bootstrap Icons, and vanilla JavaScript (no complex build steps)

---

## 3. Project Structure

```
Pramana/
├── manage.py                          # Django management script
├── requirements.txt                   # Project dependencies
├── .env.example                       # Environment configuration template
├── .env                               # Local environment variables
├── .gitignore                         # Git exclusion rules
├── README.md                          # Comprehensive documentation
├── sample_docs/                       # Pre-made documentation ready for RAG indexing
│   ├── python_loops_and_indexing.txt  # Zero-based indexing, range(), slicing
│   ├── python_functions_and_scope.txt # Mutable defaults, LEGB scope rules
│   └── python_data_structures.txt     # KeyError, safe .get(), iteration mutation
├── data/
│   ├── uploads/                       # Uploaded documentation files
│   └── vector_store/                  # Persistent FAISS index & chunk metadata
├── pramana_core/                      # Django project configuration
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── pramana/                           # Core application package
    ├── services/
    │   ├── ai_service.py              # Learn Mode, Bug DNA & Evidence grounding
    │   ├── rag_service.py             # PDF/TXT extraction, chunking, FAISS index & search
    │   ├── verification_service.py    # Safe AST static analysis & delimiter checks
    │   └── game_data.py               # Game challenges repository & answer validation
    ├── templates/pramana/
    │   └── index.html                 # Main single-page application dashboard
    ├── static/pramana/
    │   ├── css/style.css              # Custom developer dark-theme stylesheet
    │   └── js/app.js                  # Frontend interactive controllers
    ├── views.py                       # REST API & template controllers
    ├── urls.py                        # App route declarations
    └── tests.py                       # Automated test suite (17 comprehensive tests)
```

---

## 4. Quick Start & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Pip package manager

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and add your Google Gemini API key:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
DEBUG=True
```
*(Note: If you run without an API key, static AST checks, diffing, game arena, and UI presets will still work fully, and Pramana will honestly notify you that AI reasoning requires a key).*

### Step 3: Run Database Migrations
```bash
python manage.py migrate
```

### Step 4: Run the Automated Test Suite
```bash
python manage.py test
```
*All 17 unit and integration tests will run and pass.*

### Step 5: Start the Development Server
```bash
python manage.py runserver
```
Visit **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser.

---

## 5. Application Walkthrough

### 1. Learn Mode (Line-by-Line Code Explainer)
- Paste any code or click one of the preset buttons (`Off-by-One`, `Mutable Default`, `Type Error`, `Slicing`).
- Click **"Explain Line-by-Line"**.
- Click individual code lines in the interactive viewer:
  - **What It Does:** Clear explanation for beginners.
  - **Why It's Needed:** Architectural necessity in the program.
  - **Surrounding Connection:** Links with prior and subsequent statements.
  - **If Removed or Changed:** Risk analysis and failure modes.
  - **Concepts:** Concept tags (loops, conditionals, functions).

### 2. Debug Mode (Bug DNA & Fix Confidence Check)
- Submit buggy code and an optional problem description.
- Click **"Run Bug DNA Analysis"**.
- Inspect the **Root Cause** vs. **Visible Symptom**.
- View the **Fix Confidence Static Check**:
  - `CHECKS PASSED`, `CHECKS FAILED`, or `NOT VERIFIED`.
  - Detailed breakdown of AST syntax trees and bracket balance.
  - Honest disclosure: clearly states that static checks validate syntax without claiming unverified runtime test passes.
- Side-by-side **Original vs. Corrected Code** diff.
- **Evidence Trail:** Grounded documentation passages with cosine similarity scores.

### 3. Game Arena (Interactive Coding Challenges)
- Switch between **Game A (Fix The Bug)**, **Game B (Find The Error)**, and **Game C (Explain The Code)**.
- Filter by difficulty: *Beginner*, *Intermediate*, *Advanced*.
- Submit answers for instant feedback, detailed explanations, and XP rewards.
- User progress, level, and XP persist in browser `localStorage`.

### 4. Evidence Docs (RAG Knowledge Management)
- Drag and drop PDF or TXT programming documentation into the dropzone.
- Automatic page extraction with `pypdf`, text chunking with overlap, vector embedding, and persistent storage in **FAISS**.
- Test semantic search live with custom queries.

---

## 6. Safety & Verification Guarantees

1. **Zero Execution of User Code:** Arbitrary user code is never executed on the server. Code validation is performed purely through Python's static `ast` parser.
2. **Honest Citations:** Pramana never invents citations, similarity scores, or document passages. If no matching documentation is found, it explicitly flags the response as relying on general AI reasoning.
3. **Clear Distinction of Claims:** Claims are categorized into *Documentation-Supported*, *General AI Suggestions*, and *Unverified Assumptions*.
