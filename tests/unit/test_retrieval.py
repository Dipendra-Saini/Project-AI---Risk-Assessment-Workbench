from raw.models import PolicyChunk
from raw.rag.ingest import POLICY_DIR, ingest, parse_policy
from raw.rag.retriever import HybridRetriever


def test_policy_chunks_have_stable_ids_and_tags():
    chunks = [c for p in POLICY_DIR.glob("*.md") for c in parse_policy(p)]
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids)) >= 40
    assert all(c["tags"] and c["text"] for c in chunks)


def test_rule_citations_exist_in_corpus():
    from raw.config_store import seed_config

    ids = {c["id"] for p in POLICY_DIR.glob("*.md") for c in parse_policy(p)}
    missing = {r["cite"] for r in seed_config()["rules"]} - ids
    assert missing == set()


def test_ingest_is_idempotent(session):
    first = ingest(session)
    second = ingest(session)
    assert first["embedded"] == first["chunks"]
    assert second["embedded"] == 0
    assert session.query(PolicyChunk).count() == first["chunks"]


def test_hybrid_retrieval_finds_relevant_sections(session):
    ingest(session)
    r = HybridRetriever(session)
    hits = r.search("virtual assets crypto custody wallet screening", dims=["PRD"], k=5)
    ids = [h.chunk_id for h in hits]
    assert "NPA-POL-3.3" in ids
    hits = r.search("politically exposed persons source of wealth", dims=["CUS"], k=3)
    assert hits[0].chunk_id == "AML-POL-3.3"
