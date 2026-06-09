import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chikooza.settings")
django.setup()

from types import SimpleNamespace
from aibot.llm_sql import ChikoozaLLMTextToSQLService
from aibot.tests import _make_llm_service

def test():
    user = SimpleNamespace(id=7, is_authenticated=True)
    groq_responses = [
        '```json\n{"sql": "SELECT flock_id, flock_name FROM ai_farm_flock_data_view WHERE owner_id = %s LIMIT 1", "params": ["__OWNER_ID__"], "metric": "least_data", "result_type": "summary"}\n```',
        'The flock with the least data is "1" on "complet".',
        '```json\n{"sql": "SELECT flock_name FROM ai_farm_flock_data_view f WHERE owner_id = %s ORDER BY flock_name ASC", "params": ["__OWNER_ID__"], "metric": "least_data_all", "result_type": "table"}\n```',
        'Yes, flock 1 has the least data across all farms.',
    ]
    executor_data = [
        [{"flock_name": "1", "count": 0, "farm_id": 99}],
        [{"flock_name": "1", "count": 0}, {"flock_name": "2", "count": 5}]
    ]
    
    svc = _make_llm_service(user, groq_responses=groq_responses)
    svc.executor.execute = lambda plan: executor_data.pop(0)
    history = []

    res1 = svc.answer("now tell me the flock with least data", history=history)
    print("RES1:", res1)
    
    history.append({"role": "user", "content": "now tell me the flock with least data"})
    history.append({"role": "assistant", "content": res1["message"]})
    
    res2 = svc.answer("in all the farms this is the one with least data?", history=history)
    print("RES2:", res2)

if __name__ == "__main__":
    test()
