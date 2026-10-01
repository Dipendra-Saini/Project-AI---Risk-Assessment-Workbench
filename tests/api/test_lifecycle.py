from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

GOLDEN = {c["id"]: c for c in yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "evals/datasets/golden_v1.yaml").read_text())["cases"]}


@pytest.fixture()
def client(db):
    from raw.graph import runner
    from raw.main import app
    from raw.rag.embeddings import get_embedder

    get_embedder.cache_clear()
    runner.reset_graph()
    with TestClient(app) as c:
        yield c
    runner.reset_graph()


def login(client, username):
    r = client.post("/api/auth/login", json={"username": username, "password": "demo"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def new_case(client, po, gid):
    g = GOLDEN[gid]
    r = client.post("/api/cases", headers=po, json={"title": g["title"], "description": g["description"],
                                                     "change_type": g["change_type"], "business_line": g["business_line"],
                                                     "document_text": g["document"]})
    assert r.status_code == 201, r.text
    return r.json()


def to_analyst(client, po, gid):
    case = new_case(client, po, gid)
    cid = case["id"]
    r = client.post(f"/api/cases/{cid}/extract", headers=po)
    assert r.status_code == 200, r.text
    assert r.json()["waiting_at"] == "po_gate"
    r = client.post(f"/api/cases/{cid}/submit", headers=po)
    assert r.status_code == 200, r.text
    return r.json()


def test_us01_to_us15_full_lifecycle(client):
    po, an, an2 = login(client, "priya"), login(client, "arjun"), login(client, "sara")
    cm = {u: login(client, u) for u in ("meera", "dev", "lina", "kofi")}

    case = new_case(client, po, "G01")
    cid = case["id"]
    assert case["status"] == "DRAFT"

    case = client.post(f"/api/cases/{cid}/extract", headers=po).json()
    ext = case["extraction"]
    assert ext and not ext["confirmed"]
    assert all("source_span" in v for v in ext["data"].values())  # US-02

    r = client.patch(f"/api/cases/{cid}/extraction", headers=po, json={"field": "monthly_volume", "value": 400000})
    assert r.status_code == 422  # reason required
    r = client.patch(f"/api/cases/{cid}/extraction", headers=po,
                     json={"field": "monthly_volume", "value": 400000, "reason": "Volume confirmed by product finance"})
    assert r.status_code == 200

    case = client.post(f"/api/cases/{cid}/submit", headers=po).json()
    assert case["status"] == "ANALYST_REVIEW", case["warnings"]
    assert case["gates"]["G0"]["passed"]
    a = case["assessment"]
    assert {f["dimension"] for f in a["factors"]} == {"PRD", "CUS", "GEO", "CHN", "TRX", "TPV"}
    assert 0 < a["residual"] <= a["inherent"]
    assert a["narrative"]["sections"] and a["critique"]["claims"]
    assert "outcome" not in a["narrative"]  # ADR-006

    r = client.post(f"/api/cases/{cid}/submit-to-committee", headers=an)
    assert r.status_code == 422 and "narrative not signed" in r.json()["detail"]

    before = a["residual_tier"]
    r = client.post(f"/api/cases/{cid}/factors/TPV/override", headers=an,
                    json={"likelihood": 5, "impact": 5, "reason": "Processor is unregulated in two corridors"})
    assert r.status_code == 200
    case = r.json()
    o = case["overrides"][-1]
    assert o["tier_before"] == before
    assert case["assessment"]["narrative_stale"]
    assert client.post(f"/api/cases/{cid}/narrative/signoff", headers=an, json={}).status_code == 422

    case = client.post(f"/api/cases/{cid}/rerun", headers=an, json={"scope": "draft"}).json()
    assert not case["assessment"]["narrative_stale"]
    r = client.post(f"/api/cases/{cid}/narrative/signoff", headers=an,
                    json={"warnings_reason": "Reviewed flagged sentences; policy basis confirmed manually"})
    assert r.status_code == 200, r.text

    if o["requires_ack"]:  # US-08
        r = client.post(f"/api/cases/{cid}/submit-to-committee", headers=an)
        assert r.status_code == 422 and "second analyst" in r.json()["detail"]
        assert client.post(f"/api/cases/{cid}/overrides/{o['id']}/ack", headers=an).status_code == 422  # self-ack
        assert client.post(f"/api/cases/{cid}/overrides/{o['id']}/ack", headers=an2).status_code == 200

    case = client.post(f"/api/cases/{cid}/submit-to-committee", headers=an).json()
    assert case["status"] == "COMMITTEE_REVIEW"

    assert client.post(f"/api/cases/{cid}/votes", headers=po, json={"vote": "APPROVE"}).status_code == 403
    cond = ["Velocity limit of USD 2,000 per day for the first 90 days"]
    for u in ("meera", "dev"):
        r = client.post(f"/api/cases/{cid}/votes", headers=cm[u], json={
            "vote": "APPROVE_WITH_CONDITIONS", "rationale": "Acceptable with limits in place", "conditions": cond})
        assert r.status_code == 200, r.text
    client.post(f"/api/cases/{cid}/votes", headers=cm["lina"], json={"conflict": True})
    r = client.post(f"/api/cases/{cid}/decision", headers=cm["meera"])
    assert r.status_code == 409 and "quorum" in r.json()["detail"]  # US-11
    client.post(f"/api/cases/{cid}/votes", headers=cm["kofi"], json={
        "vote": "APPROVE_WITH_CONDITIONS", "rationale": "Agree, with the 90-day review", "conditions": cond})
    case = client.post(f"/api/cases/{cid}/decision", headers=cm["meera"]).json()
    assert case["status"] == "APPROVED_WITH_CONDITIONS"
    assert case["decisions"][0]["conditions"] == cond

    pack = client.get(f"/api/cases/{cid}/examiner-pack", headers=an).json()  # US-15
    assert pack["chain_verification"]["valid"]
    assert pack["overrides"] and pack["votes"] and pack["decisions"]
    assert any(e["action"] == "committee.decision" for e in pack["audit_events"])
    assert client.get(f"/api/cases/{cid}/examiner-pack?format=html", headers=an).status_code == 200
    assert client.get("/api/audit/verify", headers=an).json()["valid"]  # US-14


def test_us09_ai_suggestions_block_committee_until_confirmed(client):
    po, an = login(client, "priya"), login(client, "arjun")
    case = to_analyst(client, po, "G18")
    cid = case["id"]
    pending = [f["dimension"] for f in case["assessment"]["factors"] if f["origin"] in ("ai", "offline")]
    assert pending, "incomplete case must leave dimensions for AI suggestion"
    assert not case["gates"]["G1"]["passed"]
    r = client.post(f"/api/cases/{cid}/narrative/signoff", headers=an,
                    json={"warnings_reason": "Narrative reviewed line by line by the analyst"})
    assert r.status_code == 200
    r = client.post(f"/api/cases/{cid}/submit-to-committee", headers=an)
    assert r.status_code == 422 and pending[0] in r.json()["detail"]
    for d in pending:
        assert client.post(f"/api/cases/{cid}/factors/{d}/accept", headers=an).status_code == 200
    assert client.post(f"/api/cases/{cid}/submit-to-committee", headers=an).json()["status"] == "COMMITTEE_REVIEW"


def test_us16_prompt_injection_is_flagged_and_ignored(client):
    po = login(client, "priya")
    case = to_analyst(client, po, "G17")
    assert any("prompt injection" in w for w in case["warnings"])
    assert case["assessment"]["residual_tier"] in {"Medium", "High", "Critical"}


def test_request_info_round_trip(client):
    po, an = login(client, "priya"), login(client, "arjun")
    cid = to_analyst(client, po, "G03")["id"]
    case = client.post(f"/api/cases/{cid}/request-info", headers=an,
                       json={"message": "Please confirm whether deposits can be made in cash."}).json()
    assert case["status"] == "INFO_REQUESTED" and case["waiting_at"] == "po_gate"
    r = client.post(f"/api/cases/{cid}/documents", headers=po,
                    files={"file": ("answer.txt", b"Deposits are never in cash; transfers only.", "text/plain")})
    assert r.status_code == 200
    assert client.post(f"/api/cases/{cid}/extract", headers=po).json()["extraction"]["version"] == 2
    case = client.post(f"/api/cases/{cid}/submit", headers=po).json()
    assert case["status"] == "ANALYST_REVIEW" and case["assessment"]["version"] == 2


def test_rbac_and_ownership(client):
    priya, omar, an = login(client, "priya"), login(client, "omar"), login(client, "arjun")
    cid = new_case(client, priya, "G03")["id"]
    assert client.get(f"/api/cases/{cid}", headers=omar).status_code == 403
    assert client.post("/api/cases", headers=an, json={"title": "x" * 6, "description": "y" * 12}).status_code == 403
    assert client.get("/api/audit", headers=priya).status_code == 403
    assert client.get("/api/cases").status_code == 401


def test_us13_config_versioning(client):
    an = login(client, "arjun")
    cfg = client.get("/api/config", headers=an).json()
    content = cfg["content"]
    content["scoring"]["mitigation_cap"] = 1.0
    assert client.post("/api/config", headers=an, json={"content": content, "note": "try full mitigation"}).status_code == 422
    content["scoring"]["mitigation_cap"] = 0.6
    r = client.post("/api/config", headers=an, json={"content": content, "note": "tighten mitigation cap"})
    assert r.status_code == 200 and r.json()["version"] == cfg["version"] + 1
    assert client.get("/api/config/history", headers=an).json()[0]["note"] == "tighten mitigation cap"
