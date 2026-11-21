"""Client for the Qwen3-8B OpenAI-compatible endpoint (HTTPS + custom CA cert)."""
import re
import time
from typing import Dict, List, Optional

import requests

from app.config import settings


class LLMError(RuntimeError):
    pass


def strip_thinking(text: str) -> str:
    """Qwen3 may emit <think>...</think> reasoning; remove it."""
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()


class LLMClient:
    RETRY_DELAYS = (2, 4, 8)  # for 429 / 503, per the learner guide

    def __init__(self):
        if not settings.llm_api_key or settings.llm_api_key == "YOUR_GROUP_API_KEY":
            raise LLMError("LLM_API_KEY is not set. Copy .env.example to .env and add your key.")
        if not settings.llm_ca_cert.exists():
            raise LLMError(
                f"CA certificate not found at: {settings.llm_ca_cert}\n"
                "Set LLM_CA_CERT in .env to the exact path of vm06-ca.crt."
            )
        self.url = f"{settings.llm_base_url}/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 600,
        temperature: float = 0.2,
        timeout: int = 180,
    ) -> str:
        payload = {
            "model": settings.llm_model,
            "messages": messages,
            "max_tokens": min(max(max_tokens, 1), 1024),
            "temperature": temperature,
            # ask Qwen3 to skip "thinking" mode (ignored by servers that don't support it)
            "chat_template_kwargs": {"enable_thinking": False},
        }
        last_err: Optional[str] = None
        for attempt in range(len(self.RETRY_DELAYS) + 1):
            try:
                r = requests.post(
                    self.url,
                    headers=self.headers,
                    json=payload,
                    verify=str(settings.llm_ca_cert),
                    timeout=timeout,
                )
            except requests.exceptions.SSLError as e:
                raise LLMError(f"TLS/certificate error: {e}") from e
            except requests.exceptions.RequestException as e:
                last_err = f"network error: {e}"
            else:
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"] or ""
                    return strip_thinking(content)
                if r.status_code in (429, 503):
                    last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                else:
                    raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
            if attempt < len(self.RETRY_DELAYS):
                time.sleep(self.RETRY_DELAYS[attempt])
        raise LLMError(f"Failed after retries. Last error: {last_err}")

    def ping(self) -> str:
        return self.chat([{"role": "user", "content": "Reply with the single word: OK"}], max_tokens=10)
