"""OpenAI-compatible chat completions client (optional; key from env only)."""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.request
from typing import Any

from pydantic import SecretStr

from agentic_data_product.integrations.llm.base import LlmMessage

logger = logging.getLogger(__name__)


class OpenAICompatibleLlmClient:
    """HTTP client for OpenAI-compatible ``/chat/completions`` endpoints."""

    def __init__(
        self,
        *,
        api_key: SecretStr,
        model: str,
        base_url: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    def _complete_sync(self, messages: list[LlmMessage], temperature: float) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key.get_secret_value()}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logger.error("LLM HTTP error status=%s", exc.code)
            msg = f"LLM provider HTTP {exc.code}: {detail[:200]}"
            raise RuntimeError(msg) from exc
        except urllib.error.URLError as exc:
            logger.error("LLM transport error")
            msg = f"LLM provider unreachable: {exc.reason}"
            raise RuntimeError(msg) from exc

        data = json.loads(raw)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            msg = "Unexpected LLM response shape"
            raise RuntimeError(msg) from exc
        if not isinstance(content, str):
            msg = "LLM response content was not a string"
            raise TypeError(msg)
        return content

    async def complete(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float = 0.0,
    ) -> str:
        return await asyncio.to_thread(self._complete_sync, messages, temperature)
