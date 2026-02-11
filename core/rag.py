import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Configuration
FAISS_INDEX_PATH = "db/faiss_index"
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

class RAGManager:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            add_start_index=True
        )
        self.db = None
        self._init_db()

    def _init_db(self):
        if os.path.exists(FAISS_INDEX_PATH):
            self.db = FAISS.load_local(FAISS_INDEX_PATH, self.embeddings, allow_dangerous_deserialization=True)
        else:
            # Initialize with dummy document if index doesn't exist
            from langchain_core.documents import Document
            self.db = FAISS.from_documents([Document(page_content="initialization", metadata={})], self.embeddings)

    def process_file(self, file_path: str):
        if file_path.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith(".txt"):
            loader = TextLoader(file_path)
        else:
            raise ValueError("Unsupported file format")

        documents = loader.load()
        chunks = self.text_splitter.split_documents(documents)
        
        # Add to FAISS
        self.db.add_documents(chunks)
        self.db.save_local(FAISS_INDEX_PATH)
        return chunks

    def query(self, text: str, k: int = 5):
        if self.db is None:
             return []
        return self.db.similarity_search(text, k=k)

    def get_retriever(self, search_kwargs={"k": 5}):
        return self.db.as_retriever(search_kwargs=search_kwargs)

rag_manager = RAGManager()
