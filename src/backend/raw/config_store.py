"""Versioned, analyst-tunable configuration (FR-18)."""

import copy
from functools import lru_cache
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from raw.audit import chain
from raw.models import ConfigVersion
from raw.scoring.engine import config_hash, validate_config
from raw.settings import get_settings


@lru_cache
def seed_config() -> dict[str, Any]:
    with open(get_settings().config_dir / "v1.yaml") as f:
        return yaml.safe_load(f)


@lru_cache
def control_library() -> list[dict[str, Any]]:
    with open(get_settings().config_dir / "controls.yaml") as f:
        return yaml.safe_load(f)["controls"]


def active(session: Session) -> ConfigVersion:
    cv = session.execute(select(ConfigVersion).order_by(ConfigVersion.version.desc()).limit(1)).scalar_one_or_none()
    if cv is None:
        cv = _create(session, copy.deepcopy(seed_config()), "system", "seed from config/v1.yaml")
    return cv


def get(session: Session, config_version_id: int) -> ConfigVersion:
    cv = session.get(ConfigVersion, config_version_id)
    if cv is None:
        raise KeyError(config_version_id)
    return cv


def _create(session: Session, content: dict[str, Any], actor: str, note: str) -> ConfigVersion:
    validate_config(content["scoring"])
    wf = content["workflow"]
    if wf["quorum"] < 1:
        raise ValueError("quorum must be >= 1")
    if wf["tie_outcome"] not in {"DEFERRED", "REJECTED"}:
        raise ValueError("tie_outcome must be DEFERRED or REJECTED (never an approval)")
    last = session.execute(select(ConfigVersion).order_by(ConfigVersion.version.desc()).limit(1)).scalar_one_or_none()
    cv = ConfigVersion(
        version=(last.version + 1) if last else 1,
        content=content,
        content_hash=config_hash(content),
        note=note,
        created_by=actor,
    )
    session.add(cv)
    session.flush()
    chain.record(session, actor, "config.version_created", "config", cv.version,
                 {"hash": cv.content_hash, "note": note, "previous": last.version if last else None})
    return cv


def create_version(session: Session, content: dict[str, Any], actor: str, note: str) -> ConfigVersion:
    if not note or len(note.strip()) < 5:
        raise ValueError("a change note is required")
    return _create(session, content, actor, note)
