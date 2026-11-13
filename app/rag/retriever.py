"""
Policy Retriever Module.
Executes semantic retrieval with metadata filtering, policy ranking, and citation building.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from app.config.logging_config import logger
from app.rag.vector_store import VectorStore
from app.rag.embedding_service import EmbeddingService


class PolicyRetriever:
    def __init__(self, vector_store: VectorStore, embedding_service: EmbeddingService):
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    def retrieve_policy_context(
        self,
        query: str,
        department: Optional[str] = None,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Retrieve relevant policy chunks and format them into grounded context and citations.
        """
        q_vec = self.embedding_service.embed_query(query)
        filters = {}
        if department and department != "ALL":
            filters["department"] = department

        raw_results = self.vector_store.search(q_vec, top_k=top_k, filters=filters)

        citations = []
        context_snippets = []

        for r in raw_results:
            meta = r.get("metadata", {})
            page = meta.get("source_page")
            page_str = f"Page {page}" if page is not None else "Page information unavailable in source metadata"

            citation = {
                "document_name": meta.get("document_name", "Institutional Workload Regulations"),
                "document_id": meta.get("document_id", "DOC-POL-2026-V1"),
                "policy_id": meta.get("policy_id", "POL-ALL"),
                "department": meta.get("department", "ALL"),
                "effective_date": meta.get("effective_date", "2026-07-01"),
                "source_page": page_str,
                "version": meta.get("version", "1.0"),
                "similarity_score": round(r["similarity_score"], 3)
            }
            citations.append(citation)
            context_snippets.append(f"--- Document: {citation['document_name']} ({citation['source_page']}) ---\n{r['content']}")

        full_context = "\n\n".join(context_snippets) if context_snippets else "No relevant policy documents found."

        return {
            "query": query,
            "context": full_context,
            "citations": citations,
            "retrieved_count": len(raw_results)
        }

