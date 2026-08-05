"""Deterministic LLM stand-in for tests and offline development."""

from __future__ import annotations

from agentic_data_product.integrations.llm.base import LlmMessage


class DeterministicLlmClient:
    """Returns a fixed JSON-shaped completion derived from the last user message.

    The Requirements Agent prefers its own heuristic path when this provider is
    selected; ``complete`` remains available for optional prompt-shaped flows.
    """

    @property
    def provider_name(self) -> str:
        return "deterministic"

    async def complete(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float = 0.0,
    ) -> str:
        _ = temperature
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "",
        )
        # Echo a compact acknowledgement — agents should not rely on free-form text
        # when the deterministic requirements path is active.
        return f'{{"provider":"deterministic","ack":true,"user_chars":{len(last_user)}}}'
