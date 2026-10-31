import React, { useState, useEffect } from 'react';
import {
  fetchStatus,
  fetchPapers,
  savePaper,
  deletePaper,
  searchPapers,
  fetchDocuments,
  uploadDocuments,
  summarizeDocument,
  deleteDocument,
  askAssistant,
  comparePapers,
  identifyGaps,
  draftReport,
  saveReport,
  downloadDocx,
  downloadPdf
} from './api';

const NAV_OPTIONS = [
  { id: 'Hub', label: '🏠 Workspace Hub' },
  { id: 'Research Discovery', label: '🔍 Research Discovery' },
  { id: 'Document Analysis', label: '📄 Document Analysis' },
  { id: 'AI Research Assistant', label: '🤖 AI Research Assistant' },
  { id: 'Comparative Analysis', label: '⚖️ Comparative Analysis' },
  { id: 'Research Gap Identification', label: '🔬 Research Gap Identification' },
  { id: 'Report Generation', label: '📝 Report Generation' }
];

export default function App() {
  const [activeSection, setActiveSection] = useState('Hub');
  const [status, setStatus] = useState({
    saved_papers_count: 0,
    indexed_documents_count: 0,
    gemini_connected: false,
    active_model: 'gemini-2.5-flash',
    database: 'SQLite + ChromaDB'
  });
  const [papers, setPapers] = useState([]);
  const [docs, setDocs] = useState([]);
  const [libraryExpanded, setLibraryExpanded] = useState(false);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSources, setSelectedSources] = useState(['Crossref', 'arXiv']);
  const [fromYear, setFromYear] = useState('');
  const [toYear, setToYear] = useState('');
  const [searchLimit, setSearchLimit] = useState(10);
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [searchErrors, setSearchErrors] = useState([]);

  // Document Analysis state
  const [selectedPaperForUpload, setSelectedPaperForUpload] = useState('None');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadNotes, setUploadNotes] = useState([]);
  const [summarizingDocId, setSummarizingDocId] = useState(null);

  // Assistant state
  const [selectedDocIds, setSelectedDocIds] = useState([]);
  const [question, setQuestion] = useState('');
  const [isAnswering, setIsAnswering] = useState(false);
  const [lastAnswer, setLastAnswer] = useState(null);
  const [lastQuestion, setLastQuestion] = useState('');

  // Comparison state
  const [selectedComparePapers, setSelectedComparePapers] = useState([]);
  const [isComparing, setIsComparing] = useState(false);
  const [comparisonResult, setComparisonResult] = useState('');
  const [comparedPapersList, setComparedPapersList] = useState([]);

  // Gap Identification state
  const [isFindingGaps, setIsFindingGaps] = useState(false);
  const [gapsResult, setGapsResult] = useState('');

  // Report state
  const [reportTopic, setReportTopic] = useState('');
  const [isDraftingReport, setIsDraftingReport] = useState(false);
  const [reportText, setReportText] = useState('');
  const [reportSavedMsg, setReportSavedMsg] = useState('');

  // Initial load
  const loadInitialData = async () => {
    try {
      const [s, p, d] = await Promise.all([fetchStatus(), fetchPapers(), fetchDocuments()]);
      setStatus(s);
      setPapers(p);
      setDocs(d);
      if (d.length > 0 && selectedDocIds.length === 0) {
        setSelectedDocIds(d.map((x) => x.id));
      }
      if (p.length > 0 && selectedComparePapers.length === 0) {
        setSelectedComparePapers(p.slice(0, 4).map((x) => x.id));
      }
    } catch (err) {
      console.error('Error loading data:', err);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  // Update selected doc IDs when docs change
  useEffect(() => {
    if (docs.length > 0 && selectedDocIds.length === 0) {
      setSelectedDocIds(docs.map((d) => d.id));
    }
  }, [docs]);

  // Handle Paper Search
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    setSearchErrors([]);
    try {
      const data = await searchPapers(searchQuery, selectedSources, searchLimit, fromYear, toYear);
      setSearchResults(data.results || []);
      setSearchErrors(data.errors || []);
    } catch (err) {
      setSearchErrors([err.message]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSavePaper = async (paper) => {
    try {
      await savePaper(paper);
      const updated = await fetchPapers();
      setPapers(updated);
      const s = await fetchStatus();
      setStatus(s);
    } catch (err) {
      alert('Failed to save paper: ' + err.message);
    }
  };

  const handleDeletePaper = async (paperId) => {
    try {
      await deletePaper(paperId);
      const updated = await fetchPapers();
      setPapers(updated);
      const s = await fetchStatus();
      setStatus(s);
    } catch (err) {
      alert('Failed to delete paper: ' + err.message);
    }
  };

  // Handle PDF Upload
  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;
    setIsUploading(true);
    const formData = new FormData();
    for (const f of selectedFiles) {
      formData.append('files', f);
    }
    if (selectedPaperForUpload !== 'None') {
      formData.append('paper_id', selectedPaperForUpload);
    }

    try {
      const res = await uploadDocuments(formData);
      setUploadNotes(res.notes || []);
      setDocs(res.documents || []);
      const s = await fetchStatus();
      setStatus(s);
      setSelectedFiles([]);
    } catch (err) {
      alert('Upload failed: ' + err.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSummarizeDoc = async (docId) => {
    setSummarizingDocId(docId);
    try {
      const res = await summarizeDocument(docId);
      setDocs(docs.map((d) => (d.id === docId ? { ...d, summary: res.summary } : d)));
    } catch (err) {
      alert('Summarization failed: ' + err.message);
    } finally {
      setSummarizingDocId(null);
    }
  };

  const handleDeleteDoc = async (docId) => {
    try {
      await deleteDocument(docId);
      const updated = await fetchDocuments();
      setDocs(updated);
      const s = await fetchStatus();
      setStatus(s);
    } catch (err) {
      alert('Failed to delete document: ' + err.message);
    }
  };

  // Handle Assistant Question
  const handleAskQuestion = async () => {
    if (!question.trim()) return;
    setIsAnswering(true);
    try {
      const result = await askAssistant(question, selectedDocIds);
      setLastAnswer(result);
      setLastQuestion(question);
      if (!reportTopic) setReportTopic(question);
    } catch (err) {
      alert('Error from Assistant: ' + err.message);
    } finally {
      setIsAnswering(false);
    }
  };

  // Handle Compare
  const handleCompare = async () => {
    if (selectedComparePapers.length < 2) return;
    setIsComparing(true);
    try {
      const res = await comparePapers(selectedComparePapers);
      setComparisonResult(res.comparison);
      setComparedPapersList(res.papers);
    } catch (err) {
      alert('Comparison failed: ' + err.message);
    } finally {
      setIsComparing(false);
    }
  };

  // Handle Gaps
  const handleIdentifyGaps = async () => {
    setIsFindingGaps(true);
    try {
      const res = await identifyGaps();
      setGapsResult(res.gaps);
    } catch (err) {
      alert('Gap identification failed: ' + err.message);
    } finally {
      setIsFindingGaps(false);
    }
  };

  // Handle Draft Report
  const handleDraftReport = async () => {
    setIsDraftingReport(true);
    setReportSavedMsg('');
    try {
      const res = await draftReport(
        reportTopic || 'Research overview',
        lastAnswer?.answer || null,
        comparisonResult || null,
        gapsResult || null
      );
      setReportText(res.report);
    } catch (err) {
      alert('Failed to draft report: ' + err.message);
    } finally {
      setIsDraftingReport(false);
    }
  };

  const handleSaveReportToDb = async () => {
    try {
      await saveReport(reportTopic || 'Research Report', reportText);
      setReportSavedMsg('Report saved to SQLite database successfully!');
    } catch (err) {
      alert('Failed to save report: ' + err.message);
    }
  };

  return (
    <div className="app-layout">
      {/* Sidebar Utility Panel */}
      <aside className="sidebar">
        <div className="sidebar-title">
          <span>📚</span> ResearchMate AI
        </div>
        <div className="sidebar-caption">Interactive Multi-Agent Academic Workspace</div>

        <button
          className={`btn ${activeSection === 'Hub' ? 'btn-primary' : 'btn-secondary'} btn-block`}
          onClick={() => setActiveSection('Hub')}
        >
          🏠 Workspace Hub
        </button>

        <div className="sidebar-divider"></div>

        <div className="sidebar-metric">
          <div className="metric-label">Saved papers</div>
          <div className="metric-value">{papers.length}</div>
        </div>

        <div className="sidebar-metric">
          <div className="metric-label">Indexed documents</div>
          <div className="metric-value">{docs.length}</div>
        </div>

        <div className={`gemini-status ${status.gemini_connected ? '' : 'disconnected'}`}>
          {status.gemini_connected
            ? `Gemini: connected (${status.active_model})`
            : 'Gemini: add GEMINI_API_KEY in .env'}
        </div>

        <div className="sidebar-divider"></div>

        {/* Collapsible Saved Papers Library */}
        <div className="accordion">
          <div
            className="accordion-header"
            onClick={() => setLibraryExpanded(!libraryExpanded)}
          >
            <span>📚 Saved Papers Library</span>
            <span>{libraryExpanded ? '▾' : '▸'}</span>
          </div>
          {libraryExpanded && (
            <div className="accordion-body">
              {papers.length > 0 ? (
                papers.map((p) => (
                  <div key={p.id} style={{ marginBottom: '8px' }}>
                    • <strong>{p.title}</strong> ({p.year || 'n/a'})
                  </div>
                ))
              ) : (
                <div style={{ color: 'var(--text-muted)' }}>No papers saved yet.</div>
              )}
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-wrapper">
        {/* Hero Banner */}
        <div className="hero">
          <h1>ResearchMate AI</h1>
          <p>Discover, analyze, compare, and synthesize research with verifiable evidence and multi-agent AI.</p>
        </div>

        {/* Top Navigation Pills Bar */}
        <nav className="nav-pills-bar">
          {NAV_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              className={`nav-pill ${activeSection === opt.id ? 'active' : ''}`}
              onClick={() => setActiveSection(opt.id)}
            >
              {opt.label}
            </button>
          ))}
        </nav>

        {/* ========================================================================= */}
        {/* VIEW: WORKSPACE HUB */}
        {/* ========================================================================= */}
        {activeSection === 'Hub' && (
          <div>
            <div className="hub-header">
              <h2>Workspace Modules</h2>
              <p>Click any component below to launch the respective research stage:</p>
            </div>

            <div className="modules-grid">
              {/* Card 1 */}
              <div className="module-card">
                <div>
                  <h3>🔍 Research Discovery</h3>
                  <div className="module-category">ACADEMIC SEARCH & LIBRARY</div>
                  <p>Search academic papers across Crossref, arXiv, and Semantic Scholar with publication year filters. Save results directly into your library.</p>
                </div>
                <div>
                  <span className="module-badge">📚 {papers.length} saved papers</span>
                  <button
                    className="btn btn-primary btn-block"
                    onClick={() => setActiveSection('Research Discovery')}
                  >
                    Open Research Discovery →
                  </button>
                </div>
              </div>

              {/* Card 2 */}
              <div className="module-card">
                <div>
                  <h3>📄 Document Analysis</h3>
                  <div className="module-category">PDF INGESTION & AI SUMMARIES</div>
                  <p>Upload full-text PDF papers. Automatically extract page numbers, detect paper sections, build vector chunks, and generate structured summaries.</p>
                </div>
                <div>
                  <span className="module-badge">📑 {docs.length} indexed documents</span>
                  <button
                    className="btn btn-primary btn-block"
                    onClick={() => setActiveSection('Document Analysis')}
                  >
                    Open Document Analysis →
                  </button>
                </div>
              </div>

              {/* Card 3 */}
              <div className="module-card">
                <div>
                  <h3>🤖 AI Research Assistant</h3>
                  <div className="module-category">MULTI-AGENT GROUNDED RAG</div>
                  <p>Ask complex research questions. Runs a multi-agent workflow (Planner → Retrieval → Synthesis → Citation Critic) with page-level citations.</p>
                </div>
                <div>
                  <span className="module-badge">⚡ LangGraph Multi-Agent</span>
                  <button
                    className="btn btn-primary btn-block"
                    onClick={() => setActiveSection('AI Research Assistant')}
                  >
                    Open AI Assistant →
                  </button>
                </div>
              </div>

              {/* Card 4 */}
              <div className="module-card">
                <div>
                  <h3>⚖️ Comparative Analysis</h3>
                  <div className="module-category">CROSS-PAPER SYNTHESIS</div>
                  <p>Select 2 or more saved papers to compare side-by-side across objectives, algorithms, benchmarks, metrics, and reported limitations.</p>
                </div>
                <div>
                  <span className="module-badge">📊 Matrix Comparison</span>
                  <button
                    className="btn btn-primary btn-block"
                    onClick={() => setActiveSection('Comparative Analysis')}
                  >
                    Open Comparative Analysis →
                  </button>
                </div>
              </div>

              {/* Card 5 */}
              <div className="module-card">
                <div>
                  <h3>🔬 Research Gap Identification</h3>
                  <div className="module-category">HYPOTHESIS & LIMITATION DISCOVERY</div>
                  <p>Review recurring methods, explicitly acknowledged limitations, and uncover evidence-backed underexplored directions with source citations.</p>
                </div>
                <div>
                  <span className="module-badge">💡 Novelty Exploration</span>
                  <button
                    className="btn btn-primary btn-block"
                    onClick={() => setActiveSection('Research Gap Identification')}
                  >
                    Open Gap Identification →
                  </button>
                </div>
              </div>

              {/* Card 6 */}
              <div className="module-card">
                <div>
                  <h3>📝 Report Generation</h3>
                  <div className="module-category">ACADEMIC REVIEW & EXPORT</div>
                  <p>Draft comprehensive academic reviews incorporating literature, evidence answers, and verified references. Export to Word DOCX or PDF.</p>
                </div>
                <div>
                  <span className="module-badge">📥 PDF & DOCX Export</span>
                  <button
                    className="btn btn-primary btn-block"
                    onClick={() => setActiveSection('Report Generation')}
                  >
                    Open Report Generator →
                  </button>
                </div>
              </div>
            </div>

            <div className="sidebar-divider"></div>

            <h4 style={{ marginBottom: '1rem', color: '#f1f5f9' }}>⚡ Quick Workspace Activity</h4>
            <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
              <div className="sidebar-metric">
                <div className="metric-label">Saved Papers in Library</div>
                <div className="metric-value">{papers.length}</div>
              </div>
              <div className="sidebar-metric">
                <div className="metric-label">Indexed PDF Documents</div>
                <div className="metric-value">{docs.length}</div>
              </div>
              <div className="sidebar-metric">
                <div className="metric-label">Configured Model</div>
                <div className="metric-value" style={{ fontSize: '1.1rem' }}>{status.active_model}</div>
              </div>
              <div className="sidebar-metric">
                <div className="metric-label">Database</div>
                <div className="metric-value" style={{ fontSize: '1.1rem' }}>SQLite + ChromaDB</div>
              </div>
            </div>

            <div className="grid-2">
              <div className="card">
                <h4 style={{ marginBottom: '0.8rem', color: '#f1f5f9' }}>Recently Saved Papers</h4>
                {papers.length > 0 ? (
                  papers.slice(0, 4).map((p) => (
                    <div key={p.id} style={{ marginBottom: '6px', fontSize: '0.88rem' }}>
                      • <strong>{p.title}</strong> ({p.year || 'n/a'})
                    </div>
                  ))
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                    No papers saved yet. Go to Research Discovery.
                  </div>
                )}
              </div>

              <div className="card">
                <h4 style={{ marginBottom: '0.8rem', color: '#f1f5f9' }}>Recently Indexed Documents</h4>
                {docs.length > 0 ? (
                  docs.slice(0, 4).map((d) => (
                    <div key={d.id} style={{ marginBottom: '6px', fontSize: '0.88rem' }}>
                      • <strong>{d.name}</strong> (added {d.added_at || 'recently'})
                    </div>
                  ))
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                    No documents uploaded yet. Go to Document Analysis.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW: RESEARCH DISCOVERY */}
        {/* ========================================================================= */}
        {activeSection === 'Research Discovery' && (
          <div>
            <div className="section-header">
              <h2>🔍 Research Discovery</h2>
              <button className="btn btn-secondary" onClick={() => setActiveSection('Hub')}>
                ← Back to Hub
              </button>
            </div>

            <div className="card">
              <form onSubmit={handleSearch}>
                <div className="form-group">
                  <label className="form-label">Research topic, keywords, or question</label>
                  <input
                    type="text"
                    className="input"
                    placeholder="e.g., retrieval augmented generation evaluation"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>

                <div className="grid-3">
                  <div className="form-group">
                    <label className="form-label">Academic sources</label>
                    <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
                      {['Crossref', 'arXiv', 'Semantic Scholar'].map((src) => (
                        <label key={src} style={{ fontSize: '0.86rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <input
                            type="checkbox"
                            checked={selectedSources.includes(src)}
                            onChange={(e) => {
                              if (e.target.checked) setSelectedSources([...selectedSources, src]);
                              else setSelectedSources(selectedSources.filter((s) => s !== src));
                            }}
                          />
                          {src}
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">From year (0 = no limit)</label>
                    <input
                      type="number"
                      className="input"
                      value={fromYear}
                      onChange={(e) => setFromYear(e.target.value)}
                      placeholder="0"
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">To year (0 = no limit)</label>
                    <input
                      type="number"
                      className="input"
                      value={toYear}
                      onChange={(e) => setToYear(e.target.value)}
                      placeholder="0"
                    />
                  </div>
                </div>

                <div className="form-group" style={{ maxWidth: '300px' }}>
                  <label className="form-label">Maximum results per source: {searchLimit}</label>
                  <input
                    type="range"
                    min="5"
                    max="25"
                    value={searchLimit}
                    onChange={(e) => setSearchLimit(parseInt(e.target.value))}
                    style={{ width: '100%' }}
                  />
                </div>

                <button type="submit" className="btn btn-primary" disabled={isSearching}>
                  {isSearching ? <span className="spinner"></span> : null}
                  {isSearching ? ' Searching academic indexes…' : 'Search papers'}
                </button>
              </form>
            </div>

            {/* Error notifications */}
            {searchErrors.map((err, idx) => (
              <div key={idx} className="alert alert-warning">
                ⚠️ {err.includes('429')
                  ? 'Semantic Scholar is rate-limiting unauthenticated requests right now. Crossref and arXiv results are still available.'
                  : err}
              </div>
            ))}

            {/* Search Results */}
            {searchResults.length > 0 && (
              <div style={{ marginBottom: '2rem' }}>
                <h3 style={{ margin: '1rem 0', color: '#f8fafc' }}>
                  Search Results ({searchResults.length} papers found)
                </h3>
                {searchResults.map((p, idx) => (
                  <div key={idx} className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
                      <div style={{ flex: 1 }}>
                        <h4 style={{ fontSize: '1.05rem', color: '#ffffff', marginBottom: '4px' }}>
                          {p.title || 'Untitled'}
                        </h4>
                        <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                          {p.authors || 'Authors unavailable'} · {p.year || 'Year n/a'} · {p.source || ''}
                        </div>
                        {p.abstract && (
                          <p style={{ fontSize: '0.88rem', color: '#cbd5e1', lineHeight: '1.45', marginBottom: '8px' }}>
                            {p.abstract}
                          </p>
                        )}
                        <div style={{ fontSize: '0.85rem' }}>
                          {p.doi && (
                            <a href={`https://doi.org/${p.doi}`} target="_blank" rel="noreferrer" style={{ marginRight: '12px' }}>
                              DOI
                            </a>
                          )}
                          {p.url && (
                            <a href={p.url} target="_blank" rel="noreferrer">
                              Open source
                            </a>
                          )}
                        </div>
                      </div>
                      <div>
                        <button
                          className="btn btn-secondary"
                          onClick={() => handleSavePaper(p)}
                        >
                          Save paper
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="sidebar-divider"></div>

            <h4 style={{ marginBottom: '1rem', color: '#f1f5f9' }}>Your saved library</h4>
            {papers.length > 0 ? (
              papers.map((p) => (
                <div key={p.id} className="card" style={{ padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong>{p.title}</strong> · {p.year || 'year n/a'} · {p.source || ''}
                  </div>
                  <button className="btn btn-danger" onClick={() => handleDeletePaper(p.id)}>
                    Remove
                  </button>
                </div>
              ))
            ) : (
              <div className="alert alert-info">Search for papers and save useful results here.</div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW: DOCUMENT ANALYSIS */}
        {/* ========================================================================= */}
        {activeSection === 'Document Analysis' && (
          <div>
            <div className="section-header">
              <h2>📄 Document Analysis</h2>
              <button className="btn btn-secondary" onClick={() => setActiveSection('Hub')}>
                ← Back to Hub
              </button>
            </div>

            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.2rem', fontSize: '0.92rem' }}>
              Upload one or more PDF papers. Text, page numbers, and detected section labels are stored in your shared research collection.
            </p>

            <div className="card">
              <div className="form-group">
                <label className="form-label">Link uploaded files to a saved paper (optional)</label>
                <select
                  className="select"
                  value={selectedPaperForUpload}
                  onChange={(e) => setSelectedPaperForUpload(e.target.value)}
                >
                  <option value="None">None</option>
                  {papers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Upload research PDFs</label>
                <input
                  type="file"
                  accept="application/pdf"
                  multiple
                  className="input"
                  onChange={(e) => setSelectedFiles(Array.from(e.target.files))}
                />
              </div>

              <button
                className="btn btn-primary"
                onClick={handleUpload}
                disabled={selectedFiles.length === 0 || isUploading}
              >
                {isUploading ? <span className="spinner"></span> : null}
                {isUploading ? ' Analyzing and indexing PDFs…' : 'Analyze and index PDFs'}
              </button>
            </div>

            {/* Upload results / summaries */}
            {uploadNotes.map((note, idx) => (
              <div key={idx} className="accordion">
                <div className="accordion-header">
                  <span>{note.name} — {note.meta?.title || 'Extracted Document'}</span>
                </div>
                <div className="accordion-body">
                  <div className="markdown-content">{note.summary}</div>
                </div>
              </div>
            ))}

            <h4 style={{ margin: '1.5rem 0 1rem 0', color: '#f1f5f9' }}>Indexed collection</h4>
            {docs.length > 0 ? (
              docs.map((d) => (
                <div key={d.id} className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                    <div>
                      <strong style={{ fontSize: '1rem', color: '#ffffff' }}>{d.name}</strong>
                      <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginLeft: '10px' }}>
                        added {d.added_at}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        className="btn btn-primary"
                        onClick={() => handleSummarizeDoc(d.id)}
                        disabled={summarizingDocId === d.id}
                      >
                        {summarizingDocId === d.id ? <span className="spinner"></span> : null}
                        {summarizingDocId === d.id ? ' Summarizing…' : 'Generate / retry summary'}
                      </button>
                      <button className="btn btn-danger" onClick={() => handleDeleteDoc(d.id)}>
                        Delete
                      </button>
                    </div>
                  </div>

                  {d.summary && (
                    <div className="accordion" style={{ marginTop: '12px' }}>
                      <div className="accordion-header">
                        <span>AI summary</span>
                      </div>
                      <div className="accordion-body">
                        <div className="markdown-content">{d.summary}</div>
                      </div>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="alert alert-info">Your uploaded documents will appear here.</div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW: AI RESEARCH ASSISTANT */}
        {/* ========================================================================= */}
        {activeSection === 'AI Research Assistant' && (
          <div>
            <div className="section-header">
              <h2>🤖 AI Research Assistant</h2>
              <button className="btn btn-secondary" onClick={() => setActiveSection('Hub')}>
                ← Back to Hub
              </button>
            </div>

            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.2rem', fontSize: '0.92rem' }}>
              Answers use retrieved passages from your uploaded documents. Citations identify exact source documents and pages.
            </p>

            <div className="card">
              <div className="form-group">
                <label className="form-label">Research collection (filter by indexed documents)</label>
                {docs.length > 0 ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginTop: '6px' }}>
                    {docs.map((d) => (
                      <label key={d.id} style={{ fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <input
                          type="checkbox"
                          checked={selectedDocIds.includes(d.id)}
                          onChange={(e) => {
                            if (e.target.checked) setSelectedDocIds([...selectedDocIds, d.id]);
                            else setSelectedDocIds(selectedDocIds.filter((id) => id !== d.id));
                          }}
                        />
                        {d.name}
                      </label>
                    ))}
                  </div>
                ) : (
                  <div className="alert alert-info" style={{ marginTop: '8px' }}>
                    Upload PDFs in Document Analysis to enable passage-level RAG.
                  </div>
                )}
              </div>

              <div className="form-group">
                <label className="form-label">Ask a research question</label>
                <textarea
                  className="textarea"
                  placeholder="What methods do these papers use, and what limitations do they report?"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                />
              </div>

              <button
                className="btn btn-primary"
                onClick={handleAskQuestion}
                disabled={!question.trim() || isAnswering}
              >
                {isAnswering ? <span className="spinner"></span> : null}
                {isAnswering
                  ? ' Research planner → evidence retrieval → synthesis → citation critic…'
                  : 'Research question'}
              </button>
            </div>

            {/* Answer Display */}
            {lastAnswer && (
              <div style={{ marginTop: '1.5rem' }}>
                <div className="card">
                  <h3 style={{ marginBottom: '0.8rem', color: '#ffffff' }}>Answer</h3>
                  <div className="markdown-content" style={{ fontSize: '0.95rem' }}>
                    {lastAnswer.answer}
                  </div>
                  <div style={{ marginTop: '1rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Workflow status: {lastAnswer.status || 'complete'}
                  </div>
                </div>

                {lastAnswer.plan && (
                  <div className="accordion">
                    <div className="accordion-header">
                      <span>Research plan</span>
                    </div>
                    <div className="accordion-body">
                      <div className="markdown-content">{lastAnswer.plan}</div>
                    </div>
                  </div>
                )}

                <h4 style={{ margin: '1.2rem 0 0.8rem 0', color: '#f1f5f9' }}>Retrieved evidence</h4>
                {lastAnswer.evidence?.map((x, i) => (
                  <div key={i} className="accordion">
                    <div className="accordion-header">
                      <span>
                        [E{i + 1}] {x.name} · page {x.page || '?'} · relevance {x.score?.toFixed(2) || '0.00'}
                      </span>
                    </div>
                    <div className="accordion-body">
                      <p>{x.text}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW: COMPARATIVE ANALYSIS */}
        {/* ========================================================================= */}
        {activeSection === 'Comparative Analysis' && (
          <div>
            <div className="section-header">
              <h2>⚖️ Comparative Analysis</h2>
              <button className="btn btn-secondary" onClick={() => setActiveSection('Hub')}>
                ← Back to Hub
              </button>
            </div>

            {papers.length < 2 ? (
              <div className="alert alert-info">
                Save at least two papers in Research Discovery to compare them.
              </div>
            ) : (
              <div className="card">
                <div className="form-group">
                  <label className="form-label">Select papers to compare (at least 2)</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '6px' }}>
                    {papers.map((p) => (
                      <label key={p.id} style={{ fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <input
                          type="checkbox"
                          checked={selectedComparePapers.includes(p.id)}
                          onChange={(e) => {
                            if (e.target.checked) setSelectedComparePapers([...selectedComparePapers, p.id]);
                            else setSelectedComparePapers(selectedComparePapers.filter((id) => id !== p.id));
                          }}
                        />
                        <strong>{p.title}</strong> ({p.year || 'n/a'})
                      </label>
                    ))}
                  </div>
                </div>

                <button
                  className="btn btn-primary"
                  onClick={handleCompare}
                  disabled={selectedComparePapers.length < 2 || isComparing}
                >
                  {isComparing ? <span className="spinner"></span> : null}
                  {isComparing ? ' Comparing available abstracts and metadata…' : 'Generate comparison'}
                </button>
              </div>
            )}

            {comparisonResult && (
              <div style={{ marginTop: '1.5rem' }}>
                <div className="card">
                  <h3 style={{ marginBottom: '1rem', color: '#ffffff' }}>Comparative Matrix</h3>
                  <div className="markdown-content">{comparisonResult}</div>
                </div>

                {comparedPapersList.length > 0 && (
                  <div className="card">
                    <h4 style={{ marginBottom: '0.8rem', color: '#ffffff' }}>Compared Papers Overview</h4>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Title</th>
                          <th>Year</th>
                          <th>Authors</th>
                          <th>DOI</th>
                          <th>Source</th>
                        </tr>
                      </thead>
                      <tbody>
                        {comparedPapersList.map((p, i) => (
                          <tr key={i}>
                            <td><strong>{p.title}</strong></td>
                            <td>{p.year || 'n/a'}</td>
                            <td>{p.authors || 'n/a'}</td>
                            <td>{p.doi || 'Not available'}</td>
                            <td>{p.source || 'n/a'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW: RESEARCH GAP IDENTIFICATION */}
        {/* ========================================================================= */}
        {activeSection === 'Research Gap Identification' && (
          <div>
            <div className="section-header">
              <h2>🔬 Research Gap Identification</h2>
              <button className="btn btn-secondary" onClick={() => setActiveSection('Hub')}>
                ← Back to Hub
              </button>
            </div>

            <div className="alert alert-warning">
              ⚠️ Suggested gaps are hypotheses based on the saved records and abstracts. Check the original literature before claiming novelty.
            </div>

            {papers.length === 0 ? (
              <div className="alert alert-info">Save a collection of papers first in Research Discovery.</div>
            ) : (
              <div className="card">
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.92rem' }}>
                  Analyzing {papers.length} saved paper records.
                </p>
                <button
                  className="btn btn-primary"
                  onClick={handleIdentifyGaps}
                  disabled={isFindingGaps}
                >
                  {isFindingGaps ? <span className="spinner"></span> : null}
                  {isFindingGaps
                    ? ' Reviewing recurring methods, limitations, and underexplored directions…'
                    : 'Identify evidence-backed gaps'}
                </button>
              </div>
            )}

            {gapsResult && (
              <div className="card" style={{ marginTop: '1.5rem' }}>
                <h3 style={{ marginBottom: '1rem', color: '#ffffff' }}>Identified Research Gaps</h3>
                <div className="markdown-content">{gapsResult}</div>
                <div style={{ marginTop: '1.2rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                  Coverage depends on saved records and available abstracts. A larger, more diverse collection improves the review but does not establish novelty.
                </div>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW: REPORT GENERATION */}
        {/* ========================================================================= */}
        {activeSection === 'Report Generation' && (
          <div>
            <div className="section-header">
              <h2>📝 Report Generation</h2>
              <button className="btn btn-secondary" onClick={() => setActiveSection('Hub')}>
                ← Back to Hub
              </button>
            </div>

            {papers.length === 0 ? (
              <div className="alert alert-info">Save papers in Research Discovery to generate a report.</div>
            ) : (
              <div className="card">
                <div className="form-group">
                  <label className="form-label">Research topic / report title</label>
                  <input
                    type="text"
                    className="input"
                    placeholder="e.g., Retrieval Augmented Generation Evaluation"
                    value={reportTopic}
                    onChange={(e) => setReportTopic(e.target.value)}
                  />
                </div>

                <button
                  className="btn btn-primary"
                  onClick={handleDraftReport}
                  disabled={isDraftingReport}
                >
                  {isDraftingReport ? <span className="spinner"></span> : null}
                  {isDraftingReport ? ' Drafting cited report…' : 'Draft research report'}
                </button>
              </div>
            )}

            {reportText && (
              <div className="card" style={{ marginTop: '1.5rem' }}>
                <h3 style={{ marginBottom: '0.8rem', color: '#ffffff' }}>Preview and edit report</h3>
                <div className="form-group">
                  <textarea
                    className="textarea"
                    style={{ minHeight: '380px', fontFamily: 'monospace', fontSize: '0.88rem' }}
                    value={reportText}
                    onChange={(e) => setReportText(e.target.value)}
                  />
                </div>

                {reportSavedMsg && (
                  <div className="alert alert-success" style={{ marginBottom: '1rem' }}>
                    ✅ {reportSavedMsg}
                  </div>
                )}

                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  <button className="btn btn-secondary" onClick={handleSaveReportToDb}>
                    Save report to database
                  </button>
                  <button
                    className="btn btn-primary"
                    onClick={() => downloadDocx(reportText, reportTopic)}
                  >
                    Download DOCX
                  </button>
                  <button
                    className="btn btn-primary"
                    onClick={() => downloadPdf(reportText, reportTopic)}
                  >
                    Download PDF
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
