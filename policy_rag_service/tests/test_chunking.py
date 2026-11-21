import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion import split_text
from app.llm_client import strip_thinking


def test_short_text_single_chunk():
    assert split_text("Hello world", 1000, 100) == ["Hello world"]


def test_long_text_is_chunked_with_overlap():
    text = ("Sentence number one is here. " * 100).strip()
    chunks = split_text(text, 300, 50)
    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)


def test_empty_text():
    assert split_text("   \n\n ", 300, 50) == []


def test_strip_thinking():
    assert strip_thinking("<think>reasoning</think>Final answer") == "Final answer"
    assert strip_thinking("Plain answer") == "Plain answer"
