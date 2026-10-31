const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function fetchStatus() {
  const res = await fetch(`${API_BASE}/api/status`);
  if (!res.ok) throw new Error('Failed to fetch status');
  return res.json();
}

export async function fetchPapers() {
  const res = await fetch(`${API_BASE}/api/papers`);
  if (!res.ok) throw new Error('Failed to fetch papers');
  return res.json();
}

export async function savePaper(paper) {
  const res = await fetch(`${API_BASE}/api/papers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(paper)
  });
  if (!res.ok) throw new Error('Failed to save paper');
  return res.json();
}

export async function deletePaper(paperId) {
  const res = await fetch(`${API_BASE}/api/papers/${paperId}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error('Failed to delete paper');
  return res.json();
}

export async function searchPapers(query, sources, limit, fromYear, toYear) {
  const res = await fetch(`${API_BASE}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      sources,
      limit,
      from_year: fromYear ? parseInt(fromYear) : null,
      to_year: toYear ? parseInt(toYear) : null
    })
  });
  if (!res.ok) throw new Error('Search failed');
  return res.json();
}

export async function fetchDocuments() {
  const res = await fetch(`${API_BASE}/api/documents`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function uploadDocuments(formData) {
  const res = await fetch(`${API_BASE}/api/documents/upload`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) throw new Error('Failed to upload documents');
  return res.json();
}

export async function summarizeDocument(docId) {
  const res = await fetch(`${API_BASE}/api/documents/${docId}/summarize`, {
    method: 'POST'
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to summarize' }));
    throw new Error(err.detail || 'Failed to summarize');
  }
  return res.json();
}

export async function deleteDocument(docId) {
  const res = await fetch(`${API_BASE}/api/documents/${docId}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error('Failed to delete document');
  return res.json();
}

export async function askAssistant(question, documentIds) {
  const res = await fetch(`${API_BASE}/api/assistant/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      document_ids: documentIds
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Assistant request failed' }));
    throw new Error(err.detail || 'Assistant request failed');
  }
  return res.json();
}

export async function comparePapers(paperIds) {
  const res = await fetch(`${API_BASE}/api/analysis/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paper_ids: paperIds })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Comparison failed' }));
    throw new Error(err.detail || 'Comparison failed');
  }
  return res.json();
}

export async function identifyGaps() {
  const res = await fetch(`${API_BASE}/api/analysis/gaps`, {
    method: 'POST'
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Gap identification failed' }));
    throw new Error(err.detail || 'Gap identification failed');
  }
  return res.json();
}

export async function draftReport(topic, lastAnswer, comparison, gaps) {
  const res = await fetch(`${API_BASE}/api/report/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topic,
      last_answer: lastAnswer,
      comparison,
      gaps
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Drafting report failed' }));
    throw new Error(err.detail || 'Drafting report failed');
  }
  return res.json();
}

export async function saveReport(title, body) {
  const res = await fetch(`${API_BASE}/api/report/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, body })
  });
  if (!res.ok) throw new Error('Failed to save report');
  return res.json();
}

export async function downloadDocx(body, title) {
  const res = await fetch(`${API_BASE}/api/report/export/docx`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ body, title })
  });
  if (!res.ok) throw new Error('DOCX export failed');
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'researchmate_report.docx';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export async function downloadPdf(body, title) {
  const res = await fetch(`${API_BASE}/api/report/export/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ body, title })
  });
  if (!res.ok) throw new Error('PDF export failed');
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'researchmate_report.pdf';
  document.body.appendChild(a);
  a.click();
  a.remove();
}
