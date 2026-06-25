import json
import time
import uuid

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import ChatLog
from .preprocessing import QueryPreprocessor
from .rag_assistant import RAGAssistantService

# The RAG assistant is created lazily so Django can start without loading
# embedding or LLM resources during import.
rag_assistant = None
preprocessor = QueryPreprocessor()


def get_rag_assistant():
    global rag_assistant
    if rag_assistant is None:
        rag_assistant = RAGAssistantService()
    return rag_assistant


@csrf_exempt
def chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        query_text = data.get("query", "").strip()
        chat_history = data.get("history", [])
        if not isinstance(chat_history, list):
            chat_history = []
        session_id = data.get("session_id") or data.get("conversation_id")
        prompt_type = data.get("prompt_type", "qa")
        chat_mode = (
            data.get("mode") or data.get("assistant") or data.get("chat_mode") or "rag"
        )
        chat_mode = str(chat_mode).strip().lower()

        if not query_text:
            return JsonResponse({"error": "Query is required"}, status=400)

        clean_query = preprocessor.preprocess(query_text)

        start_time = time.time()

        if chat_mode not in {"rag", "knowledge"}:
            return JsonResponse({"error": "Unsupported chat mode"}, status=400)

        assistant = get_rag_assistant()
        assistant_result = assistant.answer(
            clean_query,
            user=request.user,
            session_id=session_id,
            client_history=chat_history,
        )
        result = {
            "result": assistant_result.result,
            "source_documents": [],
            "sources": assistant_result.sources,
            "provider": assistant_result.provider,
            "model": assistant_result.model,
            "fallback": assistant_result.fallback,
            "display": assistant_result.display,
            "session_id": assistant_result.session_id,
        }

        processing_time = time.time() - start_time

        if not result:
            return JsonResponse({"error": "Failed to process query"}, status=500)

        source_docs = result.get("source_documents", result.get("context", []))

        serializable_context = []
        for doc in source_docs:
            serializable_context.append(
                {
                    "page_content": getattr(doc, "page_content", str(doc)),
                    "metadata": getattr(doc, "metadata", {}),
                }
            )

        chat_log = ChatLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            query=clean_query,
            response=result["result"],
            query_id=getattr(request, "query_id", str(uuid.uuid4())),
        )

        request.chat_data = {
            "query": clean_query,
            "response": result["result"],
            "context": serializable_context,
            "prompt_type": prompt_type,
            "processing_time": processing_time,
            "mode": chat_mode,
            "session_id": result.get("session_id"),
            "provider": result.get("provider", "unknown"),
            "model": result.get("model", "unknown"),
            "fallback": result.get("fallback", False),
            "sources": result.get("sources", []),
            "display": result.get("display", {}),
        }

        return JsonResponse(
            {
                "response": result["result"],
                "query_id": chat_log.query_id,
                "session_id": result.get("session_id"),
                "time_taken": processing_time,
                "mode": "rag",
                "provider": result.get("provider", "unknown"),
                "model": result.get("model", "unknown"),
                "fallback": result.get("fallback", False),
                "sources": result.get("sources", []),
                "display": result.get("display", {}),
            }
        )
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
