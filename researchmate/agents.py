"""LangGraph coordinator for the research workflow, with a sequential fallback."""
from typing import TypedDict, Any
from .ai import plan_research, retrieve, llm

class State(TypedDict, total=False):
    question: str
    document_ids: list[int]
    plan: str
    evidence: list[dict[str, Any]]
    answer: str
    status: str

def _plan(s): return {'plan':plan_research(s['question'])}
def _retrieve(s): return {'evidence':retrieve(s['question'],s.get('document_ids'),10)}
def _synthesize(s):
    ev=s.get('evidence',[])
    if not ev: return {'answer':'No relevant passages found in the selected collection.','status':'insufficient_evidence'}
    ctx='\n'.join(f"[E{i}] {x['name']} p.{x['page']}: {x['text']}" for i,x in enumerate(ev,1))
    out=llm(f"Answer using only the passages below. Cite every factual claim as [E#]. Separate evidence from interpretation and state evidence gaps. Question: {s['question']}\n{ctx}")
    if not out or out.startswith('__ERROR__'):
        err_msg = f"\n\n> ⚠️ **Gemini Notice**: {out.replace('__ERROR__','',1).strip()}" if (out and out.startswith('__ERROR__')) else ""
        out=f'Evidence retrieved. Configure Gemini to synthesize; inspect the passage list and citations.{err_msg}'
    return {'answer':out,'status':'complete'}

def _verify(s):
    ev=s.get('evidence',[])
    ctx='\n'.join(f"[E{i}] {x['name']} p.{x['page']}: {x['text']}" for i,x in enumerate(ev,1))
    valid={f'E{i}' for i in range(1,len(ev)+1)}
    citations=set(__import__('re').findall(r'\[(E\d+)\]',s.get('answer','')))
    invalid=citations-valid
    if invalid: return {'answer':s['answer']+'\n\nCitation check: the draft included a reference to unavailable evidence; verify citations against the passage list.','status':'citation_review_needed'}
    if ev and not citations and not s.get('answer','').startswith('Evidence retrieved.'):
        return {'answer':s['answer']+'\n\nCitation check: no passage citations were detected. Treat factual statements as unverified and consult the evidence list.','status':'citation_review_needed'}
    audit=llm('''Act as a citation support critic. Review the answer against the supplied passages. Ensure each factual claim is actually supported by its cited passage ID, uses only valid passage IDs, and marks missing evidence as unknown. If a claim is unsupported, remove it or explicitly label it as uncertain. Return the corrected answer only; do not add sources.\n\nANSWER:\n'''+s.get('answer','')+'\n\nPASSAGES:\n'+ctx)
    if audit and not audit.startswith('__ERROR__'):
        if set(__import__('re').findall(r'\[(E\d+)\]',audit))-valid:
            return {'answer':s['answer']+'\n\nCitation check: the critic returned an unavailable evidence ID. Treat this draft as unverified and inspect the passages.','status':'citation_review_needed'}
        return {'answer':audit,'status':'citation_support_reviewed'}
    if not s.get('answer','').startswith('Evidence retrieved.'):
        return {'answer':s['answer']+'\n\nCitation check: passage IDs are valid. Semantic support review requires Gemini; inspect the cited passages before relying on the answer.','status':'citation_id_checked'}
    return {'status':'evidence_retrieved'}

def run_research_graph(question, document_ids=None):
    initial={'question':question,'document_ids':document_ids or []}
    try:
        from langgraph.graph import StateGraph, START, END
        graph=StateGraph(State); graph.add_node('plan',_plan); graph.add_node('retrieve',_retrieve); graph.add_node('synthesize',_synthesize); graph.add_node('citation_critic',_verify)
        graph.add_edge(START,'plan'); graph.add_edge('plan','retrieve'); graph.add_edge('retrieve','synthesize'); graph.add_edge('synthesize','citation_critic'); graph.add_edge('citation_critic',END)
        return graph.compile().invoke(initial)
    except ImportError:
        state={**initial,**_plan(initial)}; state.update(_retrieve(state)); state.update(_synthesize(state)); state.update(_verify(state)); return state
