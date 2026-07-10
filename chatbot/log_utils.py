import csv
import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from django.conf import settings


class ChatLogHandler:
    def __init__(self):
        import sys
        self.logs_dir = os.path.join(settings.BASE_DIR, "chatbot_logs")
        self.file_logging_enabled = os.getenv("CHIKBOT_FILE_LOGGING", "true").lower() in ("true", "1", "yes")

        self.system_logger = logging.getLogger("chikbot_system")
        self.system_logger.setLevel(logging.INFO)
        
        # Clear existing handlers to prevent duplicates on module reload
        if self.system_logger.hasHandlers():
            self.system_logger.handlers.clear()

        # Shared formatter
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] [chikbot] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        # 1. Always write to Console stdout (Terminal output)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.system_logger.addHandler(console_handler)

        # 2. Add Rotating File Logger only if file logging is enabled
        if self.file_logging_enabled:
            os.makedirs(self.logs_dir, exist_ok=True)
            self.log_file = os.path.join(self.logs_dir, "system.log")
            file_handler = RotatingFileHandler(
                self.log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            self.system_logger.addHandler(file_handler)

    def log_interaction(self, log_data):
        """Log a chatbot interaction in console/terminal, and optional file formats."""
        # Ensure we have clean metrics dictionary
        metrics = log_data.get("metrics")
        if not metrics:
            # Fallback wrapper if metrics not directly present in telemetry data
            metrics = self._build_fallback_metrics(log_data)

        # 1. Write Human-readable log (always logged to console/terminal via stdout)
        self._write_readable_log(metrics)

        # 2. Write JSON and CSV logs only if file logging is enabled
        if self.file_logging_enabled:
            self._write_json_log(metrics)
            self._write_csv_log(metrics)

    def _write_readable_log(self, m):
        try:
            req_id = m.get("request_id")
            timings = m.get("timings", {})
            errors = m.get("errors", {})

            # Start demarcation
            self.system_logger.info("--- NEW CHATBOT QUERY ---")

            # 1. Log Request info
            self.system_logger.info(
                f"[REQUEST] Query: \"{m.get('original_question')}\" | User ID: {m.get('user_id')} | Session ID: {m.get('conversation_id')} | Request ID: {req_id}"
            )

            # 2. Log Retrieval details
            chunks = m.get("retrieved_chunks", [])
            self.system_logger.info(
                f"[RETRIEVAL] Model: {m.get('embedding_model')} | Vector DB: {m.get('vector_database')} | "
                f"Requested Top-K: {m.get('top_k_requested')} | Returned: {m.get('top_k_returned')} chunks"
            )
            for i, c in enumerate(chunks, 1):
                self.system_logger.info(
                    f"[RETRIEVAL]   -> Chunk #{c.get('chunk_id')} | Score: {c.get('similarity_score')} | "
                    f"Document: {c.get('document_name')} | Page: {c.get('page_number')} | Used in Prompt: {'Yes' if c.get('was_used') else 'No'}"
                )

            # 3. Log LLM details
            self.system_logger.info(
                f"[LLM CALL] Provider: {m.get('provider')} | Model: {m.get('model')} | Temperature: {m.get('temperature')} | "
                f"Tokens: {m.get('prompt_tokens')} input / {m.get('completion_tokens')} output ({m.get('total_tokens')} total) | "
                f"Cost: ${round(m.get('estimated_cost', 0), 6)}"
            )

            # 4. Log Response & Citations
            answer_preview = m.get('final_answer', '')
            if len(answer_preview) > 300:
                answer_preview = answer_preview[:300] + "..."
            self.system_logger.info(f"[RESPONSE] Answer: \"{answer_preview}\"")
            
            citations = m.get("citations", [])
            if citations:
                self.system_logger.info("[RESPONSE] Citations:")
                for c in citations:
                    self.system_logger.info(
                        f"  - Document: {c.get('document_name')} | Page: {c.get('page_number')} | Chunk ID: {c.get('chunk_id')}"
                    )
            else:
                self.system_logger.info("[RESPONSE] Citations: None")

            # 5. Log Performance timings summary
            self.system_logger.info(
                f"[PERFORMANCE] Total Time: {round(timings.get('total_time', 0), 4)}s ("
                f"Embedding: {round(timings.get('embedding_time', 0), 4)}s | "
                f"DB Query: {round(timings.get('retrieval_time', 0), 4)}s | "
                f"Prompt Construction: {round(timings.get('prompt_construction_time', 0), 4)}s | "
                f"LLM Generation: {round(timings.get('llm_generation_time', 0), 4)}s | "
                f"Post-process: {round(timings.get('post_processing_time', 0), 4)}s)"
            )

            # 6. Log Errors if present
            if m.get("status") == "Failed" or errors:
                self.system_logger.error(
                    f"[ERROR] Request ID: {req_id} | Type: {errors.get('type')} | Message: {errors.get('message')}"
                )
                if errors.get("stack_trace"):
                    self.system_logger.error(f"[ERROR_STACK] {errors.get('stack_trace')}")
            
            # End demarcation
            self.system_logger.info("--------------------------")
                    
        except Exception as e:
            self.system_logger.error(f"[ERROR] Failed to write readable log: {str(e)}")

    def _write_json_log(self, m):
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(self.logs_dir, f"interactions_{date_str}.json")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(m) + "\n")
        except Exception as e:
            self.system_logger.error(f"Failed to write JSON log: {str(e)}")

    def _write_csv_log(self, m):
        try:
            csv_file = os.path.join(self.logs_dir, "analytics.csv")
            file_exists = os.path.exists(csv_file)
            
            headers = [
                "Request ID", "Conversation ID", "User ID", "Question Timestamp", "Answer Timestamp",
                "Original Question", "Processed Question", "Intent", "Model", "Embedding Model",
                "Top-K", "Retrieved Documents", "Retrieved Chunk IDs", "Similarity Scores",
                "Documents Used", "Pages Used", "Prompt Tokens", "Completion Tokens", "Total Tokens",
                "Estimated Cost", "Total Response Time", "Status"
            ]

            # Flatten multi-valued attributes into lists for CSV format
            retrieved_chunks = m.get("retrieved_chunks", [])
            ret_docs = ",".join(list(set([c.get("document_name") for c in retrieved_chunks if c.get("document_name")])))
            ret_chunk_ids = ",".join([str(c.get("chunk_id")) for c in retrieved_chunks if c.get("chunk_id") is not None])
            ret_scores = ",".join([str(c.get("similarity_score")) for c in retrieved_chunks if c.get("similarity_score") is not None])
            
            docs_used = ",".join(list(set([c.get("document_name") for c in retrieved_chunks if c.get("was_used")])))
            pages_used = ",".join(list(set([str(c.get("page_number")) for c in retrieved_chunks if c.get("was_used") and c.get("page_number") is not None])))

            row = {
                "Request ID": m.get("request_id"),
                "Conversation ID": m.get("conversation_id"),
                "User ID": m.get("user_id"),
                "Question Timestamp": m.get("question_timestamp"),
                "Answer Timestamp": m.get("answer_timestamp"),
                "Original Question": m.get("original_question"),
                "Processed Question": m.get("processed_question"),
                "Intent": m.get("intent", "qa"),
                "Model": m.get("model"),
                "Embedding Model": m.get("embedding_model"),
                "Top-K": m.get("top_k_requested"),
                "Retrieved Documents": ret_docs,
                "Retrieved Chunk IDs": ret_chunk_ids,
                "Similarity Scores": ret_scores,
                "Documents Used": docs_used,
                "Pages Used": pages_used,
                "Prompt Tokens": m.get("prompt_tokens"),
                "Completion Tokens": m.get("completion_tokens"),
                "Total Tokens": m.get("total_tokens"),
                "Estimated Cost": m.get("estimated_cost"),
                "Total Response Time": m.get("total_response_time"),
                "Status": m.get("status")
            }

            with open(csv_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
        except Exception as e:
            self.system_logger.error(f"Failed to write CSV log: {str(e)}")

    def _build_fallback_metrics(self, data):
        now_str = datetime.utcnow().isoformat() + "Z"
        return {
            "request_id": data.get("query_id", "unknown"),
            "conversation_id": data.get("session_id", "unknown"),
            "session_id": data.get("session_id", "unknown"),
            "user_id": "anonymous",
            "question_timestamp": now_str,
            "answer_timestamp": now_str,
            "original_question": data.get("query", ""),
            "processed_question": data.get("query", ""),
            "language": "en",
            "intent": "qa",
            "embedding_model": "unknown",
            "embedding_time": 0.0,
            "vector_database": "unknown",
            "collection_namespace": "unknown",
            "top_k_requested": 5,
            "top_k_returned": 0,
            "retrieved_chunks": [],
            "context_chunk_ids": [],
            "context_tokens": 0,
            "provider": data.get("provider", "unknown"),
            "model": data.get("model", "unknown"),
            "temperature": 0.0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0,
            "status": "Success" if data.get("status_code", 200) < 400 else "Failed",
            "final_answer": data.get("response", ""),
            "citations": [],
            "timings": {
                "embedding_time": 0.0,
                "retrieval_time": 0.0,
                "prompt_construction_time": 0.0,
                "llm_generation_time": 0.0,
                "post_processing_time": 0.0,
                "total_time": data.get("processing_time", 0.0)
            },
            "total_response_time": data.get("processing_time", 0.0),
            "errors": {}
        }

    def get_logs(self, date=None):
        """Return interaction logs for a specific date."""
        date_str = date or datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.logs_dir, f"interactions_{date_str}.json")

        if not os.path.exists(log_file):
            return []

        with open(log_file, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f.readlines()]
