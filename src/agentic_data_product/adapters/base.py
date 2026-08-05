"""PlatformAdapter boundary — approved canonical artefacts → platform exports."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from agentic_data_product.adapters.types import AdapterResult, AdapterTargetConfig
from agentic_data_product.domain.artefacts import CanonicalArtefact


class PlatformAdapter(ABC):
    """Translate **approved** canonical artefacts into platform-specific exports.

    Agents never call adapter write APIs during generation. Live deploy is out of
    scope for MVP; implementations may return stub/export bundles only.
    """

    @property
    @abstractmethod
    def platform_id(self) -> str:
        """Stable platform identifier (e.g. ``databricks``)."""

    @abstractmethod
    def to_platform(
        self,
        artefacts: Sequence[CanonicalArtefact],
        target_config: AdapterTargetConfig,
    ) -> AdapterResult:
        """Map approved artefacts to platform-shaped assets.

        Implementations must:
        - Reject inputs that are not approved (Review Package ``decision_state``).
        - Derive all outputs from the provided canonical artefacts only.
        - Propagate ``governance_metadata`` when present on source artefacts.
        - Never elevate source-platform permissions or invent inaccessible entities.
        """
