import hashlib,json,platform,subprocess,sys
from pathlib import Path
from scripts.evaluation.runtime import configure
s=configure(True)
paths=[]
for folder in ['backend/app','backend/alembic','backend/tests','apps/mobile/src','apps/mobile/tests','evals/datasets','scripts/evaluation','evaluation/datasets']:
 paths.extend(p for p in Path(folder).rglob('*') if p.is_file() and '__pycache__' not in str(p))
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
manifest={'version':'resume-evaluation-v1','python':sys.version,'platform':platform.platform(),'node':subprocess.check_output(['node','--version'],text=True).strip(),'git_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_sha256':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest(),'files':hashes,'provider':s.agent_provider,'model':s.agent_default_model,'model_map':s.agent_model_map,'temperature':0,'max_output_tokens':s.agent_max_output_tokens,'timeout_seconds':s.agent_timeout_seconds,'retries':s.agent_max_retries,'configured_pricing_usd_per_million':s.agent_model_pricing,'default_rates':[s.agent_input_usd_per_million,s.agent_output_usd_per_million],'database':'isolated PostgreSQL 18.6, 127.0.0.1:55439, journey_resume_eval','gold_status':'agent_authored_pending_human_review','random_seed':'no dataset randomness; provider seed unsupported/not set; temperature 0 does not guarantee bitwise repeatability'}
Path('evaluation/raw/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
