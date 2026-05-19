#MV-2025-07-04-<5>  STARTS
import os
import re
import time

from django.conf import settings
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .prompts import PROMPTS
#from langchain_community.llms import HTTPLLM


class RAGService:
    def __init__(self):
        # U: OLD: self.index_dir = os.path.join(settings.BASE_DIR, 'data')
        # U: NEW: keep chatbot RAG data inside the chatbot app, matching latest upstream layout.
        self.index_dir = os.path.join(settings.BASE_DIR, 'chatbot', 'data')
        self.index_path = os.path.join(self.index_dir, 'index')
        self.llm = None
        self.retriever = None
        # U: OLD code hardcoded Ollama URL/model inside _load_components.
        # U: NEW keeps the same default model but allows local/deployment overrides.
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "gemma3:1b")
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
        # U: OLD: RetrievalQA.from_chain_type(...) used the deprecated legacy chain API.
        # U: NEW: use explicit retrieve -> format context -> prompt -> LLM invocation,
        # U: which is compatible with the current LangChain package split.
        self.llm = OllamaLLM(
            # U: OLD: model="gemma3:1b", base_url=f"{ollama_base_url}"
            # U: NEW: use env-backed fields configured during service setup.
            model=self.ollama_model,
            base_url=self.ollama_base_url,
        )
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})

        print("[✅] Loaded existing FAISS index from", self.index_dir)
        #AS-2025-07-21-<1>  ENDS

    # def _load_components(self):
    #     self.embeddings = HuggingFaceEmbeddings(
    #         model_name="sentence-transformers/all-MiniLM-L6-v2"
    #     )
    #
    #     self.vector_store = FAISS.load_local(
    #         folder_path=self.index_dir,
    #         embeddings=self.embeddings,
    #         index_name="index",
    #         allow_dangerous_deserialization=True
    #     )
    #
    #     self.qa_chain = RetrievalQA.from_chain_type(
    #
    #         llm = OllamaLLM(model="llama3.2:3b") ,
    #         chain_type="stuff",
    #         retriever=self.vector_store.as_retriever(search_kwargs={"k": 3}),
    #         return_source_documents=True,
    #         chain_type_kwargs={"prompt": PROMPTS['qa']}
    #     )
    #
    #     print("[✅] Loaded existing FAISS index from", self.index_dir)

    def query(self, query_text, prompt_type='qa'):
        try:
            prompt = PROMPTS.get(prompt_type, PROMPTS['qa'])
            docs = self.retriever.invoke(query_text)
            context = self._format_documents(docs)
            answer = self.llm.invoke(
                prompt.format(context=context, question=query_text)
            )
            return {
                "result": str(answer),
                "context": docs
            }

        except Exception as e:
            print(f"Error during query: {e}")
            # U: OLD: return None
            # U: NEW: keep /chat/ usable for local MVP testing when Ollama is not installed/running.
            return self._retrieval_only_fallback(query_text, e)

    def _retrieval_only_fallback(self, query_text, error):
        """
        Return retrieved context when the local Ollama LLM is unavailable.
        This is not a replacement for the real RAG answer; it prevents a 500 and
        tells the tester exactly which local model dependency is missing.
        """
        try:
            docs = self.vector_store.similarity_search(query_text, k=3)
        except Exception as retrieval_error:
            return {
                "result": (
                    "The chatbot could not answer because the local RAG components "
                    f"failed to retrieve context. Details: {retrieval_error}"
                ),
                "context": []
            }

        snippets = []
        for index, doc in enumerate(docs, start=1):
            text = re.sub(r"\s+", " ", doc.page_content).strip()
            snippets.append(f"{index}. {text[:500]}")

        return {
            "result": (
                "The local chatbot LLM is not running, so this is a retrieval-only "
                f"fallback instead of a generated answer. Start Ollama at {self.ollama_base_url} "
                f"and pull/run model `{self.ollama_model}` for full chatbot answers.\n\n"
                "Relevant retrieved context:\n" + "\n\n".join(snippets)
            ),
            "context": docs
        }

    def _format_documents(self, docs):
        return "\n\n".join(doc.page_content for doc in docs)

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
