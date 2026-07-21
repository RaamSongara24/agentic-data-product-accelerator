"""FastAPI dependency providers."""

from agentic_data_product.config import Settings, get_settings
from agentic_data_product.persistence import Database, PostgresArtefactStore, get_database


def settings_dep() -> Settings:
    return get_settings()


def database_dep() -> Database:
    return get_database()


def artefact_store_dep() -> PostgresArtefactStore:
    database = get_database()
    return PostgresArtefactStore(database.session_factory)
