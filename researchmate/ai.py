import os
import re
from collections import Counter
from .config import get_env_var
from .db import all_chunks

_client = None
_cached_key = None

def _normalize_model_name(model_name: str) -> str:
    """Normalize model names and map aliases or typos to valid Gemini API models."""
    if not model_name:
        return "gemini-2.5-flash"
    m = model_name.strip().lower()
    alias_map = {
        "gemini-3.8-flash": "gemini-2.5-flash",
        "gemini-3.0-flash": "gemini-2.5-flash",
        "gemini-3-flash": "gemini-2.5-flash",
        "gemini-flash": "gemini-2.5-flash",
        "flash": "gemini-2.5-flash",
        "gemini-3.8-pro": "gemini-2.5-pro",
        "gemini-3.0-pro": "gemini-2.5-pro",
        "gemini-3-pro": "gemini-2.5-pro",
        "gemini-pro": "gemini-2.5-pro",
        "pro": "gemini-2.5-pro",
    }
    return alias_map.get(m, m)

def get_gemini_client():
    global _client, _cached_key
    api_key = get_env_var("GEMINI_API_KEY", "")
    if not api_key:
        return None, None
    if _client is None or _cached_key != api_key:
        from google import genai
        os.environ["GEMINI_API_KEY"] = api_key
        _client = genai.Client(api_key=api_key)
        _cached_key = api_key
    return _client, api_key

def llm(prompt):
    client, api_key = get_gemini_client()
    if not api_key:
        return None

    model_env = get_env_var("GEMINI_MODEL", "gemini-2.5-flash")
    primary_model = _normalize_model_name(model_env)

    # Fallback cascade in case the primary model is not accessible
    candidate_models = [primary_model]
    for fallback in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    last_error = None
    for model_name in candidate_models:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={'max_output_tokens': 5000}
            )
            output = res.text
            if not output:
                return '__ERROR__ Gemini returned an empty response. Check the model, request, or API availability.'
            return output
        except Exception as e:
            msg = str(e)
            if api_key:
                msg = msg.replace(api_key, '[API key hidden]')
            last_error = msg
            # If authentication failed definitively, report it immediately
            if any(term in msg.lower() for term in ["api_key_invalid", "unauthenticated", "permission denied", "forbidden", "401", "403"]):
                return f"__ERROR__ Gemini authentication failed: {msg}. Please check that GEMINI_API_KEY in .env is valid."
            # Otherwise try next fallback model (e.g. 404, not found, quota, etc.)
            continue

    return f'__ERROR__ Gemini request failed: {last_error}'


def _terms(text): return [x for x in re.findall(r'[a-zA-Z0-9-]{3,}',text.lower()) if x not in {'the','and','for','with','from','that','this','are','was','were','into','how','what'}]

def retrieve(question, document_ids=None, top_k=8):
    chunks=all_chunks(document_ids)
    if not chunks: return []
    # Semantic retrieval is preferred; lexical scoring keeps the app usable without a model download.
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        model=SentenceTransformer('all-MiniLM-L6-v2')
        vectors=model.encode([question]+[x['text'] for x in chunks],normalize_embeddings=True,show_progress_bar=False)
        try:
            import chromadb
            from .config import VECTOR_PATH
            client=chromadb.PersistentClient(path=str(VECTOR_PATH))
            collection=client.get_or_create_collection('research_passages')
            collection.upsert(ids=[str(x['id']) for x in chunks],documents=[x['text'] for x in chunks],
                embeddings=vectors[1:].tolist(),metadatas=[{'document_id':int(x['document_id']),'page':int(x['page'] or 0),'name':x['name'],'section':x.get('section') or ''} for x in chunks])
            result=collection.query(query_embeddings=[vectors[0].tolist()],n_results=min(top_k,len(chunks)),
                where={'document_id':{'$in':[int(x) for x in document_ids]}} if document_ids else None,include=['distances','ids'])
            rank={pid:1-float(dist) for pid,dist in zip(result['ids'][0],result['distances'][0])}
            scores=[rank.get(str(x['id']),-1.0) for x in chunks]
        except Exception:
            scores=cosine_similarity(vectors[:1],vectors[1:])[0]
    except Exception:
        q=Counter(_terms(question)); scores=[]
        for item in chunks:
            words=Counter(_terms(item['text'])); denom=sum(q.values()) or 1
            scores.append(sum(min(count,words[t]) for t,count in q.items())/denom + .12*sum(1 for t in q if t in words)/max(len(q),1))
    for item,score in zip(chunks,scores): item['score']=float(score)
    return sorted(chunks,key=lambda x:x['score'],reverse=True)[:top_k]

def plan_research(topic):
    prompt=f'''Create a concise research search plan for this topic: {topic!r}. Return 4 focused subquestions and 6 search keywords. Do not assert facts.'''
    answer=llm(prompt)
    if answer and not answer.startswith('__ERROR__'): return answer
    terms=_terms(topic); return 'Research plan\n1. Define the problem and scope.\n2. Identify common methods.\n3. Compare datasets and evaluation.\n4. Review limitations and open questions.\n\nSearch terms: '+', '.join(dict.fromkeys(terms[:8]))

