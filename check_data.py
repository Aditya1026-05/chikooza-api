import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chikooza.settings")
django.setup()

from django.db import connection

def check_data():
    with connection.cursor() as cursor:
        print("--- Farm Flock Count ---")
        cursor.execute("""
            SELECT farm_name, COUNT(*) as c
            FROM ai_farm_flock_data_view 
            WHERE owner_id = 7 
            GROUP BY farm_name 
            ORDER BY c ASC
        """)
        for row in cursor.fetchall():
            print(row)
            
        print("\n--- Daily Data Count ---")
        cursor.execute("""
            SELECT farm_name, COUNT(*) as c
            FROM ai_dailydata_data_view 
            WHERE owner_id = 7 
            GROUP BY farm_name 
            ORDER BY c ASC
        """)
        for row in cursor.fetchall():
            print(row)

if __name__ == "__main__":
    check_data()
