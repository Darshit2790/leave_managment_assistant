"""Local embeddings via fastembed (ONNX, no GPU/torch needed).

The Qwen API server does not expose an embeddings endpoint, so we embed locally.
The model is downloaded once on first use (~130 MB) and cached.
"""
from typing import List

from app.config import settings


class Embedder:
    def __init__(self, model_name: str = settings.embedding_model):
        from fastembed import TextEmbedding

        self.model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [v.tolist() for v in self.model.passage_embed(texts)]

    def embed_query(self, query: str) -> List[float]:
        return next(iter(self.model.query_embed(query))).tolist()
