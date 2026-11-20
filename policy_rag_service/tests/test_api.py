import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import app.api as api
from app.rag import RAGResult


class FakeStore:
    def count(self): return 3
    def list_sources(self): return {"leave_policy.pdf": 3}


class FakeRAG:
    store = FakeStore()
    def answer(self, q, history=None):
        if "annual" in q:
            return RAGResult("18 days [leave_policy.pdf, p.1]", True,
                             [{"source": "leave_policy.pdf", "page": 1, "score": 0.8}])
        return RAGResult("not found", False)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api, "_rag", FakeRAG())
    return TestClient(api.app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "chunks_indexed": 3}


def test_query_found(client):
    r = client.post("/policies/query", json={"question": "annual leave?"}).json()
    assert r["found"] and r["sources"][0]["page"] == 1


def test_query_not_found(client):
    assert client.post("/policies/query", json={"question": "weather?"}).json()["found"] is False


def test_empty_question_rejected(client):
    assert client.post("/policies/query", json={"question": ""}).status_code == 422
