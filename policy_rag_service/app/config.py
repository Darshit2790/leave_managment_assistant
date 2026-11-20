"""Central configuration loaded from environment / .env file."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _path(value: str) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else ROOT / p


@dataclass(frozen=True)
class Settings:
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://103.42.50.41:1032/v1").rstrip("/")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "Qwen/Qwen3-8B")
    llm_ca_cert: Path = _path(os.getenv("LLM_CA_CERT", "certs/vm06-ca.crt"))

    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    top_k: int = int(os.getenv("TOP_K", "4"))
    min_similarity: float = float(os.getenv("MIN_SIMILARITY", "0.45"))

    policies_dir: Path = ROOT / "data" / "policies"
    vectorstore_dir: Path = ROOT / "data" / "vectorstore"
    collection_name: str = "hr_policies"


settings = Settings()
