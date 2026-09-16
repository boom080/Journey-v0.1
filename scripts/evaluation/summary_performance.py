"""Twenty uncached current 30-day summary service calls on a fixed synthetic week."""
import json,time
from pathlib import Path
from datetime import datetime,UTC,timedelta
from unittest.mock import patch
from scripts.evaluation.runtime import configure,real_router
configure(True)
from sqlalchemy import delete
from app.models.user import User
from app.models.profile import Profile
from app.models.food_record import FoodRecord
from app.models.agent import AgentSummaryCache
from app.services.agent_summary import generate_summary
class FrozenDatetime(datetime):
    @classmethod
    def now(cls,tz=None):return cls(2026,9,11,4,0,tzinfo=UTC).astimezone(tz) if tz else cls(2026,9,11,4,0)
def main():
    out=Path('evaluation/raw/summary-performance.jsonl')
    if out.exists():raise RuntimeError('refusing overwrite')
    with real_router('00000000-0000-4000-8000-000000000092') as router:
        db=router.db;user=db.get(User,router.user_id)
        if db.get(Profile,user.id) is None: db.add(Profile(user_id=user.id,display_name='Synthetic',timezone='Asia/Shanghai'))
        db.execute(delete(FoodRecord).where(FoodRecord.user_id==user.id))
        for i in range(7):
            at=FrozenDatetime.now(UTC)-timedelta(days=i)
            db.add(FoodRecord(user_id=user.id,recorded_at=at,record_date=at.date(),meal_type='lunch',name='测试餐',energy_kcal=500,source='manual'))
        db.commit()
        original=router.generate;observed=[]
        def measured(*args,**kwargs):
            result=original(*args,**kwargs);observed.append(result);return result
        router.generate=measured
        for i in range(20):
            db.execute(delete(AgentSummaryCache).where(AgentSummaryCache.user_id==user.id));db.commit()
            start=time.perf_counter()
            with patch('app.services.agent_summary.datetime',FrozenDatetime):
                result=generate_summary(db,user,period_days=30,request_id=f'eval-summary-{i}',model_router=router)
            inv=observed[-1]
            row={'index':i,'total_ms':(time.perf_counter()-start)*1000,'cache_hit':result.cache_hit,'result':result.model_dump(mode='json'),'invocation':{k:getattr(inv,k) for k in ('provider','model','input_tokens','output_tokens','latency_ms','estimated_cost_usd','fallback_used','error_code')}}
            with out.open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
            print(i,inv.error_code or 'ok',flush=True)
if __name__=='__main__':main()
