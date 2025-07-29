#MV-2025-07-04-<5>  STARTS
import time
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_community.llms import Ollama
from langchain_huggingface import HuggingFaceEmbeddings
from .prompts import PROMPTS
import os
from django.conf import settings
from langchain_ollama import OllamaLLM
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
#from langchain_community.llms import HTTPLLM



class RAGService:
    def __init__(self):
        self.index_dir = os.path.join(settings.BASE_DIR, 'chatbot', 'data')
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
        #AS-2025-07-21-<1>  STARTS
        # Read the Ollama URL from the environment, with a fallback default
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=OllamaLLM(
                model="llama3.2:3b",
                base_url=f"{ollama_base_url}",  
            ), 
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 3}),
            return_source_documents=True,  
            chain_type_kwargs={"prompt": PROMPTS['qa']}
        )
          
        print("[✅] Loaded existing FAISS index from", self.index_dir) 
        #AS-2025-07-21-<1>  ENDS

    # def _load_components(self):
    #     self.embeddings = HuggingFaceEmbeddings(
    #         model_name="sentence-transformers/all-MiniLM-L6-v2"
    #     )
        
    #     self.vector_store = FAISS.load_local(
    #         folder_path=self.index_dir,
    #         embeddings=self.embeddings,
    #         index_name="index",
    #         allow_dangerous_deserialization=True
    #     )
        
    #     self.qa_chain = RetrievalQA.from_chain_type(
           
    #         llm = OllamaLLM(model="llama3.2:3b") , 
    #         chain_type="stuff",
    #         retriever=self.vector_store.as_retriever(search_kwargs={"k": 3}),
    #         return_source_documents=True,  
    #         chain_type_kwargs={"prompt": PROMPTS['qa']}
    #     )
        
    #     print("[✅] Loaded existing FAISS index from", self.index_dir)
        
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
    def add_files_to_index(self, file_paths):
        """
        Incrementally add new files to the FAISS vector store.
        file_paths: list of file paths (PDF or text files)
        """
        # 1. Load and split new documents
        docs = []
        for path in file_paths:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".pdf":
                loader = PyPDFLoader(path)
            else:
                loader = TextLoader(path)
            docs.extend(loader.load())

        # 2. Split documents into chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        split_docs = splitter.split_documents(docs)

        # 3. Embed and add to existing FAISS index
        new_vector_store = FAISS.from_documents(split_docs, self.embeddings)
        self.vector_store.merge_from(new_vector_store)

        # 4. Save the updated index
        self.vector_store.save_local(self.index_dir, index_name="index")
        print(f"[✅] Added {len(split_docs)} new chunks to FAISS index.")

    
#MV-2025-07-04-<5>  ENDS