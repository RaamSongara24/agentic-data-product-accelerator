"""LLM client protocol — providers live under integrations/, not in graph state."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class LlmMessage(BaseModel):
    """One chat message exchanged with an LLM provider."""

    model_config = ConfigDict(extra="forbid")

    role: str = Field(min_length=1)
    content: str


@runtime_checkable
class LlmClient(Protocol):
    """Minimal chat-completion interface used by agents."""

    @property
    def provider_name(self) -> str:
        """Stable provider identifier for observability."""

    async def complete(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float = 0.0,
    ) -> str:
        """Return the assistant text completion for ``messages``."""
