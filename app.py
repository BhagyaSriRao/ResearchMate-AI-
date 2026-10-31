import io, re, importlib
import pandas as pd
import streamlit as st

import researchmate.config
import researchmate.ai
import researchmate.agents

importlib.reload(researchmate.config)
importlib.reload(researchmate.ai)
importlib.reload(researchmate.agents)

from researchmate.config import GEMINI_API_KEY, get_env_var
from researchmate.db import init_db, list_papers, save_paper, delete_paper, list_documents, add_document, add_chunks, delete_document, save_document_summary, all_chunks
from researchmate.search import search_papers
from researchmate.ingest import extract_pdf, split_chunks, metadata_from_pdf
from researchmate.ai import llm, answer_question, structured_analysis, make_report
from researchmate.agents import run_research_graph

st.set_page_config(page_title='ResearchMate AI', page_icon='📚', layout='wide')
init_db()

st.markdown('''<style>
.block-container { padding-top: 1.2rem; max-width: 1440px; }
.hero {
    padding: 1.5rem 1.8rem;
    border-radius: 18px;
    background: linear-gradient(135deg, #13243d 0%, #0d3b48 50%, #172c44 100%);
    border: 1px solid rgba(80, 216, 204, 0.25);
    color: #f4fbff;
    margin-bottom: 1rem;
    box-shadow: 0 14px 32px rgba(0,0,0,0.3);
}
.hero h1 { margin: 0; font-size: 2.1rem; font-weight: 700; color: #ffffff; letter-spacing: -0.5px; }
.hero p { margin: 0.4rem 0 0; color: #bde4ed; font-size: 1.02rem; }
.hub-header { margin: 1rem 0 0.8rem 0; }
.hub-header h2 { margin: 0; font-size: 1.45rem; color: #f1f5f9; font-weight: 600; }
.hub-header p { margin: 0.25rem 0 0; color: #94a3b8; font-size: 0.92rem; }
.module-badge {
    display: inline-block;
    background: rgba(56, 189, 248, 0.12);
    color: #38bdf8;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    border: 1px solid rgba(56, 189, 248, 0.25);
    margin-bottom: 0.8rem;
}
div[data-testid="stMetric"] { background: #121a2b; padding: 12px 15px; border-radius: 12px; border: 1px solid #27344a; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #29364b !important; border-radius: 14px; }
button[kind="primary"] { box-shadow: 0 4px 14px rgba(57, 185, 165, 0.25); }
a { color: #80d8cc !important; }
</style>''', unsafe_allow_html=True)

papers = list_papers()
docs = list_documents()
active_key = get_env_var("GEMINI_API_KEY")
active_model = get_env_var("GEMINI_MODEL", "gemini-2.5-flash")

# Navigation state management
if 'active_section' not in st.session_state:
    st.session_state['active_section'] = 'Hub'

NAV_OPTIONS = [
    '🏠 Workspace Hub',
    '🔍 Research Discovery',
    '📄 Document Analysis',
    '🤖 AI Research Assistant',
    '⚖️ Comparative Analysis',
    '🔬 Research Gap Identification',
    '📝 Report Generation'
]

LABEL_TO_SECTION = {
    '🏠 Workspace Hub': 'Hub',
    '🔍 Research Discovery': 'Research Discovery',
    '📄 Document Analysis': 'Document Analysis',
    '🤖 AI Research Assistant': 'AI Research Assistant',
    '⚖️ Comparative Analysis': 'Comparative Analysis',
    '🔬 Research Gap Identification': 'Research Gap Identification',
    '📝 Report Generation': 'Report Generation'
}
SECTION_TO_LABEL = {v: k for k, v in LABEL_TO_SECTION.items()}

# Sidebar Utility Panel
st.sidebar.title('📚 ResearchMate AI')
st.sidebar.caption('Interactive Multi-Agent Academic Workspace')

if st.sidebar.button('🏠 Workspace Hub', key='side_hub_btn', use_container_width=True, type='secondary' if st.session_state['active_section'] != 'Hub' else 'primary'):
    st.session_state['active_section'] = 'Hub'
    st.rerun()

st.sidebar.divider()
st.sidebar.metric('Saved papers', len(papers))
st.sidebar.metric('Indexed documents', len(docs))
if not active_key:
    st.sidebar.caption('Gemini: add GEMINI_API_KEY in .env for generated analysis')
