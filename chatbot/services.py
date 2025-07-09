#MV-2025-07-04-<5>  STARTS
import time
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_community.llms import Ollama
from langchain_huggingface import HuggingFaceEmbeddings
from .prompts import PROMPTS
import os
from django.conf import settings

class RAGService:
    def __init__(self):
        # Define paths relative to Django project
        self.index_dir = os.path.join(settings.BASE_DIR, 'data')
        self.index_path = os.path.join(self.index_dir, 'index')
        self.qa_chain = None
        self._load_components()
        
    def _load_components(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        self.vector_store = FAISS.load_local(
            folder_path=self.index_dir,
            embeddings=self.embeddings,
            index_name="index",
            allow_dangerous_deserialization=True
        )
        
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=Ollama(model="gemma3:1b"),
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 3}),
            return_source_documents=True,  
            chain_type_kwargs={"prompt": PROMPTS['qa']}
        )
        
        print("[✅] Loaded existing FAISS index from", self.index_dir)
        
    def query(self, query_text, prompt_type='qa'):
        try:
            self.qa_chain.combine_documents_chain.llm_chain.prompt = PROMPTS.get(prompt_type, PROMPTS['qa'])
            
            result = self.qa_chain.invoke({"query": query_text})
            print(result)
            return {
                "result": result["result"],
                "context": result.get("source_documents", []) 
            }
            
        except Exception as e:
            print(f"Error during query: {e}")
            return None
#MV-2025-07-04-<5>  ENDS