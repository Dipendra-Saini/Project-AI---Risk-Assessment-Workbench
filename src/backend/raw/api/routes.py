from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from raw import config_store
from raw.api.deps import current_user, get_db, issue_token, require, verify_password
from raw.api.serializers import case_detail, case_summary
from raw.audit import chain
from raw.domain import ChangeType, Role, Status
from raw.graph import runner
from raw.models import AuditEvent, ChangeRequest, Control, LLMCall, PolicyChunk, User
from raw.rag.retriever import HybridRetriever
from raw.services import cases
from raw.services.assessment import latest_assessment
from raw.services.examiner import build_pack, to_html
from raw.settings import get_settings

api = APIRouter(prefix="/api")
PO, AN, CM = Role.PRODUCT_OWNER, Role.ANALYST, Role.COMMITTEE


# ---------- schemas ----------

class LoginIn(BaseModel):
    username: str
    password: str


class CaseIn(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10)
    change_type: ChangeType = ChangeType.OTHER
    business_line: str = ""
    launch_date: str | None = None
    document_text: str | None = None


class ExtractionEdit(BaseModel):
    field: str
    value: Any
    reason: str = ""


class FactorOverride(BaseModel):
    likelihood: int
    impact: int
    reason: str = ""


class ControlsIn(BaseModel):
    controls: list[dict[str, Any]]
    reason: str = ""


class NarrativeEdit(BaseModel):
    dimension: str
    text: str
    reason: str = ""


class SignOff(BaseModel):
    warnings_reason: str | None = None


class InfoRequest(BaseModel):
    message: str


class Rerun(BaseModel):
    scope: str = Field(pattern="^(full|draft)$")


class VoteIn(BaseModel):
    vote: str | None = None
    rationale: str = ""
    conflict: bool = False
    conditions: list[str] = []


class Note(BaseModel):
    note: str


class ConfigIn(BaseModel):
    content: dict[str, Any]
    note: str


# ---------- helpers ----------

def _case(db: Session, cr_id: int, user: User) -> ChangeRequest:
    cr = db.get(ChangeRequest, cr_id)
    if cr is None:
        raise HTTPException(404, "case not found")
    if user.role == PO and cr.created_by != user.id:
        raise HTTPException(403, "product owners can only access their own cases")
    return cr


def _detail(db: Session, cr: ChangeRequest) -> dict[str, Any]:
    db.commit()
    db.refresh(cr)
    return case_detail(db, cr)


def _commit_then(db: Session, fn, *args, **kwargs) -> None:
    """Commit the request transaction before handing work to the pipeline thread."""
    db.commit()
    fn(*args, **kwargs)


# ---------- auth ----------

@api.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == body.username)).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "invalid credentials")
    chain.record(db, user.username, "auth.login", "user", user.id, {})
    return {"token": issue_token(user), "user": {"id": user.id, "username": user.username, "name": user.name, "role": user.role}}


@api.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "username": user.username, "name": user.name, "role": user.role}


@api.get("/users/demo")
def demo_users(db: Session = Depends(get_db)):
    return [{"username": u.username, "name": u.name, "role": u.role} for u in db.execute(select(User).order_by(User.id)).scalars()]


# ---------- cases ----------

