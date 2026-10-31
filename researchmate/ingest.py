import re

SECTION_NAMES = ['abstract','introduction','related work','literature review','methodology','methods','materials and methods','results','discussion','conclusion','limitations']

def extract_pdf(filename, payload):
    try:
        import fitz
    except ImportError as e:
        raise RuntimeError('Install project dependencies with: pip install -r requirements.txt (PyMuPDF is needed for PDF extraction).') from e
    doc=fitz.open(stream=payload,filetype='pdf')
    pages=[]
    for n,page in enumerate(doc,1):
        txt=page.get_text('text').strip()
        if txt: pages.append({'page':n,'text':txt})
    return pages

def split_chunks(pages, size=1100, overlap=160):
    out=[]
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter=RecursiveCharacterTextSplitter(chunk_size=size,chunk_overlap=overlap,separators=['\n\n','\n','. ',' ',''])
        for pg in pages:
            section=''
            low=pg['text'].lower()
            for s in SECTION_NAMES:
                if re.search(r'\b'+re.escape(s)+r'\b',low): section=s.title(); break
            for piece in splitter.split_text(pg['text']):
                piece=re.sub(r'\s+',' ',piece).strip()
                if len(piece)>60: out.append({'page':pg['page'],'section':section,'text':piece})
        return out
    except ImportError:
        pass
    for pg in pages:
        text=re.sub(r'\s+',' ',pg['text']).strip()
        # Keep page metadata and detect nearby paper section headings.
        section=''
        low=text.lower()
        for s in SECTION_NAMES:
            if re.search(r'\b'+re.escape(s)+r'\b',low): section=s.title(); break
        start=0
        while start<len(text):
            end=min(len(text),start+size)
            if end<len(text):
                boundary=text.rfind('. ',start+size//2,end)
                if boundary>start: end=boundary+1
            piece=text[start:end].strip()
            if len(piece)>60: out.append({'page':pg['page'],'section':section,'text':piece})
            if end>=len(text): break
            start=max(start+1,end-overlap)
    return out

def metadata_from_pdf(filename, pages):
    text='\n'.join(p['text'] for p in pages[:3])
    lines=[re.sub(r'\s+',' ',x).strip() for x in text.splitlines() if x.strip()]
    title=next((x for x in lines if len(x)>12 and len(x)<180 and not x.lower().startswith(('abstract','arxiv','doi:'))),filename.rsplit('.',1)[0])
    return {'title':title,'authors':'','year':None,'doi':''}
