import os
import math
import re
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, List
from pypdf import PdfReader
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
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
            self.db = FAISS.from_documents([Document(page_content="initialization", metadata={})], self.embeddings)

    def _extract_pdf_text(self, file_path: str) -> list[dict[str, Any]]:
        reader = PdfReader(file_path)
        pages: list[dict[str, Any]] = []
        for idx, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            pages.append({"page_number": idx, "text": text})
        return pages

    def _extract_pdf_images(self, file_path: str) -> list[dict[str, Any]]:
        reader = PdfReader(file_path)
        images: list[dict[str, Any]] = []
        for page_idx, page in enumerate(reader.pages, start=1):
            for image_idx, image_file in enumerate(getattr(page, "images", []), start=1):
                images.append(
                    {
                        "page_number": page_idx,
                        "image_number": image_idx,
                        "name": getattr(image_file, "name", f"page{page_idx}_img{image_idx}"),
                        "bytes": getattr(image_file, "data", b""),
                    }
                )
        return images

    def _ocr_images(self, images: list[dict[str, Any]]) -> list[dict[str, Any]]:
        try:
            import pytesseract
            from PIL import Image
        except Exception:
            return []

        ocr_items: list[dict[str, Any]] = []
        for item in images:
            image_bytes = item.get("bytes", b"")
            if not image_bytes:
                continue
            try:
                with Image.open(BytesIO(image_bytes)) as img:
                    text = (pytesseract.image_to_string(img) or "").strip()
                if text:
                    ocr_items.append(
                        {
                            "page_number": item["page_number"],
                            "image_number": item["image_number"],
                            "name": item["name"],
                            "text": text,
                        }
                    )
            except Exception:
                continue
        return ocr_items

    def _build_pdf_documents(self, file_path: str) -> list[Document]:
        uploaded_at = datetime.now(timezone.utc).isoformat()
        filename = os.path.basename(file_path)

        pages = self._extract_pdf_text(file_path)
        images = self._extract_pdf_images(file_path)
        ocr_items = self._ocr_images(images)

        page_to_ocr_texts: dict[int, list[str]] = {}
        for item in ocr_items:
            page_to_ocr_texts.setdefault(item["page_number"], []).append(item["text"])

        documents: list[Document] = []
        for page in pages:
            page_number = page["page_number"]
            page_text = page["text"]
            ocr_text = "\n".join(page_to_ocr_texts.get(page_number, [])).strip()

            if page_text:
                documents.append(
                    Document(
                        page_content=page_text,
                        metadata={
                            "source": file_path,
                            "filename": filename,
                            "page": page_number - 1,
                            "page_number": page_number,
                            "uploaded_at": uploaded_at,
                            "source_type": "pdf_text",
                        },
                    )
                )
            if ocr_text:
                documents.append(
                    Document(
                        page_content=ocr_text,
                        metadata={
                            "source": file_path,
                            "filename": filename,
                            "page": page_number - 1,
                            "page_number": page_number,
                            "uploaded_at": uploaded_at,
                            "source_type": "pdf_ocr",
                        },
                    )
                )

        return documents

    def _build_text_documents(self, file_path: str) -> list[Document]:
        uploaded_at = datetime.now(timezone.utc).isoformat()
        filename = os.path.basename(file_path)
        loader = TextLoader(file_path)
        docs = loader.load()
        normalized: list[Document] = []
        for doc in docs:
            normalized.append(
                Document(
                    page_content=doc.page_content,
                    metadata={
                        **(doc.metadata or {}),
                        "source": file_path,
                        "filename": filename,
                        "page_number": 1,
                        "uploaded_at": uploaded_at,
                        "source_type": "text",
                    },
                )
            )
        return normalized

    def _enrich_chunk_metadata(self, file_path: str, chunks: list[Document]) -> list[Document]:
        filename = os.path.basename(file_path)
        uploaded_at = datetime.now(timezone.utc).isoformat()
        for idx, chunk in enumerate(chunks, start=1):
            meta = chunk.metadata or {}
            page_number = meta.get("page_number")
            if not page_number:
                page_number = int(meta.get("page", 0)) + 1
            source_type = meta.get("source_type", "unknown")
            chunk.metadata = {
                **meta,
                "source": file_path,
                "filename": filename,
                "page_number": page_number,
                "uploaded_at": meta.get("uploaded_at", uploaded_at),
                "source_type": source_type,
                "chunk_id": f"{filename}:p{page_number}:{source_type}:c{idx}",
            }
        return chunks

    def process_file(self, file_path: str):
        lower = file_path.lower()
        if lower.endswith(".pdf"):
            documents = self._build_pdf_documents(file_path)
        elif lower.endswith((".txt", ".md")):
            documents = self._build_text_documents(file_path)
        else:
            raise ValueError("Unsupported file format")

        if not documents:
            documents = [
                Document(
                    page_content="",
                    metadata={
                        "source": file_path,
                        "filename": os.path.basename(file_path),
                        "page_number": 1,
                        "uploaded_at": datetime.now(timezone.utc).isoformat(),
                        "source_type": "empty",
                    },
                )
            ]

        chunks = self.text_splitter.split_documents(documents)
        chunks = self._enrich_chunk_metadata(file_path, chunks)

        # Add to FAISS
        self.db.add_documents(chunks)
        self.db.save_local(FAISS_INDEX_PATH)
        return chunks

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", (text or "").lower())

    def _all_index_documents(self) -> list[Document]:
        if not self.db:
            return []
        docstore = getattr(self.db, "docstore", None)
        store = getattr(docstore, "_dict", {}) if docstore else {}
        docs = [doc for doc in store.values() if isinstance(doc, Document)]
        return docs

    def _sparse_bm25_search(self, query: str, k: int = 20) -> list[tuple[Document, float]]:
        docs = self._all_index_documents()
        if not docs:
            return []

        tokenized_docs = [self._tokenize(doc.page_content) for doc in docs]
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        doc_freq: dict[str, int] = {}
        for tokens in tokenized_docs:
            for term in set(tokens):
                doc_freq[term] = doc_freq.get(term, 0) + 1

        n_docs = len(docs)
        avgdl = sum(len(toks) for toks in tokenized_docs) / max(n_docs, 1)
        k1 = 1.5
        b = 0.75
        scored: list[tuple[Document, float]] = []

        for doc, tokens in zip(docs, tokenized_docs):
            if not tokens:
                continue
            tf: dict[str, int] = {}
            for term in tokens:
                tf[term] = tf.get(term, 0) + 1
            dl = len(tokens)
            score = 0.0
            for term in query_tokens:
                if term not in tf:
                    continue
                df = doc_freq.get(term, 0)
                idf = math.log(((n_docs - df + 0.5) / (df + 0.5)) + 1.0)
                freq = tf[term]
                denom = freq + k1 * (1 - b + b * (dl / max(avgdl, 1e-9)))
                score += idf * ((freq * (k1 + 1)) / max(denom, 1e-9))
            if score > 0:
                scored.append((doc, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def query_dense(self, text: str, k: int = 10) -> list[dict[str, Any]]:
        if self.db is None:
            return []
        pairs = self.db.similarity_search_with_score(text, k=k)
        out: list[dict[str, Any]] = []
        for rank, (doc, distance) in enumerate(pairs, start=1):
            out.append(
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata or {},
                    "dense_score": 1.0 / (1.0 + float(distance)),
                    "dense_rank": rank,
                }
            )
        return out

    def query_hybrid(
        self,
        text: str,
        k: int = 5,
        k_dense: int = 20,
        k_sparse: int = 20,
        dense_weight: float = 0.55,
        sparse_weight: float = 0.45,
        rrf_k: int = 60,
    ) -> list[dict[str, Any]]:
        dense_results = self.query_dense(text, k=k_dense)
        sparse_pairs = self._sparse_bm25_search(text, k=k_sparse)
        sparse_results: list[dict[str, Any]] = []
        for rank, (doc, score) in enumerate(sparse_pairs, start=1):
            sparse_results.append(
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata or {},
                    "sparse_score": float(score),
                    "sparse_rank": rank,
                }
            )

        merged: dict[str, dict[str, Any]] = {}

        def _key(content: str, metadata: dict[str, Any]) -> str:
            return f"{metadata.get('chunk_id', '')}|{metadata.get('source', '')}|{metadata.get('page_number', '')}|{hash(content)}"

        for item in dense_results:
            key = _key(item["content"], item["metadata"])
            merged.setdefault(
                key,
                {"content": item["content"], "metadata": item["metadata"], "dense_rank": None, "sparse_rank": None, "dense_score": 0.0, "sparse_score": 0.0},
            )
            merged[key]["dense_rank"] = item.get("dense_rank")
            merged[key]["dense_score"] = item.get("dense_score", 0.0)

        for item in sparse_results:
            key = _key(item["content"], item["metadata"])
            merged.setdefault(
                key,
                {"content": item["content"], "metadata": item["metadata"], "dense_rank": None, "sparse_rank": None, "dense_score": 0.0, "sparse_score": 0.0},
            )
            merged[key]["sparse_rank"] = item.get("sparse_rank")
            merged[key]["sparse_score"] = item.get("sparse_score", 0.0)

        fused: list[dict[str, Any]] = []
        for item in merged.values():
            dense_rank = item.get("dense_rank")
            sparse_rank = item.get("sparse_rank")
            dense_rrf = 0.0 if dense_rank is None else 1.0 / (rrf_k + dense_rank)
            sparse_rrf = 0.0 if sparse_rank is None else 1.0 / (rrf_k + sparse_rank)
            fused_score = (dense_weight * dense_rrf) + (sparse_weight * sparse_rrf)
            fused.append(
                {
                    "content": item["content"],
                    "metadata": item["metadata"],
                    "dense_score": item.get("dense_score", 0.0),
                    "sparse_score": item.get("sparse_score", 0.0),
                    "fused_score": fused_score,
                    "dense_rank": dense_rank,
                    "sparse_rank": sparse_rank,
                }
            )

        fused.sort(key=lambda x: x.get("fused_score", 0.0), reverse=True)
        for rank, item in enumerate(fused, start=1):
            item["hybrid_rank"] = rank
        return fused[:k]

    def query(self, text: str, k: int = 5):
        results = self.query_hybrid(text, k=k)
        docs: list[Document] = []
        for item in results:
            docs.append(
                Document(
                    page_content=item["content"],
                    metadata={
                        **(item.get("metadata") or {}),
                        "dense_score": item.get("dense_score", 0.0),
                        "sparse_score": item.get("sparse_score", 0.0),
                        "fused_score": item.get("fused_score", 0.0),
                        "hybrid_rank": item.get("hybrid_rank"),
                    },
                )
            )
        return docs

    def get_retriever(self, search_kwargs={"k": 5}):
        return self.db.as_retriever(search_kwargs=search_kwargs)

class LazyRAGManager:
    def __init__(self):
        self._instance: RAGManager | None = None

    def _get_instance(self) -> RAGManager:
        if self._instance is None:
            self._instance = RAGManager()
        return self._instance

    def __getattr__(self, name: str):
        return getattr(self._get_instance(), name)


rag_manager = LazyRAGManager()
