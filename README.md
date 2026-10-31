# ResearchMate AI

An academic research workspace built with Streamlit, Gemini, LangGraph, LangChain-compatible RAG components, Sentence Transformers, ChromaDB, SQLite, Semantic Scholar, and arXiv.

## Features

- Search real paper records from Crossref and arXiv by default, with Semantic Scholar available as an optional source; filter by publication years, inspect DOI/source links, and save records to a shared SQLite library.
- Upload multiple PDFs, extract page text with PyMuPDF, detect common section labels, create overlapping chunks, and index them for retrieval.
- Ask questions against selected uploaded papers. The LangGraph workflow plans, retrieves, synthesizes, and runs a citation critic. With Gemini configured, the critic checks passage support; without it, citation IDs are checked and the interface says semantic review is unavailable. Passage references show document and page.
- Compare saved papers, identify potential gaps with explicit source labels, and draft editable reports for DOCX/PDF export.
- Runs without Gemini configured: search, storage, ingestion, and retrieval still work; the app shows retrieved evidence rather than pretending to have generated a synthesis.

## Requirements

- Python 3.10 or newer.
- Internet access for installation, academic search APIs, and Gemini calls.
- Optional Gemini API key for generated analysis. API keys are never hard-coded.

## Install and run (Windows PowerShell)

```powershell
cd ResearchMateAI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set `GEMINI_API_KEY` to your key. A Semantic Scholar API key is optional; unauthenticated requests can be rate-limited. Crossref and arXiv are enabled by default as alternate search sources. You may add `CROSSREF_EMAIL` in `.env` to identify requests to Crossref.

### Run with React Frontend & FastAPI Backend (Recommended)

1. Start the FastAPI backend:
```powershell
uvicorn main:app --reload --port 8000
```

2. In a separate terminal, start the React development server:
```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser. (The Vite dev server automatically proxies `/api` calls to FastAPI at `http://localhost:8000`).

Alternatively, build the React production bundle once (`cd frontend && npm run build`) and start `python main.py`—FastAPI will serve both the React app and all API routes directly at `http://localhost:8000`!

### Deployment: Render & Vercel

- **Render (Backend)**: Deploy as a Python Web Service.
  - Build Command: `pip install --upgrade pip && pip install -r requirements.txt`
  - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
  - Environment Variables: `GEMINI_API_KEY`, `PYTHON_VERSION=3.10.13`
- **Vercel (Frontend)**: Deploy the `frontend/` directory to Vercel.
  - Framework Preset: `Vite`
  - Output Directory: `dist`
  - Environment Variable: `VITE_API_BASE_URL` set to your Render backend URL (e.g. `https://your-service.onrender.com`).

## Suggested demo

1. In **Research Discovery**, search a topic such as “retrieval augmented generation evaluation” and save 3–5 papers.
2. In **Document Analysis**, upload PDFs for the saved papers. The system extracts page-aware chunks and displays structured summaries when Gemini is configured.
3. In **AI Research Assistant**, select the indexed documents and ask a question about methods, results, or limitations. Expand evidence cards to inspect passages and page numbers.
4. In **Comparative Analysis**, select multiple saved papers and compare the details available in their abstracts.
5. In **Research Gap Identification**, review observations and hypotheses, checking linked papers before making novelty claims.
6. In **Report Generation**, preview/edit the brief and download DOCX or PDF.

## Architecture

`app.py` provides the six-section Streamlit UI with a dark theme. `researchmate/search.py` calls Crossref, arXiv, and Semantic Scholar. Crossref results are cached in-process to reduce repeated requests; its public REST API does not require sign-up. `ingest.py` extracts and chunks PDF text. `db.py` manages the shared SQLite library. `ai.py` provides Gemini prompts, semantic retrieval, analysis, and report drafting. `agents.py` coordinates planner, retriever, synthesizer, and citation critic nodes with LangGraph; it has a sequential fallback if LangGraph is unavailable.

## Verification and limitations

- `python -m compileall -q app.py researchmate` checks Python syntax.
- `python -m streamlit run app.py` is the local smoke check after dependencies are installed.
- Search endpoints may rate-limit. If Semantic Scholar returns HTTP 429, its warning explains that other selected sources may still return results. Crossref and arXiv are selected by default; Crossref asks clients to cache repeated requests, identify requests with a `mailto` or agent value, and back off if response times increase.
- Semantic embeddings and Chroma are used when available. Retrieval falls back to lexical matching if model/vector components fail to initialize.
- Abstract-based comparisons can only report what is in available abstracts/metadata. Upload full papers for richer analysis.
- Citation IDs are checked against the evidence set, but users must inspect cited passages. The prototype is not a guarantee of factual accuracy or literature completeness.
- PDF export and DOCX export format the generated report; verify references and academic requirements before submission.
