"""Unit tests for checkpointer URL helpers."""

from agentic_data_product.orchestration.checkpointer import psycopg_conninfo


def test_psycopg_conninfo_strips_asyncpg_driver() -> None:
    assert (
        psycopg_conninfo("postgresql+asyncpg://adp:adp@localhost:5432/adp")
        == "postgresql://adp:adp@localhost:5432/adp"
    )


def test_psycopg_conninfo_passthrough() -> None:
    url = "postgresql://adp:adp@localhost:5432/adp"
    assert psycopg_conninfo(url) == url
