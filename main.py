import os
import io
import re
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from researchmate.config import get_env_var
from researchmate.db import (
    init_db,
    list_papers,
    save_paper,
    delete_paper,
    list_documents,
    add_document,
    add_chunks,
    delete_document,
    save_document_summary,
    all_chunks,
    save_report
)
from researchmate.search import search_papers
from researchmate.ingest import extract_pdf, split_chunks, metadata_from_pdf
from researchmate.ai import (
    llm,
    structured_analysis,
    make_report
)
from researchmate.agents import run_research_graph

# Initialize database schema on startup
init_db()

app = FastAPI(
    title="ResearchMate AI API",
    description="Backend API for ResearchMate AI academic research platform",
    version="1.0.0"
)

# Enable CORS for local development and Vercel deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pydantic Request Models
# ---------------------------------------------------------------------------
class PaperModel(BaseModel):
    id: str
    title: str
    authors: Optional[str] = ""
    abstract: Optional[str] = ""
    year: Optional[int] = None
    doi: Optional[str] = ""
    url: Optional[str] = ""
    source: Optional[str] = ""

class SearchRequest(BaseModel):
    query: str
    sources: List[str] = ["Crossref", "arXiv"]
    limit: int = 10
    from_year: Optional[int] = None
    to_year: Optional[int] = None

class AskRequest(BaseModel):
    question: str
    document_ids: Optional[List[int]] = None

class CompareRequest(BaseModel):
    paper_ids: List[str]

class DraftReportRequest(BaseModel):
    topic: str
    last_answer: Optional[str] = None
    comparison: Optional[str] = None
    gaps: Optional[str] = None

class SaveReportRequest(BaseModel):
    title: str
    body: str

class ExportRequest(BaseModel):
    body: str
    title: Optional[str] = "Research Report"

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------
@app.get("/api/status")
def get_status():
    papers = list_papers()
    docs = list_documents()
    active_key = get_env_var("GEMINI_API_KEY")
    active_model = get_env_var("GEMINI_MODEL", "gemini-2.5-flash")
    return {
        "saved_papers_count": len(papers),
        "indexed_documents_count": len(docs),
        "gemini_connected": bool(active_key),
        "active_model": active_model,
        "database": "SQLite + ChromaDB"
    }

@app.get("/api/papers")
def get_papers():
    return list_papers()

@app.post("/api/papers")
def create_paper(paper: PaperModel):
    save_paper(paper.dict())
    return {"success": True, "paper": paper}

@app.delete("/api/papers/{paper_id}")
def remove_paper(paper_id: str):
    delete_paper(paper_id)
    return {"success": True}