else:
    st.sidebar.caption(f'Gemini: connected ({active_model})')

with st.sidebar.expander('📚 Saved Papers Library', expanded=False):
    if papers:
        for p in papers:
            st.markdown(f"• **{p['title']}** ({p.get('year') or 'n/a'})")
    else:
        st.caption('No papers saved yet.')

# Hero Banner
st.markdown('<div class="hero"><h1>ResearchMate AI</h1><p>Discover, analyze, compare, and synthesize research with verifiable evidence and multi-agent AI.</p></div>', unsafe_allow_html=True)

# Top Navigation Pills Bar
current_label = SECTION_TO_LABEL.get(st.session_state['active_section'], '🏠 Workspace Hub')
selected_pill = st.pills(
    "Navigation",
    NAV_OPTIONS,
    default=current_label,
    label_visibility="collapsed",
    key="top_nav_pills"
)
if selected_pill and LABEL_TO_SECTION.get(selected_pill) != st.session_state['active_section']:
    st.session_state['active_section'] = LABEL_TO_SECTION[selected_pill]
    st.rerun()

section = st.session_state['active_section']

def show_papers(items):
    for i, p in enumerate(items):
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"**{p.get('title','Untitled')}**  ")
            c1.caption(f"{p.get('authors') or 'Authors unavailable'} · {p.get('year') or 'Year n/a'} · {p.get('source') or ''}")
            if p.get('abstract'): c1.write(p['abstract'])
            links = []
            if p.get('doi'): links.append(f"[DOI](https://doi.org/{p['doi']})")
            if p.get('url'): links.append(f"[Open source]({p['url']})")
            if links: c1.markdown(' · '.join(links))
            if c2.button('Save paper', key=f"save_{section}_{i}_{p.get('id')}"):
                save_paper(p); st.success('Saved to your research library.'); st.rerun()

