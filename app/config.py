"""Orchestrator configuration, loaded from environment / .env files.

Reads the project-root .env first, then policy_rag_service/.env so the
LLM settings (key, base URL, CA cert) are shared with the RAG service.
Values already set are never overridden.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
RAG_DIR = ROOT / "policy_rag_service"

load_dotenv(ROOT / ".env")
load_dotenv(RAG_DIR / ".env")


def _cert_path(value: str) -> Path:
    p = Path(value).expanduser()
    if p.is_absolute():
        return p
    for base in (ROOT, RAG_DIR):
        if (base / p).exists():
            return base / p
    return RAG_DIR / p


def _url(name: str, default: str) -> str:
    return os.getenv(name, default).rstrip("/")


@dataclass(frozen=True)
class Settings:
    # Downstream services
    employee_service_url: str = _url("EMPLOYEE_SERVICE_URL", "http://127.0.0.1:9090")
    leave_service_url: str = _url("LEAVE_SERVICE_URL", "http://127.0.0.1:9091")
    policy_service_url: str = _url("POLICY_SERVICE_URL", "http://127.0.0.1:8001")
    service_timeout: float = float(os.getenv("SERVICE_TIMEOUT", "180"))

    # LLM (intent routing)
    llm_base_url: str = _url("LLM_BASE_URL", "https://103.42.50.41:1032/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "Qwen/Qwen3-8B")
    llm_ca_cert: Path = _cert_path(os.getenv("LLM_CA_CERT", "certs/vm06-ca.crt"))
    use_llm_router: bool = os.getenv("USE_LLM_ROUTER", "true").lower() in {"1", "true", "yes"}
    llm_timeout: float = float(os.getenv("LLM_TIMEOUT", "120"))

    # Conversation memory
    history_turns: int = int(os.getenv("SESSION_HISTORY_TURNS", "3"))
    session_ttl_minutes: int = int(os.getenv("SESSION_TTL_MINUTES", "120"))

    # Output limits
    max_history_rows: int = int(os.getenv("MAX_HISTORY_ROWS", "10"))
    max_holiday_rows: int = int(os.getenv("MAX_HOLIDAY_ROWS", "10"))

    cors_origins: str = os.getenv("CORS_ORIGINS", "*")


settings = Settings()
