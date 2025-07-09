#MV-2025-07-04-<6>  STARTS
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ChatLog
from .services import RAGService
from .preprocessing import QueryPreprocessor
import json
import time
import uuid

rag_service = RAGService()
preprocessor = QueryPreprocessor()
@csrf_exempt
def chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        query_text = data.get('query', '').strip()
        prompt_type = data.get('prompt_type', 'qa')
        
        clean_query = preprocessor.preprocess(query_text)
        
        start_time = time.time()
        result = rag_service.query(clean_query, prompt_type)
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
            'model': 'gemma3:1b'
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