# ==============================================================================
# SECTION: WORKSPACE HUB (Interactive Central Components)
# ==============================================================================
if section == 'Hub':
    st.markdown('<div class="hub-header"><h2>Workspace Modules</h2><p>Click any component below to launch the respective research stage:</p></div>', unsafe_allow_html=True)
    
    # 3-column interactive component grid
    row1_c1, row1_c2, row1_c3 = st.columns(3)
    
    with row1_c1:
        with st.container(border=True):
            st.markdown('### 🔍 Research Discovery')
            st.caption('ACADEMIC SEARCH & LIBRARY')
            st.write('Search academic papers across Crossref, arXiv, and Semantic Scholar with publication year filters. Save results directly into your library.')
            st.markdown(f'<span class="module-badge">📚 {len(papers)} saved papers</span>', unsafe_allow_html=True)
            if st.button('Open Research Discovery →', key='btn_nav_discovery', use_container_width=True, type='primary'):
                st.session_state['active_section'] = 'Research Discovery'
                st.rerun()

    with row1_c2:
        with st.container(border=True):
            st.markdown('### 📄 Document Analysis')
            st.caption('PDF INGESTION & AI SUMMARIES')
            st.write('Upload full-text PDF papers. Automatically extract page numbers, detect paper sections, build vector chunks, and generate structured summaries.')
            st.markdown(f'<span class="module-badge">📑 {len(docs)} indexed documents</span>', unsafe_allow_html=True)
            if st.button('Open Document Analysis →', key='btn_nav_analysis', use_container_width=True, type='primary'):
                st.session_state['active_section'] = 'Document Analysis'
                st.rerun()

    with row1_c3:
        with st.container(border=True):
            st.markdown('### 🤖 AI Research Assistant')
            st.caption('MULTI-AGENT GROUNDED RAG')
            st.write('Ask complex research questions. Runs a multi-agent workflow (Planner → Retrieval → Synthesis → Citation Critic) with page-level citations.')
            st.markdown('<span class="module-badge">⚡ LangGraph Multi-Agent</span>', unsafe_allow_html=True)
            if st.button('Open AI Assistant →', key='btn_nav_assistant', use_container_width=True, type='primary'):
                st.session_state['active_section'] = 'AI Research Assistant'
                st.rerun()

    st.write("")
    row2_c1, row2_c2, row2_c3 = st.columns(3)

    with row2_c1:
        with st.container(border=True):
            st.markdown('### ⚖️ Comparative Analysis')
            st.caption('CROSS-PAPER SYNTHESIS')
            st.write('Select 2 or more saved papers to compare side-by-side across objectives, algorithms, benchmarks, metrics, and reported limitations.')
            st.markdown('<span class="module-badge">📊 Matrix Comparison</span>', unsafe_allow_html=True)
            if st.button('Open Comparative Analysis →', key='btn_nav_compare', use_container_width=True, type='primary'):
                st.session_state['active_section'] = 'Comparative Analysis'
                st.rerun()

    with row2_c2:
        with st.container(border=True):
            st.markdown('### 🔬 Research Gap Identification')
            st.caption('HYPOTHESIS & LIMITATION DISCOVERY')
            st.write('Review recurring methods, explicitly acknowledged limitations, and uncover evidence-backed underexplored directions with source citations.')
            st.markdown('<span class="module-badge">💡 Novelty Exploration</span>', unsafe_allow_html=True)
            if st.button('Open Gap Identification →', key='btn_nav_gaps', use_container_width=True, type='primary'):
                st.session_state['active_section'] = 'Research Gap Identification'
                st.rerun()

    with row2_c3:
        with st.container(border=True):
            st.markdown('### 📝 Report Generation')
            st.caption('ACADEMIC REVIEW & EXPORT')
            st.write('Draft comprehensive academic reviews incorporating literature, evidence answers, and verified references. Export to Word DOCX or PDF.')
            st.markdown('<span class="module-badge">📥 PDF & DOCX Export</span>', unsafe_allow_html=True)
            if st.button('Open Report Generator →', key='btn_nav_report', use_container_width=True, type='primary'):
                st.session_state['active_section'] = 'Report Generation'
                st.rerun()

    # Workspace status & quick preview
    st.divider()
    st.markdown('#### ⚡ Quick Workspace Activity')
    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Saved Papers in Library', len(papers))
    m2.metric('Indexed PDF Documents', len(docs))
    m3.metric('Configured Model', active_model)
    m4.metric('Database', 'SQLite + ChromaDB')

    if papers or docs:
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown('##### Recently Saved Papers')
            if papers:
                for p in papers[:4]:
                    st.write(f"• **{p['title']}** ({p.get('year') or 'n/a'})")
            else:
                st.caption('No papers saved yet. Go to Research Discovery.')
        with col_right:
            st.markdown('##### Recently Indexed Documents')
            if docs:
                for d in docs[:4]:
                    st.write(f"• **{d['name']}** (added {d.get('added_at','recently')})")
            else:
                st.caption('No documents uploaded yet. Go to Document Analysis.')

# ==============================================================================
# SECTION: RESEARCH DISCOVERY
# ==============================================================================
elif section == 'Research Discovery':
    h_col1, h_col2 = st.columns([5, 1])
    h_col1.subheader('🔍 Research Discovery')
    if h_col2.button('← Back to Hub', key='back_from_discovery'):
        st.session_state['active_section'] = 'Hub'
        st.rerun()

    with st.form('paper_search'):
        query = st.text_input('Research topic, keywords, or question', placeholder='e.g., retrieval augmented generation evaluation')
        a, b, c = st.columns(3)
        sources = a.multiselect('Academic sources', ['Crossref', 'arXiv', 'Semantic Scholar'], default=['Crossref', 'arXiv'])
        y1 = b.number_input('From year (0 = no limit)', min_value=0, max_value=2100, value=0)
        y2 = c.number_input('To year (0 = no limit)', min_value=0, max_value=2100, value=0)
        limit = st.slider('Maximum results per source', 5, 25, 10)
        submitted = st.form_submit_button('Search papers', type='primary')

    if submitted:
        if not query.strip():
            st.warning('Enter a topic or question.')
        else:
            with st.spinner('Searching academic indexes…'):
                results, errors = search_papers(query, sources, limit, int(y1) or None, int(y2) or None)
            st.session_state['search_results'] = results
            for e in errors:
                if e.startswith('Semantic Scholar:') and '429' in e:
                    st.warning('Semantic Scholar is rate-limiting unauthenticated requests right now. Crossref and arXiv results are still available; add a Semantic Scholar key later if needed.')
                else:
                    provider = e.split(':', 1)[0]
                    st.warning(f'{provider} search is temporarily unavailable. Results from other selected sources may still be shown.')
            if not results and not errors:
                st.info('No papers found. Try broader keywords.')

    if st.session_state.get('search_results'):
        show_papers(st.session_state['search_results'])

    st.divider()
    st.markdown('#### Your saved library')
    if papers:
        for p in papers:
            a, b = st.columns([6, 1])
            a.write(f"**{p['title']}** · {p.get('year') or 'year n/a'} · {p.get('source') or ''}")
            if b.button('Remove', key=f"delpaper_{p['id']}"):
                delete_paper(p['id'])
                st.rerun()
    else:
        st.info('Search for papers and save useful results here.')

