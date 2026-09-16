"""Aggregate saved evidence only; null means unavailable, never invented zero."""
import csv,json,statistics,math,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,UTC
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'evaluation/raw'
def lines(name):
 p=RAW/name
 return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []
def junit(name):
 root=ET.parse(RAW/name).getroot(); cases=list(root.iter('testcase'))
 return {'total':len(cases),'passed':sum(not any(c.find(k) is not None for k in ('failure','error','skipped')) for c in cases),'failed':sum(c.find('failure') is not None for c in cases),'errors':sum(c.find('error') is not None for c in cases),'skipped':sum(c.find('skipped') is not None for c in cases),'failures':[{'name':c.attrib.get('name'),'message':(c.find('failure') if c.find('failure') is not None else c.find('error')).attrib.get('message')} for c in cases if c.find('failure') is not None or c.find('error') is not None]}
def performance(rows,field='total_ms'):
 if not rows:return None
 times=sorted(r[field] for r in rows)
 good=[r for r in rows if not r['invocation']['fallback_used'] and r['invocation']['error_code'] is None]
 return {'tasks':len(rows),'successful_model_calls':len(good),'mean_ms':statistics.mean(times),'p50_ms':statistics.median(times),'p95_ms':times[math.ceil(.95*len(times))-1],'mean_input_tokens_per_task':statistics.mean(r['invocation']['input_tokens'] for r in rows),'mean_output_tokens_per_task':statistics.mean(r['invocation']['output_tokens'] for r in rows),'mean_configured_cost_usd_per_task':statistics.mean(r['invocation']['estimated_cost_usd'] for r in rows),'cost_cny':None,'actual_billed_cost':None}
