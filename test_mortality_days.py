import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chikooza.settings")
django.setup()

from django.contrib.auth.models import User
from aibot.llm_sql import ChikoozaLLMTextToSQLService, EntityResolution

def run_test():
    try:
        user = User.objects.get(id=13)
    except User.DoesNotExist:
        user = User.objects.first()

    svc = ChikoozaLLMTextToSQLService(user)
    
    # Mock entity resolution to have complete (id=18) as active flock context
    class MockResolver:
        def resolve(self, question, history=None, active_context=None):
            res = EntityResolution(context="Active app flock context: flock_id=18\nResolved Flock: complete (flock_id=18)")
            object.__setattr__(res, 'resolved_flock_id', 18)
            object.__setattr__(res, 'resolved_farm_id', 17)
            return res

    svc.entity_resolver = MockResolver()
    
    history = [
        {"role": "user", "content": "Daily data for current flock"},
        {"role": "assistant", "content": "Here is the daily data...", "resolved_flock_id": 18, "resolved_farm_id": 17}
    ]

    print("\n--- TEST: lowest mortality is in which days? ---")
    try:
        res = svc.answer("lowest mortality is in which days?", history=history)
        print("SQL:", res.get("query"))
        print("Params:", res.get("params"))
        print("Answer:", res.get("answer"))
        print("Message:", res.get("message"))
        print("Error Details:", res.get("details"))
        print("Rows returned:", res.get("rows"))
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    run_test()
