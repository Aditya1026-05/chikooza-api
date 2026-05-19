# views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, status
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from .services import SQLAgentService, AISQLService
from .preprocessing import QueryPreprocessor
from .log_utils import ChatLogHandler
from .models import AIChatLog
import logging
import json
import uuid

logger = logging.getLogger(__name__)

class AIChatViewSet(viewsets.ViewSet):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preprocessor = QueryPreprocessor()
        self.log_handler = ChatLogHandler()

    def create(self, request):
        """Handle natural language queries"""
        try:
            raw_query = request.data.get("query", "").strip()
            if not raw_query:
                return Response(
                    {"error": "Query is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                query = self.preprocessor.preprocess(raw_query)
            except ValueError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            query_id = str(uuid.uuid4())
            request.chat_data = {
                'user_id': request.user.id,
                'raw_query': raw_query,
                'cleaned_query': query,
                'query_id': query_id
            }

            # service = SQLAgentService(user=request.user)
            service = AISQLService(user=request.user)
            result = service.query(query)
            
            self._log_interaction(request, result)
            self._save_to_db(request, result)

            if result["status"] == "error":
                return Response(
                    {
                        "error": result["message"],
                        "details": result.get("details"),
                        "suggestion": result.get("suggestion"),
                        "query_id": query_id
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            return Response(
                {
                    "status": "success",
                    "data": result["data"],
                    "query": result["query"],
                    "query_id": query_id
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Response(
                {"error": "Processing failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _log_interaction(self, request, result):
        log_data = {
            'user_id': request.user.id,
            'query': request.chat_data['cleaned_query'],
            'response': json.dumps(result),
            'status': result['status'],
            'query_id': request.chat_data['query_id']
        }
        self.log_handler.log_interaction(log_data)

    def _save_to_db(self, request, result):
        try:
            AIChatLog.objects.create(
                user=request.user,
                query=request.chat_data['cleaned_query'],
                response=json.dumps(result),
                query_id=request.chat_data['query_id']
            )
        except Exception as e:
            logger.error(f"Database save failed: {str(e)}")

    def list(self, request):
        try:
            chat_logs = AIChatLog.objects.filter(
                user=request.user
            ).order_by('-created_at')[:50]
            
            history = [{
                'id': log.id,
                'query': log.query,
                'response': self._parse_response(log.response),
                'created_at': log.created_at,
                'query_id': log.query_id
            } for log in chat_logs]
            
            return Response({'history': history}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"History retrieval failed: {str(e)}")
            return Response(
                {"error": "Failed to get history"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _parse_response(self, response_json):
        try:
            return json.loads(response_json)
        except:
            return {"status": "error", "message": "Invalid response format"}