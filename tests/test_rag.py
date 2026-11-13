"""
Tests for RAG Retrieval and Citations.
"""

import pytest
from app.rag.rag_service import RAGService


def test_rag_query_and_citations():
    rag = RAGService()
    if len(rag.vector_store.chunks) == 0:
        rag.build_or_refresh_index()

    res = rag.query_policy("What is the maximum workload for Professor?")
    assert res["retrieved_count"] > 0
    assert len(res["citations"]) > 0
    assert "context" in res
    # First citation has document metadata
    top_c = res["citations"][0]
    assert "document_name" in top_c
    assert "source_page" in top_c

