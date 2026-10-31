# ResearchMate AI — Intelligent Multi-Agent Research Assistant

## Abstract

ResearchMate AI is a web-based academic research assistant that combines generative AI, retrieval-augmented generation, semantic search, and coordinated specialist agents. It supports academic paper discovery, PDF analysis, source-grounded question answering, comparative analysis, research-gap exploration, and report generation. Paper metadata and uploaded document passages are stored in a shared research library. The RAG workflow retrieves page-aware evidence and presents citations so users can inspect the source behind an answer. A citation critic checks citation identifiers and, when Gemini is configured, reviews whether claims are supported by the cited passages. The system is intended to make literature review more efficient while keeping evidence and limitations visible.

## 1. Introduction

Academic and technical research is spread across papers, repositories, and reports. Researchers often spend substantial time finding relevant work, extracting comparable details, and tracing claims back to original sources. General-purpose chatbots can produce fluent answers without reliable source grounding. ResearchMate AI addresses these challenges with an integrated workspace for paper discovery and evidence-based synthesis.

## 2. Problem statement

Researchers lack a single accessible tool that can discover academic literature, analyze uploaded papers, answer questions using the selected source collection, compare methods and results, explore research gaps, and generate a structured report with traceable references. Unverified AI-generated claims and fabricated bibliographic details can undermine trust in automated research assistance.

## 3. Objectives

- Retrieve real academic-paper metadata from Semantic Scholar and arXiv.
- Analyze uploaded research PDFs while retaining document and page references.
- Retrieve relevant passages and answer questions using only the selected evidence.
- Coordinate planning, retrieval, synthesis, and citation review as separate workflow stages.
- Compare paper metadata and abstracts, while marking unavailable details rather than inferring them.
- Identify possible research directions and distinguish observed limitations from hypotheses.
- Generate editable academic-style reports with PDF and DOCX export.

## 4. System modules

1. **Research Discovery:** searches Crossref and arXiv by default, with Semantic Scholar available as an optional source; it filters by year and saves records in the shared library.
2. **Document Analysis:** extracts page text from PDFs, detects common section labels, creates overlapping chunks, and produces structured summaries when the LLM is available.
3. **AI Research Assistant:** plans a question, retrieves relevant passages, generates a grounded answer, and displays source/page evidence.
4. **Comparative Analysis:** compares selected paper records and abstracts across objectives, methods, datasets, metrics, findings, and limitations.
5. **Research Gap Identification:** reports recurring themes and explicitly reported limitations, then proposes potential directions as hypotheses requiring further review.
6. **Report Generation:** drafts an editable research brief and exports it as DOCX or PDF.

## 5. Multi-agent workflow

```text
Research question
      ↓
Research Planner Agent
      ↓
Evidence Retrieval Agent (semantic + lexical search)
      ↓
Analysis / Synthesis Agent (Gemini, grounded in retrieved passages)
      ↓
Citation Verification Agent (valid IDs; semantic support review when Gemini is configured)
      ↓
Answer with document names, page references, caveats, and evidence gaps
```

LangGraph coordinates the planner, retrieval, synthesis, and critic nodes through shared workflow state. A sequential fallback keeps the evidence workflow usable if LangGraph is unavailable. Each retrieved passage carries a source document, page number, section label, and relevance score. The system does not claim that citation checks guarantee truth; users can open the source evidence and review it themselves.

## 6. Technical stack

| Component | Technology |
|---|---|
| User interface | Streamlit |
| Application language | Python |
| LLM | Google Gemini API (optional, configured with environment variable) |
| Agent orchestration | LangGraph |
| Text splitting / RAG utilities | LangChain text splitters |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) |
| Vector database | ChromaDB |
| Academic discovery | Crossref REST API, arXiv API, and optional Semantic Scholar API |
| PDF extraction | PyMuPDF |
| Tabular display | Pandas |
| Report export | python-docx and ReportLab |
| Persistence | SQLite |
| Configuration | python-dotenv |

## 7. Data flow

1. A user searches academic indexes and saves selected paper records. Crossref is the default DOI metadata fallback when Semantic Scholar is rate-limited.
2. PDFs are uploaded and extracted into page-specific text.
3. Text is divided into overlapping chunks and stored in SQLite; embeddings are written to ChromaDB when available.
4. A research question is planned and used to retrieve relevant passages from the chosen document collection.
5. The synthesis agent drafts an answer using retrieved passages and passage identifiers.
6. The citation critic checks identifiers and, with Gemini configured, audits claim support against evidence.
7. The UI displays the answer, references, and caveats. Reports can be edited and exported.

## 8. Evaluation plan

Evaluate the prototype on a curated collection of 10–20 papers and 8–12 questions with manually identified evidence passages.

- **Retrieval hit rate@5:** questions with at least one relevant passage among the top five results.
- **Citation coverage:** factual answer claims that include a passage reference.
- **Citation support rate:** sampled cited claims judged supported by their passages through manual review.
- **Comparison coverage:** whether the tool reports missing abstract information rather than guessing.
- **Task time:** time needed to assemble a cited brief compared with manual review of the same small collection.

Report actual observed results only after running the evaluation; the application does not claim universal accuracy or completeness.

## 9. Responsible use and limitations

Search APIs may rate-limit or return incomplete metadata. PDF extraction can fail on scanned documents. Retrieval can miss relevant passages, and generated analysis can still be wrong. Abstract-based comparisons are limited to the information available in abstracts. Suggested gaps are not proof of novelty. Users should inspect original sources, verify all references, and follow their institution’s academic-integrity requirements. This prototype is a research aid, not professional medical, legal, or financial advice.

## 10. Future enhancements

- Add structured database migrations, user accounts, and project-level workspaces.
- Add more scholarly repositories and citation graph exploration.
- Improve metadata extraction and support scanned PDFs with OCR.
- Add benchmark datasets and a reviewed human feedback loop for retrieval quality.
- Provide multilingual indexing and collaborative source annotations.

## 11. Running the application

See [README.md](README.md) for dependency installation, `.env` configuration, and the local run command. In brief: install requirements, set `GEMINI_API_KEY` in `.env`, and run `streamlit run app.py`.
