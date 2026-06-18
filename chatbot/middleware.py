import time
import uuid

from .log_utils import ChatLogHandler


class LoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.log_handler = ChatLogHandler()

    def __call__(self, request):
        if not request.path.endswith("/chat/"):
            return self.get_response(request)

        request.query_id = str(uuid.uuid4())
        start_time = time.time()

        response = self.get_response(request)

        processing_time = time.time() - start_time

        log_data = {
            "query_id": request.query_id,
            "path": request.path,
            "method": request.method,
            "processing_time": processing_time,
            "status_code": response.status_code,
            "timestamp": time.time(),
        }

        if hasattr(request, "chat_data"):
            log_data.update(request.chat_data)

        self.log_handler.log_interaction(log_data)

        return response