def main():
 rag=lines('rag.jsonl');rel=lines('reliability.jsonl');summary=lines('summary-performance.jsonl')
 mobile=json.loads((RAW/'mobile.json').read_text())
 tests={'backend':junit('backend.xml'),'mobile_components':{'total':mobile['numTotalTests'],'passed':mobile['numPassedTests'],'failed':mobile['numFailedTests']}}
 log=(RAW/'mobile-logic.log').read_text()
 import re
 tests['mobile_logic']={k:int(re.search(r'# '+label+r' (\d+)',log).group(1)) for k,label in [('total','tests'),('passed','pass'),('failed','fail')]}
 if (RAW/'reliability-all.xml').exists():tests['reliability']=junit('reliability-all.xml')
 else:
  tests['reliability']=junit('reliability.xml');tests['run_reexecution']=junit('run-reexecution.xml')
 answerable=[r for r in rag if not r['should_abstain']];unanswerable=[r for r in rag if r['should_abstain']]
 metrics=[]
 def add(section,name,value,n,d,formula,note=''):
  metrics.append(dict(section=section,metric=name,value=value,numerator=n,denominator=d,formula=formula,note=note))
 total=sum(x['total'] for x in tests.values());passed=sum(x['passed'] for x in tests.values())
 add('tests','executed_tests',total,None,None,'count(testcase); repeated environment-debug runs excluded')
 add('tests','pass_rate',passed/total,passed,total,'passed / executed incl failure and error','Mixed unit/component/API tests; not all browser E2E')
 add('reliability','write_success_rate',sum(r['rows_after']>r['rows_before'] for r in rel)/len(rel),sum(r['rows_after']>r['rows_before'] for r in rel),len(rel),'scenarios with at least one write / scenarios','At least one write does not imply exactly once')
 add('reliability','exactly_once_rate',sum(r['rows_after']-r['rows_before']==1 for r in rel)/len(rel),sum(r['rows_after']-r['rows_before']==1 for r in rel),len(rel),'scenarios with exactly one new row / scenarios')
 add('reliability','excess_duplicate_rows',sum(r['extra_rows'] for r in rel),None,None,'sum(max(new_rows - 1,0))')
 idem=[r for r in rel if r['scenario'] not in ('normal','edited')]
 add('reliability','idempotency_rate',sum(r['extra_rows']==0 for r in idem)/len(idem),sum(r['extra_rows']==0 for r in idem),len(idem),'replay scenarios with exactly-once outcome / replay scenarios')
 recovery=[r for r in rel if r['scenario'] in ('retry','lost_response')]
 add('reliability','simulated_recovery_rate',sum(r['extra_rows']==0 for r in recovery)/len(recovery),sum(r['extra_rows']==0 for r in recovery),len(recovery),'successful sequential retry/lost-response recovery / simulated recovery scenarios','No physical network fault or process restart')
 add('rag','question_count',len(rag),None,None,'count(executed questions)')
 add('rag','macro_recall_at_3',statistics.mean(r['recall'] for r in answerable),None,len(answerable),'mean(|top3 docs intersect gold docs| / |gold docs|)','Existing gold pending human review')
 add('rag','gold_document_citation_membership',sum(r['citation_gold_matches'] for r in answerable)/sum(len(r['citations']) for r in answerable),sum(r['citation_gold_matches'] for r in answerable),sum(len(r['citations']) for r in answerable),'gold-matching citations / emitted citations on answerable questions','Proxy; valid extra documents can be penalized; not semantic citation correctness')
 add('rag','reference_term_full_coverage_rate',sum(r['reference_term_coverage']==1 for r in answerable)/len(answerable),sum(r['reference_term_coverage']==1 for r in answerable),len(answerable),'answers covering every reference term group / answerable questions','Lexical proxy, not human answer correctness')
 add('rag','unanswerable_abstention_marker_rate',sum(r['abstained'] for r in unanswerable)/len(unanswerable),sum(r['abstained'] for r in unanswerable),len(unanswerable),'unanswerable cases matching refusal markers / unanswerable cases','Includes retrieval-level no-context refusal')
 add('rag','unanswerable_nonabstention_proxy',sum(not r['abstained'] for r in unanswerable)/len(unanswerable),sum(not r['abstained'] for r in unanswerable),len(unanswerable),'unanswerable cases without refusal marker / unanswerable cases','Not a measured semantic hallucination rate')
 for name in ['semantic_citation_correctness','citation_answer_consistency','human_answer_correctness','semantic_hallucination_rate']:
  add('rag',name,None,None,None,'human approved labels / applicable cases','当前无法测量：缺逐题人工语义审核标签')
 add('rag','mean_retrieval_ms',statistics.mean(r['retrieval_ms'] for r in rag),None,len(rag),'sum(retrieval_ms) / questions')
 perf={'rag_workflow':performance(rag),'thirty_day_summary_uncached':performance(summary)}
 parsing_path=RAW/'parsing-summary.json'
 parsing=json.loads(parsing_path.read_text()) if parsing_path.exists() else None
 if parsing:
  parsing_rows=lines('parsing.jsonl')
  parsing_latencies=[row['latency_ms'] for row in parsing_rows]
  add('parsing','sample_count',parsing['dataset']['cases'],None,None,'count(executed fixed cases)','Gold labels are pending human review')
  add('parsing','case_pass_rate',parsing['metrics']['case_pass_rate']['rate'],parsing['metrics']['case_pass_rate']['passed'],parsing['metrics']['case_pass_rate']['completed'],'passed case / executed cases','Pending human review')
  route=parsing['metrics']['route_intents_exact']
  add('parsing','intent_exact_rate',route['exact'],route['matched'],route['scored'],'exact intent matches / scored cases','Pending human review')
  for kind, fields in parsing['metrics'].items():
   if kind not in ('food','activity'):
    continue
   for field, metric in fields.items():
    add('parsing.'+kind,field+'_exact_rate',metric['exact'],metric['matched'],metric['scored'],'exact matches / explicitly scorable fields','Pending human review; null means no scorable sample')
  invocations=parsing['counts']['invocations']
  add('parsing','model_invocation_success_rate',(invocations-parsing['counts']['fallback_invocations'])/invocations,invocations-parsing['counts']['fallback_invocations'],invocations,'non-fallback invocations / all invocations','Availability measure, not semantic correctness')
  perf['health_parsing_case']={
   'tasks': parsing['dataset']['cases'],
   'mean_ms': statistics.mean(parsing_latencies),
   'p50_ms': parsing['usage']['latency_p50_ms'],
   'p95_ms': parsing['usage']['latency_p95_ms'],
   'mean_input_tokens_per_task': parsing['usage']['input_tokens']/parsing['dataset']['cases'],
   'mean_output_tokens_per_task': parsing['usage']['output_tokens']/parsing['dataset']['cases'],
   'mean_configured_cost_usd_per_task': parsing['usage']['estimated_cost_usd']/parsing['dataset']['cases'],
   'cost_cny': None,
   'actual_billed_cost': None,
  }
 for feature,p in perf.items():
  for key,val in p.items():
   if key not in ('tasks','successful_model_calls'):add('performance.'+feature,key,val,None,p['tasks'],'see performance definitions', 'configured USD estimates are not billing; CNY unavailable' if 'cost' in key else '')
 inventory=json.loads((RAW/'history-inventory.json').read_text()) if (RAW/'history-inventory.json').exists() else None
 result={'evaluation_version':'journey-resume-v1','generated_at':datetime.now(UTC).isoformat(),'environment':json.loads((RAW/'manifest.json').read_text()),'gold_status':'pending_human_review','metrics':metrics,'tests':tests,'reliability':rel,'database_audit':json.loads((RAW/'database-audit.json').read_text()),'rag':{'questions':len(rag),'answerable':len(answerable),'unanswerable':len(unanswerable),'fallbacks':sum(r['invocation']['fallback_used'] for r in rag),'failures_proxy':[r['id'] for r in answerable if r['reference_term_coverage']<1]},'parsing':parsing,'performance':perf,'history':inventory}
 (ROOT/'evaluation/results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 with (ROOT/'evaluation/summary.csv').open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=['section','metric','value','numerator','denominator','formula','note']);writer.writeheader();writer.writerows(metrics)
 print(json.dumps({'tests':total,'passed':passed,'rag':len(rag),'reliability':len(rel)},ensure_ascii=False))
if __name__=='__main__':main()
