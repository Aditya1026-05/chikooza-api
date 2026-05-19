#MV-2025-07-04-<6>  STARTS
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ChatLog
from .services import RAGService
from .preprocessing import QueryPreprocessor
import json
import time
import uuid

# OLD: rag_service = RAGService()
# NEW: lazy-load RAG only when /chat/ is called, so chatbot setup does not block API startup.
rag_service = None
preprocessor = QueryPreprocessor()


def get_rag_service():
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
    return rag_service


@csrf_exempt
def chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        query_text = data.get('query', '').strip()
        prompt_type = data.get('prompt_type', 'qa')

        # U: OLD: empty queries reached the RAG service and failed later.
        # U: NEW: reject bad input before loading FAISS/Ollama.
        if not query_text:
            return JsonResponse({'error': 'Query is required'}, status=400)

        clean_query = preprocessor.preprocess(query_text)

        start_time = time.time()
        # OLD: result = rag_service.query(clean_query, prompt_type)
        # NEW: use lazy-loaded service so missing local LLM/model setup affects only /chat/.
        rag = get_rag_service()
        result = rag.query(clean_query, prompt_type)
        processing_time = time.time() - start_time
        
        if not result:
            return JsonResponse({'error': 'Failed to process query'}, status=500)
        
        source_docs = result.get('source_documents', result.get('context', []))
        
        serializable_context = []
        for doc in source_docs:
            serializable_context.append({
                'page_content': doc.page_content
            })
        
        chat_log = ChatLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            query=clean_query,
            response=result['result'],
            query_id=getattr(request, 'query_id', str(uuid.uuid4())))
        
        request.chat_data = {
            'query': clean_query,
            'response': result['result'],
            'context': serializable_context,
            'prompt_type': prompt_type,
            'processing_time': processing_time,
            # U: OLD: 'model': 'llama3.2:3b'
            # U: NEW: record the configured runtime model.
            'model': getattr(rag, 'ollama_model', 'unknown')
        }
        
        return JsonResponse({
            'response': result['result'],
            'query_id': chat_log.query_id,
            'time_taken': processing_time,
            # 'context': serializable_context
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
#MV-2025-07-04-<6>  ENDS
