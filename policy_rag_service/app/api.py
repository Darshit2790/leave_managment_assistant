"""Policy RAG service (REST API).

Run:  python main.py serve      ->  http://127.0.0.1:8001/docs  (Swagger UI)

The Agent orchestrator (Task 2) will call POST /policies/query.
"""
import threading
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.config import settings
from app.ingestion import load_pdf
from app.llm_client import LLMError
from app.rag import PolicyRAG

app = FastAPI(
    title="HR Policy RAG Service",
    version="1.0.0",
    description="PDF ingestion, semantic retrieval and cited answers over HR policy documents.",
)

_rag: Optional[PolicyRAG] = None
# The LLM key allows only 1 active request, so serialize generation calls.
_llm_lock = threading.Lock()


def get_rag() -> PolicyRAG:
    global _rag
    if _rag is None:
        _rag = PolicyRAG()
    return _rag


# ---------- schemas ----------
class Turn(BaseModel):
    question: str
    answer: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["How many annual leaves can I take?"])
    history: List[Turn] = []


class SourceRef(BaseModel):
    source: str
    page: int
    score: float


class QueryResponse(BaseModel):
    answer: str
    found: bool
    sources: List[SourceRef]


# ---------- endpoints ----------
@app.get("/health")
def health():
    rag = get_rag()
    return {"status": "ok", "chunks_indexed": rag.store.count()}


@app.get("/policies")
def list_policies():
    return {"documents": get_rag().store.list_sources()}


@app.post("/policies/ingest")
def ingest_all():
    """(Re)index every PDF in data/policies/."""
    store = get_rag().store
    pdfs = sorted(settings.policies_dir.glob("*.pdf"))
    if not pdfs:
        raise HTTPException(404, f"No PDFs found in {settings.policies_dir}")
    result = {}
    for pdf in pdfs:
        chunks = load_pdf(pdf, settings.chunk_size, settings.chunk_overlap)
        store.add_chunks(chunks)
        result[pdf.name] = len(chunks)
    return {"indexed": result, "total_chunks": store.count()}


@app.post("/policies/upload")
def upload_policy(file: UploadFile = File(...)):
    """Upload a policy PDF and index it immediately."""
    name = Path(file.filename or "").name
    if not name.lower().endswith(".pdf"):
        raise HTTPException(400, "Only .pdf files are supported")
    settings.policies_dir.mkdir(parents=True, exist_ok=True)
    dest = settings.policies_dir / name
    dest.write_bytes(file.file.read())
    chunks = load_pdf(dest, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise HTTPException(422, "No extractable text found (scanned PDF?)")
    get_rag().store.add_chunks(chunks)
    return {"document": name, "chunks": len(chunks)}


@app.post("/policies/query", response_model=QueryResponse)
def query_policy(req: QueryRequest):
    rag = get_rag()
    history = [(t.question, t.answer) for t in req.history]
    try:
        with _llm_lock:
            res = rag.answer(req.question, history)
    except LLMError as e:
        raise HTTPException(502, f"LLM error: {e}")
    return QueryResponse(answer=res.answer, found=res.found, sources=res.sources)
