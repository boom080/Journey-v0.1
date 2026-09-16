"""Sequential API fault/replay scenarios, actual PostgreSQL row assertions."""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from scripts.evaluation.runtime import configure
configure(False)
from app.main import app
from app.core.database import SessionLocal
from app.models.food_record import FoodRecord

@pytest.mark.parametrize('scenario', ['normal', 'edited', 'double_click', 'retry', 'lost_response', 'same_task'])
def test_confirmation(scenario):
    with TestClient(app) as client:
        payload = dict(email=f'eval-{scenario}@example.com', username=f'eval_{scenario}', password='EvalPassword2026', display_name='Synthetic Evaluation')
        register = client.post('/api/v1/auth/register', json=payload)
        assert register.status_code == 201, register.text
        headers = {'Authorization': 'Bearer '+register.json()['access_token']}
        run = client.post('/api/v1/agent/runs', headers=headers, json={'message':'午餐吃了鸡肉饭 520 千卡'})
        assert run.status_code == 200, run.text
        candidate = run.json()['candidates'][0]
        with SessionLocal() as db:
            before = db.query(FoodRecord).count()
        body = {k:candidate[k] for k in ('confirmation_token','kind','payload')}
        body['payload']['recorded_at']='2026-09-11T04:00:00Z'
        if scenario == 'edited': body['payload']['energy_kcal']=420
        path='/api/v1/agent/confirmations/'+candidate['candidate_id']
        first = client.post(path, headers={**headers,'Idempotency-Key':'eval-'+scenario}, json=body)
        assert first.status_code == 201, first.text
        repeated = None
        if scenario not in ('normal','edited'):
            # lost_response intentionally discards the first response at the client seam.
            key='different-task-key' if scenario == 'same_task' else 'eval-'+scenario
            repeated=client.post(path,headers={**headers,'Idempotency-Key':key},json=body)
            assert repeated.status_code == (409 if scenario == 'same_task' else 201), repeated.text
            if scenario != 'same_task': assert repeated.json()['record']['id']==first.json()['record']['id']
        with SessionLocal() as db:
            after=db.query(FoodRecord).count()
            record=db.get(FoodRecord, __import__('uuid').UUID(first.json()['record']['id']))
            assert record.energy_kcal == (420 if scenario=='edited' else 520)
        result={'scenario':scenario,'rows_before':before,'rows_after':after,'extra_rows':max(0,after-before-1),'status':first.status_code,'replay_status':repeated.status_code if repeated is not None else None}
        with Path('evaluation/raw/reliability.jsonl').open('a') as f: f.write(json.dumps(result)+'\n')
        assert after-before == 1

def test_same_run_request_reexecuted():
    with TestClient(app) as client:
        register=client.post('/api/v1/auth/register',json=dict(email='eval-run-retry@example.com',username='eval_run_retry',password='EvalPassword2026',display_name='Synthetic Evaluation'))
        assert register.status_code==201,register.text
        headers={'Authorization':'Bearer '+register.json()['access_token'],'Idempotency-Key':'same-run-request'}
        runs=[client.post('/api/v1/agent/runs',headers=headers,json={'message':'午餐吃了鸡肉饭 520 千卡'}) for _ in range(2)]
        assert all(r.status_code==200 for r in runs)
        with SessionLocal() as db:before=db.query(FoodRecord).count()
        statuses=[]
        for i,r in enumerate(runs):
            candidate=r.json()['candidates'][0]
            body={k:candidate[k] for k in ('confirmation_token','kind','payload')}
            body['payload']['recorded_at']='2026-09-11T04:00:00Z'
            response=client.post('/api/v1/agent/confirmations/'+candidate['candidate_id'],headers={**headers,'Idempotency-Key':f'run-confirm-{i}'},json=body)
            statuses.append(response.status_code)
        with SessionLocal() as db:after=db.query(FoodRecord).count()
        row={'scenario':'same_run_request_reexecuted','rows_before':before,'rows_after':after,'extra_rows':max(0,after-before-1),'run_ids':[r.json()['run_id'] for r in runs],'confirmation_statuses':statuses}
        with Path('evaluation/raw/reliability.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        assert after-before==1, 'same run submission generated duplicate logical food records'