# ==============================================================================
# SECTION: DOCUMENT ANALYSIS
# ==============================================================================
elif section == 'Document Analysis':
    h_col1, h_col2 = st.columns([5, 1])
    h_col1.subheader('📄 Document Analysis')
    if h_col2.button('← Back to Hub', key='back_from_analysis'):
        st.session_state['active_section'] = 'Hub'
        st.rerun()

    st.write('Upload one or more PDF papers. Text, page numbers, and detected section labels are stored in your shared research collection.')
    selected_paper = st.selectbox('Link uploaded files to a saved paper (optional)', options=['None'] + [p['id'] for p in papers], format_func=lambda x: 'None' if x == 'None' else next((p['title'] for p in papers if p['id'] == x), x))
    files = st.file_uploader('Upload research PDFs', type=['pdf'], accept_multiple_files=True)

    if st.button('Analyze and index PDFs', type='primary', disabled=not files):
        progress = st.progress(0)
        notes = []
        for i, f in enumerate(files):
            try:
                pages = extract_pdf(f.name, f.getvalue())
                text = '\n\n'.join(x['text'] for x in pages)
                if not text.strip():
                    raise ValueError('No selectable text found; this may be a scanned PDF.')
                meta = metadata_from_pdf(f.name, pages)
                did = add_document(f.name, text, None if selected_paper == 'None' else selected_paper)
                add_chunks(did, split_chunks(pages))
                extracted = '\n'.join('[p. {}] {}'.format(p['page'], p['text']) for p in pages[:16])[:24000]
                prompt = f'''Analyze this academic paper text for a research dashboard. Return fields: Abstract/aim, research objective, methodology/algorithms, datasets, evaluation metrics and results, limitations. Use only the supplied text. For each item cite page number as (p. N). Write "Not found in extracted text" when absent. Do not infer.\n\n{extracted}'''
                summary = llm(prompt)
                if summary is None:
                    summary_note = 'Document extracted and indexed. Gemini API key was not loaded. Check GEMINI_API_KEY in the project .env file, then fully restart Streamlit.'
                elif summary.startswith('__ERROR__'):
                    summary_note = 'Document extracted and indexed, but Gemini failed: ' + summary.replace('__ERROR__', '', 1).strip()
                else:
                    summary_note = summary
                    save_document_summary(did, summary)
                notes.append((f.name, meta, summary_note))
            except Exception as e:
                notes.append((f.name, None, f'Could not analyze file: {e}'))
            progress.progress((i + 1) / len(files))
        st.session_state['analysis_notes'] = notes
        st.rerun()

    for name, meta, summary in st.session_state.get('analysis_notes', []):
        with st.expander(f"{name} — {meta['title'] if meta else 'Error'}", expanded=True):
            st.write(summary)

    st.markdown('#### Indexed collection')
    for d in docs:
        with st.container(border=True):
            st.write(f"**{d['name']}** · added {d['added_at']}")
            if d.get('summary'):
                with st.expander('AI summary', expanded=False):
                    st.markdown(d['summary'])
            a, b = st.columns([3, 1])
            if a.button('Generate / retry summary', key=f"summary_{d['id']}", type='primary'):
                active_api_key = get_env_var("GEMINI_API_KEY")
                if not active_api_key:
                    st.error('Gemini API key was not loaded. Check GEMINI_API_KEY in the project .env.')
                else:
                    page_chunks = all_chunks([d['id']])
                    extracted = '\n'.join(f"[p. {x['page']}] {x['text']}" for x in page_chunks)[:24000]
                    if not extracted:
                        extracted = d.get('text', '')[:24000]
                    prompt = f'''Analyze this academic paper text for a research dashboard. Return fields: Abstract/aim, research objective, methodology/algorithms, datasets, evaluation metrics and results, limitations. Use only the supplied text. For each item cite page number when present. Write "Not found in extracted text" when absent. Do not infer.\n\n{extracted}'''
                    with st.spinner('Asking Gemini to summarize this indexed paper…'):
                        result = llm(prompt)
                    if result is None:
                        st.error('Gemini API key was not loaded. Add GEMINI_API_KEY in .env.')
                    elif result.startswith('__ERROR__'):
                        st.error('Gemini request failed: ' + result.replace('__ERROR__', '', 1).strip())
                    else:
                        save_document_summary(d['id'], result)
                        st.success('Summary saved.')
                        st.rerun()
            if b.button('Delete', key=f"deldoc_{d['id']}"):
                delete_document(d['id'])
                st.rerun()
    if not docs:
        st.info('Your uploaded documents will appear here.')

