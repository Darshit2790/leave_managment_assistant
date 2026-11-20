"""RAG pipeline: retrieve -> guard -> generate -> cite."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.llm_client import LLMClient
from app.vector_store import PolicyVectorStore

NOT_FOUND_MSG = (
    "I couldn't find this information in the available HR policy documents. "
    "Please contact the HR team directly for an accurate answer."
)

SYSTEM_PROMPT = """You are an HR policy assistant for company employees.
Answer ONLY using the CONTEXT excerpts provided. Rules:
1. Do not use outside knowledge and never invent numbers, dates or rules.
2. If the context does not contain the answer, reply exactly: "NOT_FOUND".
3. Be concise and clear. Use bullet points for multi-part answers.
4. After each fact, cite its source like [leave_policy.pdf, p.2]."""


@dataclass
class RAGResult:
    answer: str
    found: bool
    sources: List[Dict] = field(default_factory=list)  # [{source, page, score}]


class PolicyRAG:
    def __init__(self, store: Optional[PolicyVectorStore] = None, llm: Optional[LLMClient] = None):
        self.store = store or PolicyVectorStore()
        self._llm = llm

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    @staticmethod
    def _build_context(hits: List[Dict]) -> str:
        return "\n\n".join(
            f"[Source: {h['source']} | Page {h['page']}]\n{h['text']}" for h in hits
        )

    def answer(self, question: str, history: Optional[List[Tuple[str, str]]] = None) -> RAGResult:
        hits = [h for h in self.store.search(question) if h["score"] >= settings.min_similarity]
        if not hits:
            return RAGResult(answer=NOT_FOUND_MSG, found=False)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for q, a in (history or [])[-3:]:  # short memory keeps us inside the 8192-token limit
            messages += [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
        messages.append(
            {
                "role": "user",
                "content": f"CONTEXT:\n{self._build_context(hits)}\n\nQUESTION: {question}\n/no_think",
            }
        )

        reply = self.llm.chat(messages)
        if "NOT_FOUND" in reply:
            return RAGResult(answer=NOT_FOUND_MSG, found=False)

        seen, sources = set(), []
        for h in hits:
            key = (h["source"], h["page"])
            if key not in seen:
                seen.add(key)
                sources.append({"source": h["source"], "page": h["page"], "score": round(h["score"], 3)})
        return RAGResult(answer=reply, found=True, sources=sources)
