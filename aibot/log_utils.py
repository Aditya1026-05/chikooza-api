# log_utils.py
import csv
import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder


class ChatLogHandler:
    def __init__(self):
        import sys
        self.logs_dir = os.path.join(settings.BASE_DIR, "aibot_logs")
        self.file_logging_enabled = os.getenv("AIBOT_FILE_LOGGING", "true").lower() in ("true", "1", "yes")

        self.system_logger = logging.getLogger("aibot_system")
        self.system_logger.setLevel(logging.INFO)

        # Clear existing handlers to prevent duplicates on module reload
        if self.system_logger.hasHandlers():
            self.system_logger.handlers.clear()

        # Shared formatter
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [farmer_ai] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # 1. Console Stream Handler (Stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.system_logger.addHandler(console_handler)

        # 2. Rotating File Handler
        if self.file_logging_enabled:
            os.makedirs(self.logs_dir, exist_ok=True)
            self.log_file = os.path.join(self.logs_dir, "system.log")
            file_handler = RotatingFileHandler(
                self.log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            self.system_logger.addHandler(file_handler)

    def log_interaction(self, log_data):
        """Log complete interaction data in human-readable console format, json, and csv"""
        try:
            # 1. Write Human-readable log
            self._write_readable_log(log_data)

            # 2. Write JSON and CSV logs
            if self.file_logging_enabled:
                self._write_json_log(log_data)
                self._write_csv_log(log_data)

        except Exception as e:
            self.system_logger.error(f"[ERROR] Failed to write log interaction: {str(e)}")

    def _write_readable_log(self, data):
        try:
            res = {}
            if "response" in data:
                try:
                    res = json.loads(data["response"])
                except Exception:
                    res = {"status": "error", "message": "Failed to parse response JSON"}

            # Extract key variables
            user_id = data.get("user_id", "unknown")
            query_id = data.get("query_id", "unknown")
            user_question = data.get("query", "")
            duration = data.get("duration")
            response_time = f"{round(duration, 4)}s" if duration is not None else "N/A"
            route = res.get("route", "unknown")
            metric = res.get("metric", "unspecified")
            engine = res.get("engine", "groq_sql")
            status = res.get("status", "success")

            # Structured block demarcation
            self.system_logger.info("============================================================")
            self.system_logger.info("                     FARMER AI INTERACTION                  ")
            self.system_logger.info("============================================================")

            # 1. Core Request & Performance Details
            self.system_logger.info(f"[USER QUESTION]   : \"{user_question}\"")
            self.system_logger.info(f"[RESPONSE TIME]   : {response_time}")
            self.system_logger.info(f"[DECIDED ROUTE]   : {route} (Metric: {metric} | Engine: {engine})")
            self.system_logger.info(f"[USER METADATA]   : User ID: {user_id} | Query ID: {query_id}")

            # 2. SQL Details (if applicable)
            sql = res.get("query")
            params = res.get("params", [])
            rows = res.get("rows", [])
            if sql:
                self.system_logger.info("")
                self.system_logger.info(f"[SQL QUERY]       : {sql}")
                self.system_logger.info(f"[SQL PARAMETERS]  : {params}")
                
                row_count = len(rows) if isinstance(rows, list) else 1 if rows else 0
                self.system_logger.info(f"[DB ROW COUNT]    : {row_count} row(s) returned")
                
                if isinstance(rows, list) and row_count > 0:
                    preview_count = min(row_count, 3)
                    self.system_logger.info(f"[DB ROW PREVIEW]  :")
                    for i in range(preview_count):
                        self.system_logger.info(f"  -> Row #{i+1}: {rows[i]}")

            # 3. Context Resolution Details
            resolved_farm = res.get("resolved_farm_id")
            resolved_flock = res.get("resolved_flock_id")
            entity_type = res.get("intent_entity_type")
            if resolved_farm or resolved_flock or entity_type:
                self.system_logger.info("")
                self.system_logger.info("[RESOLVED CONTEXT]:")
                self.system_logger.info(f"  - Farm ID       : {resolved_farm or 'None'}")
                self.system_logger.info(f"  - Flock ID      : {resolved_flock or 'None'}")
                self.system_logger.info(f"  - Entity Type   : {entity_type or 'None'}")

            # 4. Final Answer & Status
            answer = res.get("answer") or res.get("message") or ""
            self.system_logger.info("")
            self.system_logger.info(f"[STATUS]          : {status.upper()}")
            self.system_logger.info("[AI RESPONSE]     :")
            self.system_logger.info("------------------------------------------------------------")
            for line in answer.splitlines():
                self.system_logger.info(line)
            self.system_logger.info("------------------------------------------------------------")

            # 5. Error Logs (if applicable)
            if status == "error" or data.get("status") == "error":
                self.system_logger.error(f"[ERROR MESSAGE]   : {res.get('message', 'Unknown failure')}")
                if res.get("details"):
                    self.system_logger.error(f"[ERROR DETAILS]   : {res.get('details')}")

            self.system_logger.info("============================================================")

        except Exception as e:
            self.system_logger.error(f"[ERROR] Failed to write readable log: {str(e)}")

    def _write_json_log(self, data):
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(self.logs_dir, f"interactions_{date_str}.json")
            
            # Format logs to align structure with telemetry logging
            if "timestamp" not in data:
                data["timestamp"] = datetime.now().isoformat()
                
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, cls=DjangoJSONEncoder) + "\n")
        except Exception as e:
            self.system_logger.error(f"Failed to write JSON log: {str(e)}")

    def _write_csv_log(self, data):
        try:
            csv_file = os.path.join(self.logs_dir, "analytics.csv")
            file_exists = os.path.exists(csv_file)

            headers = [
                "Timestamp", "Request ID", "User ID", "User Query",
                "Route", "Metric", "Engine", "SQL Query", "SQL Params",
                "Rows Count", "Resolved Farm ID", "Resolved Flock ID",
                "Response Preview", "Response Time (s)", "Status"
            ]

            res = {}
            if "response" in data:
                try:
                    res = json.loads(data["response"])
                except Exception:
                    pass

            rows = res.get("rows", [])
            row_count = len(rows) if isinstance(rows, list) else 1 if rows else 0

            answer = res.get("answer") or res.get("message") or ""
            answer_preview = answer[:200] + "..." if len(answer) > 200 else answer

            duration = data.get("duration")
            resp_time = round(duration, 4) if duration is not None else ""

            row = {
                "Timestamp": data.get("timestamp", datetime.now().isoformat()),
                "Request ID": data.get("query_id", "unknown"),
                "User ID": data.get("user_id", "unknown"),
                "User Query": data.get("query", ""),
                "Route": res.get("route", "unknown"),
                "Metric": res.get("metric", "unspecified"),
                "Engine": res.get("engine", "groq_sql"),
                "SQL Query": res.get("query", ""),
                "SQL Params": str(res.get("params", [])),
                "Rows Count": row_count,
                "Resolved Farm ID": res.get("resolved_farm_id", ""),
                "Resolved Flock ID": res.get("resolved_flock_id", ""),
                "Response Preview": answer_preview,
                "Response Time (s)": resp_time,
                "Status": data.get("status", "success")
            }

            with open(csv_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
        except Exception as e:
            self.system_logger.error(f"Failed to write CSV log: {str(e)}")