def answer_question(question, document_ids=None):
    evidence=retrieve(question,document_ids,top_k=10)
    if not evidence: return {'answer':'No indexed passages are available. Upload research PDFs in Document Analysis first.','evidence':[],'plan':plan_research(question)}
    blocks=[]
    for i,x in enumerate(evidence,1): blocks.append(f"[E{i}] {x['name']} — p. {x['page'] or '?'} — {x['section'] or 'section not detected'}\n{x['text']}")
    prompt='''You are ResearchMate AI, an academic research assistant. Use only the evidence below. Every factual claim must have one or more inline citations in the form [E1]. Cite only the evidence IDs provided. Clearly say when evidence is insufficient. Separate reported source findings from your interpretation. Never invent references or results.\n\nQUESTION: '''+question+'\n\nEVIDENCE:\n'+'\n\n'.join(blocks)+'\n\nWrite a concise answer with a direct response, evidence-backed findings, caveats, and a short synthesis.'
    generated=llm(prompt)
    if generated and not generated.startswith('__ERROR__'): answer=generated
    else:
        err_msg = generated.replace('__ERROR__','',1).strip() if (generated and generated.startswith('__ERROR__')) else 'Gemini is not configured or unavailable.'
        # Grounded fallback: return the best matching passages without inventing synthesis.
        answer=f'> ⚠️ **Gemini Notice**: {err_msg}\n\nThe strongest matching source passages are listed below; review them to form a conclusion.'
        answer+='\n\n'+'\n\n'.join(f"[E{i}] **{x['name']}**, p. {x['page'] or '?'}: {x['text']}" for i,x in enumerate(evidence[:5],1))
    return {'answer':answer,'evidence':evidence,'plan':plan_research(question)}

def _paper_context(papers):
    return '\n\n'.join(f"PAPER {i+1}: {p.get('title')} ({p.get('year') or 'year n/a'}), {p.get('authors') or 'authors n/a'}\nAbstract: {p.get('abstract') or 'Abstract unavailable.'}\nURL: {p.get('url') or 'n/a'}" for i,p in enumerate(papers))

def structured_analysis(papers, task):
    if not papers: return 'Save papers to your library first.'
    text=llm(f'''You are an academic analysis agent. {task}\nOnly use information explicitly present in these records. Cite claims as [P1], [P2] using the paper numbers. Mark missing information as “Not reported in available abstract/metadata”. Distinguish evidence-based observations from hypotheses.\n\n{_paper_context(papers)}''')
    if text and not text.startswith('__ERROR__'): return text
    err_note = f"> ⚠️ **Gemini Notice**: {text.replace('__ERROR__','',1).strip()}\n\n" if (text and text.startswith('__ERROR__')) else ""
    rows=[]
    for i,p in enumerate(papers,1): rows.append(f"- [P{i}] **{p.get('title')}** ({p.get('year') or 'year n/a'})\n  Authors: {p.get('authors') or 'not listed'}\n  Abstract: {p.get('abstract') or 'Not reported.'}\n  DOI: {p.get('doi') or 'Not available'}")
    return (err_note + 'Gemini is not configured or unavailable; displaying source metadata without generated claims.\n\n'+'\n\n'.join(rows))

def make_report(question, papers, answer=None, comparison=None, gaps=None):
    citations='\n'.join(f"[{i}] {p.get('title')} — {p.get('authors') or 'authors not listed'} ({p.get('year') or 'year n/a'}). DOI: {p.get('doi') or 'not available'}. {p.get('url') or ''}" for i,p in enumerate(papers,1))
    prompt=f'''Draft a professional academic mini-review using ONLY the attached paper metadata/abstracts and evidence notes. Do not invent methods, outcomes, citations, or DOI. Use sections Introduction, Literature Review, Methodology Comparison, Findings, Research Gaps, Future Scope, References. Cite sources [P1] etc. Explicitly mark unsupported details “not available in supplied source metadata”. Separate observed gaps from hypotheses; do not claim novelty.\nTopic: {question}\nSources:\n{_paper_context(papers)}\nEvidence answer: {answer or 'Not generated'}\nComparison: {comparison or 'Not generated'}\nGaps: {gaps or 'Not generated'}'''
    body=llm(prompt)
    if not body or body.startswith('__ERROR__'):
        err_msg = body.replace('__ERROR__','',1).strip() if (body and body.startswith('__ERROR__')) else 'API key not configured or call failed.'
        body=f"# Research brief: {question}\n\n> ⚠️ **Gemini Notice**: {err_msg}\n\n## Introduction\nThis draft is based on {len(papers)} saved academic records. Configure Gemini to generate an evidence-based synthesis.\n\n## Literature Review\n{answer or 'No source-grounded answer generated yet.'}\n\n## Methodology Comparison\n{comparison or 'Generate a comparison in the Comparative Analysis section.'}\n\n## Findings\nReview the cited abstracts and uploaded documents before drawing conclusions.\n\n## Research Gaps\n{gaps or 'Generate gap analysis after reviewing a sufficiently broad set of papers.'}\n\n## Future Scope\nTreat proposed directions as hypotheses requiring further literature search.\n\n## References\n{citations}"
    verified_records='\n'.join(f"[P{i}] {p.get('title')} — {p.get('authors') or 'authors not listed'} ({p.get('year') or 'year n/a'}). DOI: {p.get('doi') or 'not available'}. Source: {p.get('url') or 'not available'}" for i,p in enumerate(papers,1))
    if papers: body += '\n\n## Verified source records\n'+verified_records
    return body