@api.get("/cases")
def list_cases(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = select(ChangeRequest).order_by(ChangeRequest.id.desc())
    if user.role == PO:
        q = q.where(ChangeRequest.created_by == user.id)
    if status:
        q = q.where(ChangeRequest.status.in_(status.split(",")))
    users = {u.id: u for u in db.execute(select(User)).scalars()}
    return [case_summary(cr, users, latest_assessment(db, cr.id)) for cr in db.execute(q).scalars()]


@api.post("/cases", status_code=201)
def create_case(body: CaseIn, db: Session = Depends(get_db), user: User = Depends(require(PO))):
    cr = cases.create_case(db, user, body.model_dump())
    if body.document_text:
        cases.add_document(db, cr, user, "submission.txt", body.document_text.encode(), "text/plain",
                           get_settings().max_upload_bytes)
    return _detail(db, cr)


@api.get("/cases/{cr_id}")
def get_case(cr_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return case_detail(db, _case(db, cr_id, user))


@api.post("/cases/{cr_id}/documents")
async def upload(cr_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require(PO))):
    cr = _case(db, cr_id, user)
    content = await file.read()
    cases.add_document(db, cr, user, file.filename or "upload", content, file.content_type or "", get_settings().max_upload_bytes)
    return _detail(db, cr)


@api.post("/cases/{cr_id}/extract")
def extract(cr_id: int, db: Session = Depends(get_db), user: User = Depends(require(PO))):
    cr = _case(db, cr_id, user)
    if Status(cr.status) not in {Status.DRAFT, Status.INFO_REQUESTED}:
        raise HTTPException(409, "extraction only runs before submission")
    if cr.pipeline_state == "running":
        raise HTTPException(409, "pipeline already running")
    if runner.waiting_at(cr) == "po_gate":
        _commit_then(db, runner.resume, cr.id, "re_extract")
    else:
        _commit_then(db, runner.start, cr.id, "intake")
    return _detail(db, cr)


@api.patch("/cases/{cr_id}/extraction")
def edit_extraction(cr_id: int, body: ExtractionEdit, db: Session = Depends(get_db), user: User = Depends(require(PO, AN))):
    cr = _case(db, cr_id, user)
    cases.edit_extraction(db, cr, user, body.field, body.value, body.reason)
    return _detail(db, cr)


@api.post("/cases/{cr_id}/submit")
def submit(cr_id: int, db: Session = Depends(get_db), user: User = Depends(require(PO))):
    cr = _case(db, cr_id, user)
    if runner.waiting_at(cr) != "po_gate":
        raise HTTPException(409, "run extraction and wait for it to finish before submitting")
    cases.confirm_intake(db, cr, user)
    _commit_then(db, runner.resume, cr.id, "confirm")
    return _detail(db, cr)


@api.post("/cases/{cr_id}/factors/{dim}/accept")
def accept_factor(cr_id: int, dim: str, db: Session = Depends(get_db), user: User = Depends(require(AN))):
    cr = _case(db, cr_id, user)
    cases.accept_factor(db, cr, user, dim)
    return _detail(db, cr)


@api.post("/cases/{cr_id}/factors/{dim}/override")
def override_factor(cr_id: int, dim: str, body: FactorOverride, db: Session = Depends(get_db),
                    user: User = Depends(require(AN))):
    cr = _case(db, cr_id, user)
    cases.override_factor(db, cr, user, dim, body.likelihood, body.impact, body.reason)
    return _detail(db, cr)


@api.put("/cases/{cr_id}/controls")
def put_controls(cr_id: int, body: ControlsIn, db: Session = Depends(get_db), user: User = Depends(require(AN))):
    cr = _case(db, cr_id, user)
    cases.set_controls(db, cr, user, body.controls, body.reason)
    return _detail(db, cr)


@api.post("/cases/{cr_id}/narrative/override")
def narrative_override(cr_id: int, body: NarrativeEdit, db: Session = Depends(get_db), user: User = Depends(require(AN))):
    cr = _case(db, cr_id, user)
    cases.override_narrative(db, cr, user, body.dimension, body.text, body.reason)
    return _detail(db, cr)


@api.post("/cases/{cr_id}/narrative/signoff")
def signoff(cr_id: int, body: SignOff, db: Session = Depends(get_db), user: User = Depends(require(AN))):
    cr = _case(db, cr_id, user)
    cases.signoff_narrative(db, cr, user, body.warnings_reason)
    return _detail(db, cr)


@api.post("/cases/{cr_id}/overrides/{oid}/ack")
def ack(cr_id: int, oid: int, db: Session = Depends(get_db), user: User = Depends(require(AN))):
    cr = _case(db, cr_id, user)
    cases.ack_override(db, cr, user, oid)
    return _detail(db, cr)


@api.post("/cases/{cr_id}/request-info")
def request_info(cr_id: int, body: InfoRequest, db: Session = Depends(get_db), user: User = Depends(require(AN))):
    cr = _case(db, cr_id, user)
    waiting = runner.waiting_at(cr)
    cases.request_info(db, cr, user, body.message)
    if waiting == "analyst_gate":
        _commit_then(db, runner.resume, cr.id, "request_info")
    else:
        _commit_then(db, runner.start, cr.id, "intake")
    return _detail(db, cr)


@api.post("/cases/{cr_id}/rerun")
def rerun(cr_id: int, body: Rerun, db: Session = Depends(get_db), user: User = Depends(require(AN))):
    cr = _case(db, cr_id, user)
    if cr.pipeline_state == "running":
        raise HTTPException(409, "pipeline already running")
    waiting = runner.waiting_at(cr)
    cases.prepare_rerun(db, cr, user, body.scope)
    if waiting == "analyst_gate":
        _commit_then(db, runner.resume, cr.id, "rerun" if body.scope == "full" else "redraft")
    else:
        if body.scope == "draft":
            raise HTTPException(409, "no active pipeline run to redraft; use a full rerun")
        _commit_then(db, runner.start, cr.id, "assess")
    return _detail(db, cr)


@api.post("/cases/{cr_id}/submit-to-committee")
def to_committee(cr_id: int, db: Session = Depends(get_db), user: User = Depends(require(AN))):
    cr = _case(db, cr_id, user)
    waiting = runner.waiting_at(cr)
    cases.submit_to_committee(db, cr, user)
    if waiting == "analyst_gate":
        _commit_then(db, runner.resume, cr.id, "complete")
    return _detail(db, cr)


@api.post("/cases/{cr_id}/votes")
def vote(cr_id: int, body: VoteIn, db: Session = Depends(get_db), user: User = Depends(require(CM))):
    cr = _case(db, cr_id, user)
    cases.cast_vote(db, cr, user, body.vote, body.rationale, body.conflict, body.conditions)
    return _detail(db, cr)


@api.post("/cases/{cr_id}/decision")
def decision(cr_id: int, db: Session = Depends(get_db), user: User = Depends(require(CM))):
    cr = _case(db, cr_id, user)
    cases.decide(db, cr, user)
    return _detail(db, cr)


@api.post("/cases/{cr_id}/return-to-analyst")
def return_to_analyst(cr_id: int, body: Note, db: Session = Depends(get_db), user: User = Depends(require(CM))):
    cr = _case(db, cr_id, user)
    cases.return_to_analyst(db, cr, user, body.note)
    return _detail(db, cr)


@api.post("/cases/{cr_id}/reopen")
def reopen(cr_id: int, db: Session = Depends(get_db), user: User = Depends(require(AN))):
    cr = _case(db, cr_id, user)
    cases.reopen_deferred(db, cr, user)
    return _detail(db, cr)


@api.get("/cases/{cr_id}/examiner-pack")
def examiner_pack(cr_id: int, format: str = "json", db: Session = Depends(get_db), user: User = Depends(current_user)):
    cr = _case(db, cr_id, user)
    pack = build_pack(db, cr, user.username)
    if format == "html":
        return HTMLResponse(to_html(pack))
    return pack


# ---------- reference data, config, audit, ops ----------

@api.get("/controls")
def list_controls(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return [{"id": c.id, "name": c.name, "dims": c.dims, "design": c.design, "operating": c.operating}
            for c in db.execute(select(Control).order_by(Control.id)).scalars()]


@api.get("/policy/chunks/{chunk_id}")
def get_chunk(chunk_id: str, db: Session = Depends(get_db), _: User = Depends(current_user)):
    c = db.get(PolicyChunk, chunk_id)
    if c is None:
        raise HTTPException(404, "chunk not found")
    return {"id": c.id, "doc_title": c.doc_title, "section_title": c.section_title, "text": c.text, "tags": c.tags,
            "source_url": c.source_url}


@api.get("/policy/search")
def search(q: str, db: Session = Depends(get_db), _: User = Depends(current_user)):
    r = HybridRetriever(db)
    return [{"id": h.chunk_id, "score": h.score, "title": r.by_id[h.chunk_id].section_title,
             "text": r.by_id[h.chunk_id].text[:300]} for h in r.search(q, k=8)]


@api.get("/config")
def get_config(db: Session = Depends(get_db), _: User = Depends(current_user)):
    cv = config_store.active(db)
    return {"id": cv.id, "version": cv.version, "hash": cv.content_hash, "note": cv.note, "created_by": cv.created_by,
            "created_at": cv.created_at.isoformat(), "content": cv.content}


@api.get("/config/history")
def config_history(db: Session = Depends(get_db), _: User = Depends(current_user)):
    from raw.models import ConfigVersion

    return [{"id": c.id, "version": c.version, "hash": c.content_hash, "note": c.note, "created_by": c.created_by,
             "created_at": c.created_at.isoformat()}
            for c in db.execute(select(ConfigVersion).order_by(ConfigVersion.version.desc())).scalars()]


@api.post("/config")
def save_config(body: ConfigIn, db: Session = Depends(get_db), user: User = Depends(require(AN))):
    cv = config_store.create_version(db, body.content, user.username, body.note)
    return {"id": cv.id, "version": cv.version, "hash": cv.content_hash}


@api.get("/audit")
def audit(case_id: int | None = None, limit: int = 200, db: Session = Depends(get_db), user: User = Depends(require(AN, CM))):
    q = select(AuditEvent).order_by(AuditEvent.seq.desc()).limit(min(limit, 1000))
    if case_id:
        q = q.where(AuditEvent.entity_type == "change_request", AuditEvent.entity_id == str(case_id))
    return [{"seq": e.seq, "ts": e.ts, "actor": e.actor, "action": e.action, "entity_type": e.entity_type,
             "entity_id": e.entity_id, "payload": e.payload, "hash": e.hash, "prev_hash": e.prev_hash}
            for e in db.execute(q).scalars()]


@api.get("/audit/verify")
def audit_verify(db: Session = Depends(get_db), _: User = Depends(require(AN, CM))):
    return chain.verify(db)


@api.get("/ops/tokens")
def tokens(db: Session = Depends(get_db), _: User = Depends(require(AN, CM))):
    rows = db.execute(
        select(LLMCall.node, LLMCall.provider, LLMCall.model, LLMCall.status, func.count(LLMCall.id),
               func.sum(LLMCall.input_tokens), func.sum(LLMCall.output_tokens), func.sum(LLMCall.estimated_tokens))
        .group_by(LLMCall.node, LLMCall.provider, LLMCall.model, LLMCall.status)
    ).all()
    per_case = db.execute(select(LLMCall.cr_id, func.sum(LLMCall.input_tokens + LLMCall.output_tokens))
                          .group_by(LLMCall.cr_id)).all()
    return {
        "rows": [{"node": r[0], "provider": r[1], "model": r[2], "status": r[3], "calls": r[4], "input_tokens": r[5] or 0,
                  "output_tokens": r[6] or 0, "estimated_tokens": r[7] or 0} for r in rows],
        "per_case": [{"cr_id": c, "tokens": t or 0} for c, t in per_case if c is not None],
        "budget_per_case": get_settings().token_budget_per_case,
        "mode": get_settings().llm_mode,
    }