# ==============================================================================
# SECTION: AI RESEARCH ASSISTANT
# ==============================================================================
elif section == 'AI Research Assistant':
    h_col1, h_col2 = st.columns([5, 1])
    h_col1.subheader('🤖 AI Research Assistant')
    if h_col2.button('← Back to Hub', key='back_from_assistant'):
        st.session_state['active_section'] = 'Hub'
        st.rerun()

    st.caption('Answers use retrieved passages from your uploaded documents. Citations identify exact source documents and pages.')
    doc_options = {d['id']: d['name'] for d in docs}
    chosen = st.multiselect('Research collection', options=list(doc_options), format_func=lambda x: doc_options[x], default=list(doc_options))
    question = st.text_area('Ask a research question', placeholder='What methods do these papers use, and what limitations do they report?')
    if st.button('Research question', type='primary', disabled=not question.strip()):
        with st.spinner('Research planner → evidence retrieval → synthesis → citation critic…'):
            result = run_research_graph(question, chosen)
        st.session_state['last_answer'] = result
        st.session_state['last_question'] = question
    if st.session_state.get('last_answer'):
        result = st.session_state['last_answer']
        st.markdown('#### Answer')
        st.markdown(result['answer'])
        st.caption(f"Workflow status: {result.get('status','complete')}")
        with st.expander('Research plan'):
            st.markdown(result['plan'])
        st.markdown('#### Retrieved evidence')
        for i, x in enumerate(result['evidence'], 1):
            with st.expander(f"[E{i}] {x['name']} · page {x['page'] or '?'} · relevance {x.get('score',0):.2f}"):
                st.write(x['text'])
    if not docs:
        st.info('Upload PDFs in Document Analysis to enable passage-level RAG.')

# ==============================================================================
# SECTION: COMPARATIVE ANALYSIS
# ==============================================================================
elif section == 'Comparative Analysis':
    h_col1, h_col2 = st.columns([5, 1])
    h_col1.subheader('⚖️ Comparative Analysis')
    if h_col2.button('← Back to Hub', key='back_from_compare'):
        st.session_state['active_section'] = 'Hub'
        st.rerun()

    if len(papers) < 2:
        st.info('Save at least two papers in Research Discovery to compare them.')
    else:
        selected = st.multiselect('Select papers', options=[p['id'] for p in papers], default=[p['id'] for p in papers[:min(4, len(papers))]], format_func=lambda x: next(p['title'] for p in papers if p['id'] == x))
        chosen = [p for p in papers if p['id'] in selected]
        if st.button('Generate comparison', type='primary', disabled=len(chosen) < 2):
            with st.spinner('Comparing available abstracts and metadata…'):
                comp = structured_analysis(chosen, 'Compare research objectives, methods/algorithms, datasets, metrics, findings, and limitations. Give a concise table-like structured report. Do not fill gaps with assumptions.')
            st.session_state['comparison'] = comp
            st.session_state['comparison_papers'] = chosen
        if st.session_state.get('comparison'):
            st.markdown(st.session_state['comparison'])
            rows = []
            for p in st.session_state.get('comparison_papers', []):
                rows.append({'Title': p['title'], 'Year': p.get('year'), 'Authors': p.get('authors'), 'DOI': p.get('doi') or 'Not available', 'Source': p.get('source')})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ==============================================================================
