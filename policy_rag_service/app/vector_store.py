"""ChromaDB wrapper (persistent, cosine similarity)."""
from typing import Dict, List

import chromadb

from app.config import settings
from app.embeddings import Embedder
from app.ingestion import Chunk


class PolicyVectorStore:
    def __init__(self):
        settings.vectorstore_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(settings.vectorstore_dir))
        self.collection = self.client.get_or_create_collection(
            name=settings.collection_name, metadata={"hnsw:space": "cosine"}
        )
        self._embedder: Embedder | None = None

    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = Embedder()
        return self._embedder

    def count(self) -> int:
        return self.collection.count()

    def add_chunks(self, chunks: List[Chunk], batch_size: int = 64) -> None:
        if not chunks:
            return
        # Re-ingesting a file replaces its old chunks (idempotent)
        self.collection.delete(where={"source": chunks[0].source})
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            self.collection.add(
                ids=[c.id for c in batch],
                documents=[c.text for c in batch],
                embeddings=self.embedder.embed_documents([c.text for c in batch]),
                metadatas=[
                    {"source": c.source, "page": c.page, "chunk_index": c.chunk_index}
                    for c in batch
                ],
            )

    def search(self, query: str, top_k: int = settings.top_k) -> List[Dict]:
        if self.count() == 0:
            return []
        res = self.collection.query(
            query_embeddings=[self.embedder.embed_query(query)],
            n_results=min(top_k, self.count()),
        )
        hits = []
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        ):
            hits.append(
                {
                    "text": doc,
                    "source": meta["source"],
                    "page": meta["page"],
                    "score": 1.0 - float(dist),  # cosine distance -> similarity
                }
            )
        return hits

    def list_sources(self) -> Dict[str, int]:
        """Return {pdf_name: number_of_chunks}."""
        counts: Dict[str, int] = {}
        for m in self.collection.get(include=["metadatas"])["metadatas"]:
            counts[m["source"]] = counts.get(m["source"], 0) + 1
        return counts

    def reset(self) -> None:
        self.client.delete_collection(settings.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=settings.collection_name, metadata={"hnsw:space": "cosine"}
        )
