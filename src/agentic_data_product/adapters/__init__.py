"""Platform adapters (Databricks first; others later).

Maps **approved** canonical artefacts to platform-specific export stubs.
Live deploy is out of scope for MVP (ADR 004).
"""

from agentic_data_product.adapters.base import PlatformAdapter
from agentic_data_product.adapters.databricks import DatabricksAdapter
from agentic_data_product.adapters.errors import (
    AdapterApprovalRequiredError,
    AdapterError,
    AdapterInputError,
)
from agentic_data_product.adapters.types import (
    AdapterAsset,
    AdapterResult,
    AdapterTargetConfig,
)

__all__ = [
    "AdapterApprovalRequiredError",
    "AdapterAsset",
    "AdapterError",
    "AdapterInputError",
    "AdapterResult",
    "AdapterTargetConfig",
    "DatabricksAdapter",
    "PlatformAdapter",
]
