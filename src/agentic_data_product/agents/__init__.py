"""Agent packages for canonical artefact generation."""

from agentic_data_product.agents.requirements import (
    GOLDEN_REQUIRED_BEHAVIOURS,
    GOLDEN_TR_SUMMARY_PREFIX,
    generate_technical_requirement,
    generate_technical_requirement_deterministic,
)

__all__ = [
    "GOLDEN_REQUIRED_BEHAVIOURS",
    "GOLDEN_TR_SUMMARY_PREFIX",
    "generate_technical_requirement",
    "generate_technical_requirement_deterministic",
]
