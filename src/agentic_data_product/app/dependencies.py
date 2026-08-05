"""FastAPI dependency providers."""

from agentic_data_product.config import Settings, get_settings
from agentic_data_product.persistence import Database, get_database


def settings_dep() -> Settings:
    return get_settings()


def database_dep() -> Database:
    return get_database()
