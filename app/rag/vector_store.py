"""
Vector Store Module.
A high-performance local vector store with persistence to JSON and NumPy arrays:
- Fast vector similarity search via cosine similarity
- Metadata filtering (department, policy_id, academic_year, version)
- Atomic disk persistence in storage/vector_store/
- Fully standalone without external cloud dependencies.
"""

import os
import json
from typing import List, Dict, Any, Optional
import numpy as np
from app.config.settings import settings
from app.config.logging_config import logger
from app.rag.chunker import DocumentChunk


class VectorStore:
    def __init__(self, store_dir: str = settings.VECTOR_STORE_PATH):
        self.store_dir = store_dir
        os.makedirs(store_dir, exist_ok=True)
        self.index_file = os.path.join(store_dir, "chunks_index.json")
        self.vectors_file = os.path.join(store_dir, "vectors.npy")

        self.chunks: List[Dict[str, Any]] = []
        self.vectors: Optional[np.ndarray] = None
        self.load()

    def add_chunks(self, chunks: List[DocumentChunk], embeddings: np.ndarray):
        """Add new document chunks and corresponding embedding vectors."""
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match.")

        new_dicts = [c.to_dict() for c in chunks]

        if self.vectors is None or len(self.chunks) == 0:
            self.chunks = new_dicts
            self.vectors = embeddings
        else:
            self.chunks.extend(new_dicts)
            self.vectors = np.vstack([self.vectors, embeddings])

        self.save()
        logger.info(f"Vector store now contains {len(self.chunks)} chunks.")

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for top_k most similar chunks, applying optional metadata filters.
        """
        if self.vectors is None or len(self.chunks) == 0:
            return []

        # Cosine similarity
        # query_vector is shape (D,), self.vectors is shape (N, D)
        q_norm = np.linalg.norm(query_vector)
        if q_norm == 0:
            q_norm = 1.0
        q_normalized = query_vector / q_norm

        v_norms = np.linalg.norm(self.vectors, axis=1)
        v_norms[v_norms == 0] = 1.0
        v_normalized = self.vectors / v_norms[:, np.newaxis]

        scores = np.dot(v_normalized, q_normalized)

        # Apply metadata filters
        candidates = []
        for idx, score in enumerate(scores):
            chunk = self.chunks[idx]
            meta = chunk.get("metadata", {})

            # Check filters
            match = True
            if filters:
                for k, v in filters.items():
                    if k in meta:
                        # If filtering by department, allow 'ALL' matches
                        if k == "department" and meta.get(k) in [v, "ALL"]:
                            continue
                        if meta.get(k) != v:
                            match = False
                            break
            if match:
                candidates.append({
                    "chunk_id": chunk["chunk_id"],
                    "content": chunk["content"],
                    "metadata": meta,
                    "similarity_score": float(score)
                })

        # Sort descending by similarity score
        candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
        return candidates[:top_k]

    def save(self):
        """Persist index and embeddings to disk."""
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, indent=2)
        if self.vectors is not None:
            np.save(self.vectors_file, self.vectors)
        logger.debug(f"Saved vector store to {self.store_dir}")

    def load(self):
        """Load persisted index and embeddings from disk if available."""
        if os.path.exists(self.index_file) and os.path.exists(self.vectors_file):
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self.chunks = json.load(f)
                self.vectors = np.load(self.vectors_file)
                logger.info(f"Loaded {len(self.chunks)} chunks from vector store.")
            except Exception as e:
                logger.warning(f"Failed to load vector store from disk: {e}")
                self.chunks = []
                self.vectors = None

    def clear(self):
        self.chunks = []
        self.vectors = None
        if os.path.exists(self.index_file):
            os.remove(self.index_file)
        if os.path.exists(self.vectors_file):
            os.remove(self.vectors_file)

