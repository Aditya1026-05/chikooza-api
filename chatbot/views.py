import json
import time
import uuid

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import ChatLog
from .preprocessing import QueryPreprocessor
from .public_assistant import PublicSiteAssistant
from .services import RAGService

# Heavy chatbot services are created only when a request needs them.
rag_service = None
public_site_assistant = None
preprocessor = QueryPreprocessor()


def get_rag_service():
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
    return rag_service


def get_public_site_assistant():
    global public_site_assistant
    if public_site_assistant is None:
        public_site_assistant = PublicSiteAssistant()
    return public_site_assistant


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
        prompt_type = data.get("prompt_type", "qa")
        chat_mode = (
            data.get("mode") or data.get("assistant") or data.get("chat_mode") or "rag"
        )
        chat_mode = str(chat_mode).strip().lower()

        if not query_text:
            return JsonResponse({"error": "Query is required"}, status=400)

        clean_query = preprocessor.preprocess(query_text)

        start_time = time.time()

        if chat_mode in {"site", "public", "public_site"}:
            assistant = get_public_site_assistant()
            site_result = assistant.answer(clean_query, history=chat_history)
            result = {
                "result": site_result.result,
                "source_documents": [],
                "sources": site_result.sources,
                "provider": site_result.provider,
                "model": site_result.model,
                "fallback": site_result.fallback,
                "display": site_result.display,
            }
        elif chat_mode == "rag":
            # Legacy Ollama/FAISS mode remains available for direct `/chat/` callers.
            rag = get_rag_service()
            result = rag.query(clean_query, prompt_type)
            result["provider"] = "ollama-rag"
            result["model"] = getattr(rag, "ollama_model", "unknown")
            result["fallback"] = False
        else:
            return JsonResponse({"error": "Unsupported chat mode"}, status=400)

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
                "time_taken": processing_time,
                "mode": chat_mode,
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
