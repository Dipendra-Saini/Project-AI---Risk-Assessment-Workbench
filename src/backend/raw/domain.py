"""Domain vocabulary and the AI-facing schemas."""

from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


class Role(StrEnum):
    PRODUCT_OWNER = "product_owner"
    ANALYST = "analyst"
    COMMITTEE = "committee"


class Status(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    IN_ASSESSMENT = "IN_ASSESSMENT"
    ANALYST_REVIEW = "ANALYST_REVIEW"
    INFO_REQUESTED = "INFO_REQUESTED"
    COMMITTEE_REVIEW = "COMMITTEE_REVIEW"
    APPROVED = "APPROVED"
    APPROVED_WITH_CONDITIONS = "APPROVED_WITH_CONDITIONS"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


TERMINAL_STATUSES = frozenset(
    {Status.APPROVED, Status.APPROVED_WITH_CONDITIONS, Status.REJECTED, Status.DEFERRED}
)


class ChangeType(StrEnum):
    NEW_PRODUCT = "new_product"
    FEATURE_CHANGE = "feature_change"
    PROCESS_CHANGE = "process_change"
    VENDOR_ONBOARDING = "vendor_onboarding"
    NEW_GEOGRAPHY = "new_geography"
    NEW_CUSTOMER_SEGMENT = "new_customer_segment"
    OTHER = "other"


class Vote(StrEnum):
    APPROVE = "APPROVE"
    APPROVE_WITH_CONDITIONS = "APPROVE_WITH_CONDITIONS"
    REJECT = "REJECT"
    DEFER = "DEFER"


VOTE_TO_STATUS = {
    Vote.APPROVE: Status.APPROVED,
    Vote.APPROVE_WITH_CONDITIONS: Status.APPROVED_WITH_CONDITIONS,
    Vote.REJECT: Status.REJECTED,
    Vote.DEFER: Status.DEFERRED,
}

DIMENSIONS = ["PRD", "CUS", "GEO", "CHN", "TRX", "TPV"]

CUSTOMER_TYPES = [
    "retail", "small_business", "corporate", "pep", "msb", "non_resident",
    "nonprofit", "high_net_worth",
]
CHANNELS = ["branch", "online", "mobile", "api", "agent", "phone"]
THIRD_PARTY_ROLES = [
    "kyc", "transaction_monitoring", "payments_processing", "custody", "marketing",
    "it_hosting",
]
FLAGS = ["cross_border", "cash", "crypto", "instant_payments", "anonymous_or_prepaid"]

T = TypeVar("T")


class Extracted(BaseModel, Generic[T]):
    value: T
    confidence: float = Field(ge=0, le=1, default=0.5)
    source_span: str = ""
    origin: str = "ai"  # ai | offline | human


class IntakeExtraction(BaseModel):
    """What the extractor must return. Every field carries its evidence."""

    customer_types: Extracted[list[str]]
    geographies: Extracted[list[str]]
    channels: Extracted[list[str]]
    third_parties: Extracted[list[str]]
    third_party_roles: Extracted[list[str]]
    cross_border: Extracted[bool]
    cash: Extracted[bool]
    crypto: Extracted[bool]
    instant_payments: Extracted[bool]
    anonymous_or_prepaid: Extracted[bool]
    monthly_value_usd: Extracted[float | None]
    monthly_volume: Extracted[int | None]
    proposed_controls: Extracted[list[str]]


EXTRACTION_FIELDS = list(IntakeExtraction.model_fields)


class ClassifyResult(BaseModel):
    change_type: ChangeType
    confidence: float = Field(ge=0, le=1)


class FactorSuggestion(BaseModel):
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    rationale: str
    citations: list[str] = []


class NarrativeSection(BaseModel):
    dimension: str
    text: str


class Narrative(BaseModel):
    """No outcome field on purpose (ADR-006)."""

    summary: str
    sections: list[NarrativeSection]
    suggested_conditions: list[str] = []


class ClaimVerdict(BaseModel):
    index: int
    supported: bool
    reason: str = ""


class CritiqueResult(BaseModel):
    verdicts: list[ClaimVerdict]


def plain(extraction: dict[str, Any]) -> dict[str, Any]:
    """Collapse an extraction dict to {field: value}."""
    return {k: (v.get("value") if isinstance(v, dict) else v) for k, v in extraction.items()}
