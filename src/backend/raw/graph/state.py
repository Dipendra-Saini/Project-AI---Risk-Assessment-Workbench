from typing import Any, TypedDict


class CaseState(TypedDict, total=False):
    """Orchestration state only. Facts live in the DB (source of truth)."""

    cr_id: int
    entry: str  # intake | assess
    extraction_id: int | None
    assessment_id: int | None
    retrieval: dict[str, list[dict[str, Any]]]
    context_pack: str
    warnings: list[str]
    redraft_count: int
    critic_feedback: str
    unsupported: int
    loop: bool
    action: str  # last human action at an interrupt