@app.post("/api/search")
def search_academic_papers(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    y1 = req.from_year if (req.from_year and req.from_year > 0) else None
    y2 = req.to_year if (req.to_year and req.to_year > 0) else None
    
    results, errors = search_papers(
        req.query,
        req.sources,
        req.limit,
        y1,
        y2
    )
    return {"results": results, "errors": errors}

@app.get("/api/documents")
def get_documents():
    return list_documents()

@app.post("/api/documents/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    paper_id: Optional[str] = Form(None)
):
    notes = []
    pid = None if (not paper_id or paper_id == "None") else paper_id

    for f in files:
        try:
            content = await f.read()
            pages = extract_pdf(f.filename, content)
            text = "\n\n".join(x["text"] for x in pages)
            if not text.strip():
                raise ValueError("No selectable text found; this may be a scanned PDF.")
            
            meta = metadata_from_pdf(f.filename, pages)
            did = add_document(f.filename, text, pid)
            add_chunks(did, split_chunks(pages))
            
            extracted = "\n".join(f"[p. {p['page']}] {p['text']}" for p in pages[:16])[:24000]
            prompt = f'''Analyze this academic paper text for a research dashboard. Return fields: Abstract/aim, research objective, methodology/algorithms, datasets, evaluation metrics and results, limitations. Use only the supplied text. For each item cite page number as (p. N). Write "Not found in extracted text" when absent. Do not infer.\n\n{extracted}'''
            
            summary = llm(prompt)
            if summary is None:
                summary_note = "Document extracted and indexed. Gemini API key is not configured. Add GEMINI_API_KEY to environment variables."
            elif summary.startswith("__ERROR__"):
                summary_note = "Document extracted and indexed, but Gemini summary failed: " + summary.replace("__ERROR__", "", 1).strip()
            else:
                summary_note = summary
                save_document_summary(did, summary)

            notes.append({
                "name": f.filename,
                "meta": meta,
                "summary": summary_note,
                "document_id": did,
                "error": False
            })
        except Exception as e:
            notes.append({
                "name": f.filename,
                "meta": None,
                "summary": f"Could not analyze file: {str(e)}",
                "document_id": None,
                "error": True
            })

    return {"notes": notes, "documents": list_documents()}

@app.post("/api/documents/{doc_id}/summarize")
def summarize_document(doc_id: int):
    docs = {d["id"]: d for d in list_documents()}
    if doc_id not in docs:
        raise HTTPException(status_code=404, detail="Document not found")
    
    active_api_key = get_env_var("GEMINI_API_KEY")
    if not active_api_key:
        raise HTTPException(status_code=400, detail="Gemini API key is not configured.")

    page_chunks = all_chunks([doc_id])
    extracted = "\n".join(f"[p. {x['page']}] {x['text']}" for x in page_chunks)[:24000]
    if not extracted:
        extracted = docs[doc_id].get("text", "")[:24000]

    prompt = f'''Analyze this academic paper text for a research dashboard. Return fields: Abstract/aim, research objective, methodology/algorithms, datasets, evaluation metrics and results, limitations. Use only the supplied text. For each item cite page number when present. Write "Not found in extracted text" when absent. Do not infer.\n\n{extracted}'''
    
    result = llm(prompt)
    if not result or result.startswith("__ERROR__"):
        err = result.replace("__ERROR__", "").strip() if result else "Unknown Gemini error"
        raise HTTPException(status_code=500, detail=f"Gemini request failed: {err}")
    
    save_document_summary(doc_id, result)
    return {"success": True, "summary": result}

@app.delete("/api/documents/{doc_id}")
def remove_document(doc_id: int):
    delete_document(doc_id)
    return {"success": True}

@app.post("/api/assistant/ask")
def ask_assistant(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    result = run_research_graph(req.question, req.document_ids)
    return result

@app.post("/api/analysis/compare")
def compare_papers(req: CompareRequest):
    papers = list_papers()
    paper_map = {p["id"]: p for p in papers}
    chosen = [paper_map[pid] for pid in req.paper_ids if pid in paper_map]
    
    if len(chosen) < 2:
        raise HTTPException(status_code=400, detail="Please select at least 2 papers to compare.")
    
    comp = structured_analysis(
        chosen,
        "Compare research objectives, methods/algorithms, datasets, metrics, findings, and limitations. Give a concise table-like structured report. Do not fill gaps with assumptions."
    )
    return {"comparison": comp, "papers": chosen}

@app.post("/api/analysis/gaps")
def identify_gaps():
    papers = list_papers()
    if not papers:
        raise HTTPException(status_code=400, detail="No papers in library. Save papers first.")
    
    gaps = structured_analysis(
        papers,
        "Identify recurring methods and datasets, limitations explicitly reported in the abstracts, and possible underexplored directions. Structure each item as: observation, evidence [P#], confidence/coverage, and follow-up search needed. Separate direct evidence from hypotheses. Do not claim novelty."
    )
    return {"gaps": gaps, "papers_count": len(papers)}

@app.post("/api/report/draft")
def draft_report(req: DraftReportRequest):
    papers = list_papers()
    if not papers:
        raise HTTPException(status_code=400, detail="No papers in library to draft report from.")
    
    body = make_report(
        req.topic or "Research overview",
        papers,
        req.last_answer,
        req.comparison,
        req.gaps
    )
    return {"report": body}

@app.post("/api/report/save")
def store_report(req: SaveReportRequest):
    save_report(req.title or "Research report", req.body)
    return {"success": True}

@app.post("/api/report/export/docx")
def export_docx(req: ExportRequest):
    try:
        from docx import Document
        doc = Document()
        for line in req.body.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("# "):
                doc.add_heading(line[2:], 0)
            elif line.startswith("## "):
                doc.add_heading(line[3:], 1)
            elif line.startswith("### "):
                doc.add_heading(line[4:], 2)
            elif line.startswith("- "):
                doc.add_paragraph(line[2:], style="List Bullet")
            else:
                doc.add_paragraph(re.sub(r"\*\*(.*?)\*\*", r"\1", line))
        
        docx_buffer = io.BytesIO()
        doc.save(docx_buffer)
        docx_buffer.seek(0)
        return Response(
            content=docx_buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": "attachment; filename=researchmate_report.docx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DOCX export error: {e}")

@app.post("/api/report/export/pdf")
def export_pdf(req: ExportRequest):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        
        pdf = io.BytesIO()
        story = []
        styles = getSampleStyleSheet()
        for line in req.body.splitlines():
            if not line.strip():
                story.append(Spacer(1, 6))
                continue
            style = styles["Title"] if line.startswith("# ") else styles["Heading2"] if line.startswith("## ") else styles["BodyText"]
            txt = line.lstrip("# ").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("**", "")
            story.append(Paragraph(txt, style))
            story.append(Spacer(1, 4))
        
        SimpleDocTemplate(pdf, pagesize=letter, title=req.title or "Research report").build(story)
        pdf.seek(0)
        return Response(
            content=pdf.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=researchmate_report.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF export error: {e}")

# ---------------------------------------------------------------------------
# Serve Built React Frontend if dist exists
# ---------------------------------------------------------------------------
frontend_dist = Path(__file__).resolve().parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
