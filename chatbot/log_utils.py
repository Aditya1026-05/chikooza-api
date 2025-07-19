#MV-2025-07-04-<8>  STARTS
import json
import logging
import os
from datetime import datetime
from django.conf import settings

class ChatLogHandler:
    def __init__(self):
        self.logs_dir = os.path.join(settings.BASE_DIR, 'chatbot_logs')
        os.makedirs(self.logs_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(self.logs_dir, 'system.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('chatbot')

    def log_interaction(self, data):
        """Log complete interaction data to JSON file"""
        try:
            date_str = datetime.now().strftime('%Y-%m-%d')
            log_file = os.path.join(self.logs_dir, f'interactions_{date_str}.json')
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(data) + '\n')
                
            self.logger.info(f"Logged interaction: {data.get('query_id', '')}")
            
        except Exception as e:
            self.logger.error(f"Failed to write log: {str(e)}")

    def get_logs(self, date=None):
        """Retrieve logs for a specific date"""
        date_str = date or datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(self.logs_dir, f'interactions_{date_str}.json')
        
        if not os.path.exists(log_file):
            return []
            
        with open(log_file, 'r') as f:
            return [json.loads(line) for line in f.readlines()]
#MV-2025-07-04-<8>  ENDS