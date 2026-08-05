"""Fixture-first source catalogue for discovery (simulates Unity Catalog visibility)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from agentic_data_product.domain.artefacts import GovernanceMetadata


class FixtureColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    nullable: bool = True
    description: str | None = None


class FixtureObject(BaseModel):
    """One catalogue object with ACL simulating source-platform permissions."""

    model_config = ConfigDict(extra="forbid")

    object_id: str = Field(min_length=1, description="Fully-qualified object id")
    display_name: str = Field(min_length=1)
    object_type: str = Field(default="table")
    description: str = ""
    columns: list[FixtureColumn] = Field(default_factory=list)
    allowed_principals: list[str] = Field(
        default_factory=list,
        description="User ids permitted to see this object in fixture mode",
    )
    governance_metadata: GovernanceMetadata | None = None


# Catalogue intentionally mixes accessible and restricted objects for the default
# consultant principal used in golden/API tests.
FIXTURE_CATALOGUE: tuple[FixtureObject, ...] = (
    FixtureObject(
        object_id="analytics.sales.orders",
        display_name="Orders",
        description="Customer order header facts",
        allowed_principals=["consultant", "analyst", "data_engineer"],
        columns=[
            FixtureColumn(name="order_id", data_type="string", nullable=False),
            FixtureColumn(name="customer_id", data_type="string", nullable=False),
            FixtureColumn(name="order_date", data_type="date", nullable=False),
            FixtureColumn(name="order_amount", data_type="decimal", nullable=False),
            FixtureColumn(name="status", data_type="string"),
        ],
        governance_metadata=GovernanceMetadata(
            classifications=["internal"],
            sensitivity_labels=["commercial"],
        ),
    ),
    FixtureObject(
        object_id="analytics.sales.customers",
        display_name="Customers",
        description="Customer dimension",
        allowed_principals=["consultant", "analyst", "data_engineer"],
        columns=[
            FixtureColumn(name="customer_id", data_type="string", nullable=False),
            FixtureColumn(name="customer_name", data_type="string", nullable=False),
            FixtureColumn(name="region", data_type="string"),
            FixtureColumn(name="segment", data_type="string"),
        ],
        governance_metadata=GovernanceMetadata(classifications=["internal"]),
    ),
    FixtureObject(
        object_id="analytics.sales.products",
        display_name="Products",
        description="Product dimension",
        allowed_principals=["consultant", "analyst", "data_engineer"],
        columns=[
            FixtureColumn(name="product_id", data_type="string", nullable=False),
            FixtureColumn(name="product_name", data_type="string", nullable=False),
            FixtureColumn(name="category", data_type="string"),
        ],
    ),
    # Restricted — must never appear for consultant / analyst principals.
    FixtureObject(
        object_id="hr.payroll.salaries",
        display_name="Salaries",
        description="Employee compensation (restricted)",
        allowed_principals=["hr_admin"],
        columns=[
            FixtureColumn(name="employee_id", data_type="string", nullable=False),
            FixtureColumn(name="salary", data_type="decimal", nullable=False),
            FixtureColumn(name="currency", data_type="string", nullable=False),
        ],
        governance_metadata=GovernanceMetadata(
            classifications=["confidential"],
            sensitivity_labels=["pii", "compensation"],
            access_notes=["HR-only"],
        ),
    ),
    FixtureObject(
        object_id="security.audit.access_logs",
        display_name="Access logs",
        description="Platform access audit trail (restricted)",
        allowed_principals=["security_admin"],
        columns=[
            FixtureColumn(name="event_id", data_type="string", nullable=False),
            FixtureColumn(name="principal", data_type="string", nullable=False),
            FixtureColumn(name="action", data_type="string", nullable=False),
        ],
        governance_metadata=GovernanceMetadata(
            classifications=["restricted"],
            sensitivity_labels=["security"],
        ),
    ),
)

INACCESSIBLE_OBJECT_IDS: frozenset[str] = frozenset(
    obj.object_id for obj in FIXTURE_CATALOGUE if "consultant" not in obj.allowed_principals
)
