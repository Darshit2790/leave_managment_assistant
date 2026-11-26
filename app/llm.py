"""Async client for the Qwen3 OpenAI-compatible endpoint (HTTPS + custom CA)."""
import asyncio
import re
from typing import Dict, List, Optional

import httpx

from app.config import settings


class LLMError(RuntimeError):
    pass


# The group API key allows one active request at a time.
_lock = asyncio.Lock()


def strip_thinking(text: str) -> str:
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()


class LLMClient:
    RETRY_DELAYS = (2, 4, 8)

    @property
    def available(self) -> bool:
        key = settings.llm_api_key
        return bool(key) and key != "YOUR_GROUP_API_KEY" and settings.llm_ca_cert.exists()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 300,
        temperature: float = 0.0,
    ) -> str:
        if not self.available:
            raise LLMError("LLM is not configured (LLM_API_KEY / LLM_CA_CERT).")

        payload = {
            "model": settings.llm_model,
            "messages": messages,
            "max_tokens": min(max(max_tokens, 1), 1024),
            "temperature": temperature,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        url = f"{settings.llm_base_url}/chat/completions"
        last_err: Optional[str] = None

        async with _lock:
            async with httpx.AsyncClient(
                verify=str(settings.llm_ca_cert), timeout=settings.llm_timeout
            ) as client:
                for attempt in range(len(self.RETRY_DELAYS) + 1):
                    try:
                        r = await client.post(url, headers=headers, json=payload)
                    except httpx.HTTPError as e:
                        last_err = f"network error: {e}"
                    else:
                        if r.status_code == 200:
                            content = r.json()["choices"][0]["message"]["content"] or ""
                            return strip_thinking(content)
                        if r.status_code not in (429, 503):
                            raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
                        last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                    if attempt < len(self.RETRY_DELAYS):
                        await asyncio.sleep(self.RETRY_DELAYS[attempt])

        raise LLMError(f"Failed after retries. Last error: {last_err}")


llm = LLMClient()
