# log_utils.py
import json
import logging
import os
from datetime import datetime
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder


class ChatLogHandler:
    def __init__(self):
        self.logs_dir = os.path.join(settings.BASE_DIR, "aibot_logs")
        os.makedirs(self.logs_dir, exist_ok=True)

        self.logger = logging.getLogger("aibot")
        self.logger.setLevel(logging.INFO)

        # Create handlers if they don't exist
        if not self.logger.handlers:
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

            file_handler = logging.FileHandler(
                os.path.join(self.logs_dir, "system.log")
            )
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)

    def log_interaction(self, data):
        """Log complete interaction data to JSON file"""
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(self.logs_dir, f"interactions_{date_str}.json")

            # Add timestamp if not present
            if "timestamp" not in data:
                data["timestamp"] = datetime.now().isoformat()

            with open(log_file, "a") as f:
                f.write(json.dumps(data, cls=DjangoJSONEncoder) + "\n")

        except Exception as e:
            self.logger.error(f"Failed to write log: {str(e)}")
