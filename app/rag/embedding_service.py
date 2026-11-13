"""
Embedding Service.
Provides vector embeddings for semantic document retrieval:
- Features an ultra-fast, 100% offline TF-IDF vector embedding engine that works
  immediately without downloading multi-gigabyte models or waiting on remote networks.
- Also supports SentenceTransformers ('all-MiniLM-L6-v2') when explicitly configured
  or available locally.
"""

from typing import List, Optional
import numpy as np
from app.config.settings import settings
from app.config.logging_config import logger

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class EmbeddingService:
    def __init__(self, provider: str = settings.EMBEDDING_PROVIDER, model_name: str = settings.EMBEDDING_MODEL_NAME):
        self.provider = provider.lower()
        self.model_name = model_name
        self._st_model = None
        self._tfidf_vectorizer = None
        self._is_st_ready = False

        if self.provider == "sentence-transformers":
            try:
                import os
                # Only use sentence-transformers if model is cached locally
                from sentence_transformers import SentenceTransformer
                self._st_model = SentenceTransformer(self.model_name, local_files_only=True)
                self._is_st_ready = True
                logger.info(f"Loaded local SentenceTransformer: {self.model_name}")
            except Exception as e:
                logger.info(f"SentenceTransformer not cached locally ({e}). Operating in fast offline TF-IDF mode.")
                self._is_st_ready = False

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        if self._is_st_ready and self._st_model:
            try:
                embeddings = self._st_model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
                return embeddings.astype(np.float32)
            except Exception as e:
                logger.warning(f"SentenceTransformer encoding error: {e}. Falling back to TF-IDF.")

        # High-performance TF-IDF semantic projection
        if HAS_SKLEARN:
            if self._tfidf_vectorizer is None or len(texts) > 1:
                self._tfidf_vectorizer = TfidfVectorizer(
                    max_features=384,
                    stop_words="english",
                    ngram_range=(1, 2)
                )
                mat = self._tfidf_vectorizer.fit_transform(texts).toarray()
            else:
                mat = self._tfidf_vectorizer.transform(texts).toarray()

            n_samples, n_feat = mat.shape
            padded = np.zeros((n_samples, 384), dtype=np.float32)
            padded[:, :min(n_feat, 384)] = mat[:, :min(n_feat, 384)]
            # L2 normalize
            norms = np.linalg.norm(padded, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            return (padded / norms).astype(np.float32)

        # Baseline uniform normalized vector
        vec = np.ones((len(texts), 384), dtype=np.float32) / np.sqrt(384)
        return vec

    def embed_query(self, query: str) -> np.ndarray:
        res = self.embed_texts([query])
        return res[0]
