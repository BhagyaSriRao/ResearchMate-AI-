import hashlib, re, xml.etree.ElementTree as ET
from functools import lru_cache
import requests
from .config import SEMANTIC_SCHOLAR_API_KEY, CROSSREF_EMAIL

HEADERS={'User-Agent':'ResearchMateAI/1.0 (academic project)'}

def _normalize(p):
    pid=p.get('paperId') or p.get('id') or p.get('entry_id') or p.get('url','')
    doi=p.get('externalIds',{}).get('DOI') if isinstance(p.get('externalIds'),dict) else p.get('doi','')
    authors=p.get('authors',[])
    authors=', '.join(a.get('name','') for a in authors) if isinstance(authors,list) else str(authors or '')
    return {'id':str(pid or hashlib.sha1(p.get('title','').encode()).hexdigest()),'title':p.get('title') or 'Untitled',
        'authors':authors,'abstract':p.get('abstract') or '', 'year':p.get('year'), 'doi':doi or '',
        'url':p.get('url') or p.get('pdf_url') or '', 'source':p.get('source','')}

def search_semantic_scholar(query, limit=15, year_from=None, year_to=None):
    fields='title,authors,abstract,year,externalIds,url,openAccessPdf'
    params={'query':query,'limit':min(limit,100),'fields':fields}
    if year_from or year_to: params['year']=f"{year_from or 1900}-{year_to or '*'}"
    headers=dict(HEADERS)
    if SEMANTIC_SCHOLAR_API_KEY: headers['x-api-key']=SEMANTIC_SCHOLAR_API_KEY
    try:
        r=requests.get('https://api.semanticscholar.org/graph/v1/paper/search',params=params,headers=headers,timeout=20)
        r.raise_for_status()
        papers=[]
        for x in r.json().get('data',[]):
            item=_normalize(x); item['source']='Semantic Scholar'
            if x.get('openAccessPdf',{}).get('url'): item['url']=x['openAccessPdf']['url']
            papers.append(item)
        return papers
    except requests.RequestException as e: return {'error':f'Semantic Scholar: {e}'}

def search_arxiv(query, limit=15, year_from=None, year_to=None):
    try:
        r=requests.get('https://export.arxiv.org/api/query',params={'search_query':f'all:{query}','start':0,'max_results':min(limit,50),'sortBy':'relevance'},headers=HEADERS,timeout=25)
        r.raise_for_status()
        root=ET.fromstring(r.text); ns={'a':'http://www.w3.org/2005/Atom'}; papers=[]
        for e in root.findall('a:entry',ns):
            published=e.findtext('a:published',default='',namespaces=ns); year=int(published[:4]) if published[:4].isdigit() else None
            if year_from and year and year<year_from: continue
            if year_to and year and year>year_to: continue
            pid=e.findtext('a:id',default='',namespaces=ns)
            item={'id':pid,'title':' '.join(e.findtext('a:title',default='',namespaces=ns).split()),
                  'authors':', '.join(a.findtext('a:name',default='',namespaces=ns) for a in e.findall('a:author',ns)),
                  'abstract':' '.join(e.findtext('a:summary',default='',namespaces=ns).split()),'year':year,
                  'doi':'','url':pid,'source':'arXiv'}
            papers.append(item)
        return papers
    except (requests.RequestException,ET.ParseError) as e: return {'error':f'arXiv: {e}'}

@lru_cache(maxsize=128)
def search_crossref(query, limit=15, year_from=None, year_to=None):
    params={'query.bibliographic':query,'rows':min(limit,100),
            'select':'DOI,title,author,abstract,published-print,published-online,URL,type'}
    if CROSSREF_EMAIL: params['mailto']=CROSSREF_EMAIL
    filters=[]
    if year_from: filters.append(f'from-pub-date:{year_from}-01-01')
    if year_to: filters.append(f'until-pub-date:{year_to}-12-31')
    if filters: params['filter']=','.join(filters)
    try:
        agent='ResearchMateAI/1.0 (academic project)'
        if CROSSREF_EMAIL: agent=f'ResearchMateAI/1.0 (mailto:{CROSSREF_EMAIL})'
        r=requests.get('https://api.crossref.org/works',params=params,
            headers={'User-Agent':agent},timeout=20)
        r.raise_for_status(); items=r.json().get('message',{}).get('items',[]); papers=[]
        for x in items:
            titles=x.get('title') or []
            title=titles[0].strip() if titles else ''
            if not title: continue
            names=[]
            for a in x.get('author',[]):
                name=' '.join(y for y in [a.get('given'),a.get('family')] if y)
                if name: names.append(name)
            dates=x.get('published-print') or x.get('published-online') or {}
            parts=dates.get('date-parts',[[None]])
            year=(parts[0][0] if parts and parts[0] else None)
            doi=x.get('DOI','')
            abstract=re.sub(r'<[^>]+>',' ',x.get('abstract') or '')
            abstract=' '.join(abstract.split())
            papers.append({'id':doi or hashlib.sha1(title.encode()).hexdigest(),'title':title,
                'authors':', '.join(names),'abstract':abstract,'year':year,'doi':doi,
                'url':('https://doi.org/'+doi) if doi else x.get('URL',''),'source':'Crossref'})
        return papers
    except requests.RequestException as e:
        status=getattr(getattr(e,'response',None),'status_code',None)
        return {'error':f'Crossref request failed (HTTP {status}).' if status else 'Crossref is temporarily unavailable.'}

def search_papers(query, sources, limit=15, year_from=None, year_to=None):
    result=[]; errors=[]
    if 'Semantic Scholar' in sources:
        x=search_semantic_scholar(query,limit,year_from,year_to); errors.append(x['error']) if isinstance(x,dict) else result.extend(x)
    if 'arXiv' in sources:
        x=search_arxiv(query,limit,year_from,year_to); errors.append(x['error']) if isinstance(x,dict) else result.extend(x)
    if 'Crossref' in sources:
        x=search_crossref(query,limit,year_from,year_to); errors.append(x['error']) if isinstance(x,dict) else result.extend(x)
    seen=set(); unique=[]
    for p in result:
        key=(p.get('doi') or p['title']).lower()
        if key not in seen: seen.add(key); unique.append(p)
    return unique,errors
