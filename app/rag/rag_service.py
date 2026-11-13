"""
RAG Service Orchestrator.
Manages end-to-end document loading, indexing, semantic retrieval, and citation formatting.
"""

from typing import Dict, Any, Optional
from app.config.settings import settings
from app.config.logging_config import logger
from app.rag.document_loader import DocumentLoader
from app.rag.chunker import PolicyChunker
from app.rag.embedding_service import EmbeddingService
from app.rag.vector_store import VectorStore
from app.rag.retriever import PolicyRetriever


class RAGService:
    def __init__(self):
        self.doc_loader = DocumentLoader()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.retriever = PolicyRetriever(self.vector_store, self.embedding_service)

    def build_or_refresh_index(self, force: bool = False):
        """Index all documents in storage/documents/ into the vector store."""
        if len(self.vector_store.chunks) > 0 and not force:
            logger.info("Vector store index already populated. Skipping rebuild.")
            return

        logger.info("Building vector index for policy documents...")
        self.vector_store.clear()
        docs = self.doc_loader.load_all_documents()

        all_chunks = []
        for text, meta in docs:
            chunks = PolicyChunker.chunk_policy_text(text, meta)
            all_chunks.extend(chunks)

        if all_chunks:
            texts = [c.content for c in all_chunks]
            embeddings = self.embedding_service.embed_texts(texts)
            self.vector_store.add_chunks(all_chunks, embeddings)
            logger.info(f"Successfully indexed {len(all_chunks)} chunks into vector store.")
        else:
            logger.warning("No document chunks created during index build.")

    def query_policy(
        self,
        query: str,
        department: Optional[str] = None,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """Query policy knowledge base and retrieve context with citations."""
        if len(self.vector_store.chunks) == 0:
            self.build_or_refresh_index()

        return self.retriever.retrieve_policy_context(query, department, top_k)

