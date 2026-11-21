"""PDF ingestion: text extraction + chunking (page-aware for citations)."""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from pypdf import PdfReader


@dataclass
class Chunk:
    id: str
    text: str
    source: str       # PDF file name
    page: int         # 1-based page number
    chunk_index: int


def split_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> List[str]:
    """Split text into overlapping chunks, preferring paragraph/sentence boundaries."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            window = text[start:end]
            cut = max(window.rfind("\n\n"), window.rfind(". "), window.rfind("\n"))
            if cut > chunk_size * 0.5:
                end = start + cut + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def load_pdf(path: Path, chunk_size: int = 1000, overlap: int = 150) -> List[Chunk]:
    """Extract text page by page and return chunks tagged with source + page."""
    reader = PdfReader(str(path))
    chunks: List[Chunk] = []
    for page_no, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for i, piece in enumerate(split_text(text, chunk_size, overlap)):
            chunks.append(
                Chunk(
                    id=f"{path.name}::p{page_no}::c{i}",
                    text=piece,
                    source=path.name,
                    page=page_no,
                    chunk_index=i,
                )
            )
    if not chunks:
        print(f"  [warn] No extractable text in {path.name} (scanned PDF? OCR needed).")
    return chunks
