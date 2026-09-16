"""Current production retrieval defaults and real knowledge workflow, fixed corpus."""
import json, time, hashlib, statistics, math
from pathlib import Path
from scripts.evaluation.runtime import configure, real_router
configure(True)
from app.knowledge.ingest import ingest_builtin_knowledge, BUNDLE_PATH
from app.knowledge.retriever import retrieve
from app.agent.workflows import run_knowledge
from evals.run_rag_eval import _document_keys, _ranked_keys, _recall_at, _reference_coverage, _is_abstention

OUT=Path('evaluation/raw/rag.jsonl')
DATA=Path('evaluation/datasets/rag_v1.json')

def main():
    if OUT.exists(): raise RuntimeError('refusing overwrite; archive old run first')
    dataset=json.loads(DATA.read_text())
    with real_router() as router:
        db=router.db
        ingest_builtin_knowledge(db)
        keys=_document_keys(db)
        for case in dataset['cases']:
            t=time.perf_counter(); chunks=retrieve(db,case['question']); retrieval_ms=(time.perf_counter()-t)*1000
            start=time.perf_counter(); result=run_knowledge(db,router,case['question'],chunks_override=chunks)
            total_ms=retrieval_ms+(time.perf_counter()-start)*1000
            inv=result.invocation
            cited=[keys.get(c.document_id,c.document_id) for c in result.citations]
            relevant=set(case['expected_document_ids'])
            row={'id':case['id'],'question':case['question'],'should_abstain':case['should_abstain'], 'expected_document_ids':list(sorted(relevant)),
                'retrieved':_ranked_keys(chunks,keys),'recall':_recall_at(_ranked_keys(chunks,keys),relevant,3) if relevant else None,
                'answer':result.answer,'citations':cited,'citation_gold_matches':sum(c in relevant for c in cited),
                'abstained':_is_abstention(result.answer,len(cited)), 'reference_term_coverage':_reference_coverage(result.answer,case['reference_terms']) if relevant else None,
                'retrieval_ms':retrieval_ms,'total_ms':total_ms,'invocation':{k:getattr(inv,k) for k in ('provider','model','input_tokens','output_tokens','latency_ms','estimated_cost_usd','fallback_used','error_code')}}
            with OUT.open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
            print(case['id'], inv.error_code or 'ok',flush=True)
            db.rollback()
if __name__=='__main__':main()
