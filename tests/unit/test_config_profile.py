"""Unit tests for runtime config profile endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_config_profile_ok(client: AsyncClient) -> None:
    response = await client.get("/config/profile")
    assert response.status_code == 200
    payload = response.json()
    assert payload["profile_name"].endswith("-default")
    assert payload["llm_provider"] in {"deterministic", "openai_compatible"}
    assert "llm_api_key" not in payload
    assert payload["graph"] == "hitl_seven_artefact"
    assert isinstance(payload["mapping_schema_retry_cap"], int)


@pytest.mark.asyncio
async def test_ui_index_served(client: AsyncClient) -> None:
    response = await client.get("/ui/")
    assert response.status_code == 200
    assert "Consultant review workspace" in response.text
    assert "Approve" in response.text
    assert "Request revisions" in response.text


@pytest.mark.asyncio
async def test_root_redirects_to_ui(client: AsyncClient) -> None:
    response = await client.get("/", follow_redirects=False)
    assert response.status_code in {307, 302}
    assert response.headers["location"] == "/ui/"