# SECTION: RESEARCH GAP IDENTIFICATION
# ==============================================================================
elif section == 'Research Gap Identification':
    h_col1, h_col2 = st.columns([5, 1])
    h_col1.subheader('🔬 Research Gap Identification')
    if h_col2.button('← Back to Hub', key='back_from_gaps'):
        st.session_state['active_section'] = 'Hub'
        st.rerun()

    st.warning('Suggested gaps are hypotheses based on the saved records and abstracts. Check the original literature before claiming novelty.')
    if not papers:
        st.info('Save a collection of papers first in Research Discovery.')
    else:
        st.write(f'Analyzing {len(papers)} saved paper records.')
        if st.button('Identify evidence-backed gaps', type='primary'):
            with st.spinner('Reviewing recurring methods, limitations, and underexplored directions…'):
                gaps = structured_analysis(papers, 'Identify recurring methods and datasets, limitations explicitly reported in the abstracts, and possible underexplored directions. Structure each item as: observation, evidence [P#], confidence/coverage, and follow-up search needed. Separate direct evidence from hypotheses. Do not claim novelty.')
            st.session_state['gaps'] = gaps
        if st.session_state.get('gaps'):
            st.markdown(st.session_state['gaps'])
        st.caption('Coverage depends on saved records and available abstracts. A larger, more diverse collection improves the review but does not establish novelty.')

# ==============================================================================
# SECTION: REPORT GENERATION
# ==============================================================================
elif section == 'Report Generation':
    h_col1, h_col2 = st.columns([5, 1])
    h_col1.subheader('📝 Report Generation')
    if h_col2.button('← Back to Hub', key='back_from_report'):
        st.session_state['active_section'] = 'Hub'
        st.rerun()

    if not papers:
        st.info('Save papers in Research Discovery to generate a report.')
    topic = st.text_input('Research topic / report title', value=st.session_state.get('last_question', ''))
    if papers and st.button('Draft research report', type='primary'):
        with st.spinner('Drafting cited report…'):
            body = make_report(topic or 'Research overview', papers, st.session_state.get('last_answer', {}).get('answer') if st.session_state.get('last_answer') else None, st.session_state.get('comparison'), st.session_state.get('gaps'))
        st.session_state['report'] = body
    if st.session_state.get('report'):
        body = st.text_area('Preview and edit report', value=st.session_state['report'], height=460)
        c1, c2, c3 = st.columns(3)
        if c1.button('Save report to database'):
            from researchmate.db import save_report
            save_report(topic or 'Research report', body)
            st.success('Report saved.')
        docx_buffer = io.BytesIO()
        try:
            from docx import Document
            doc = Document()
            for line in body.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith('# '):
                    doc.add_heading(line[2:], 0)
                elif line.startswith('## '):
                    doc.add_heading(line[3:], 1)
                elif line.startswith('### '):
                    doc.add_heading(line[4:], 2)
                elif line.startswith('- '):
                    doc.add_paragraph(line[2:], style='List Bullet')
                else:
                    doc.add_paragraph(re.sub(r'\*\*(.*?)\*\*', r'\1', line))
            doc.save(docx_buffer)
            c2.download_button('Download DOCX', docx_buffer.getvalue(), file_name='researchmate_report.docx', mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        except Exception as e:
            c2.error(f'DOCX export unavailable: {e}')
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            pdf = io.BytesIO()
            story = []
            styles = getSampleStyleSheet()
            for line in body.splitlines():
                if not line.strip():
                    story.append(Spacer(1, 6))
                    continue
                style = styles['Title'] if line.startswith('# ') else styles['Heading2'] if line.startswith('## ') else styles['BodyText']
                txt = line.lstrip('# ').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('**', '')
                story.append(Paragraph(txt, style))
                story.append(Spacer(1, 4))
            SimpleDocTemplate(pdf, pagesize=letter, title=topic or 'Research report').build(story)
            c3.download_button('Download PDF', pdf.getvalue(), file_name='researchmate_report.pdf', mime='application/pdf')
        except Exception as e:
            c3.error(f'PDF export unavailable: {e}')
