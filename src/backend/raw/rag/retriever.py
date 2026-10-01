"""Hybrid retrieval: BM25 + vector cosine, fused with reciprocal rank fusion.

No LLM involved (ADR-003). Postgres uses pgvector for the vector leg; SQLite
uses numpy over stored vectors (the corpus is small).
"""

from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from raw.models import PolicyChunk
from raw.rag.embeddings import embed_with_fallback
from raw.rag.text import tokenize

RRF_K = 60
TAG_BOOST = 0.005


@dataclass
class Hit:
    chunk_id: str
    score: float
    bm25_rank: int | None
    vector_rank: int | None
    tag_match: bool


class HybridRetriever:
    def __init__(self, session: Session):
        self.session = session
        self.chunks: list[PolicyChunk] = list(session.execute(select(PolicyChunk).order_by(PolicyChunk.id)).scalars())
        self.by_id = {c.id: c for c in self.chunks}
        self.bm25 = BM25Okapi([tokenize(f"{c.id} {c.section_title} {c.text}") for c in self.chunks]) if self.chunks else None
        self.is_pg = session.bind is not None and session.bind.dialect.name == "postgresql"
        self._matrix = None

    def _vector_ranks(self, query: str, n: int) -> list[str]:
        model, [qv] = embed_with_fallback([query])
        usable = [c for c in self.chunks if c.embedding is not None and c.embed_model == model]
        if not usable:
            return []
        if self.is_pg:
            rows = self.session.execute(
                text("SELECT id FROM policy_chunks WHERE embed_model = :m ORDER BY embedding <=> CAST(:q AS vector) LIMIT :n"),
                {"m": model, "q": str(qv), "n": n},
            ).all()
            return [r[0] for r in rows]
        if self._matrix is None:
            self._matrix = (np.asarray([c.embedding for c in usable], dtype=np.float32), [c.id for c in usable])
        mat, ids = self._matrix
        sims = mat @ np.asarray(qv, dtype=np.float32)
        return [ids[i] for i in np.argsort(-sims)[:n]]

    def search(self, query: str, dims: list[str] | None = None, k: int = 5) -> list[Hit]:
        if not self.chunks:
            return []
        n = min(len(self.chunks), 30)
        bm = self.bm25.get_scores(tokenize(query))
        bm_order = [self.chunks[i].id for i in np.argsort(-bm)[:n] if bm[i] > 0]
        vec_order = self._vector_ranks(query, n)
        scores: dict[str, float] = {}
        bm_rank = {cid: r for r, cid in enumerate(bm_order, 1)}
        vec_rank = {cid: r for r, cid in enumerate(vec_order, 1)}
        for cid in set(bm_order) | set(vec_order):
            s = 0.0
            if cid in bm_rank:
                s += 1 / (RRF_K + bm_rank[cid])
            if cid in vec_rank:
                s += 1 / (RRF_K + vec_rank[cid])
            if dims and set(self.by_id[cid].tags) & set(dims):
                s += TAG_BOOST
            scores[cid] = s
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
        return [
            Hit(cid, round(s, 5), bm_rank.get(cid), vec_rank.get(cid), bool(dims and set(self.by_id[cid].tags) & set(dims)))
            for cid, s in ranked
        ]


def corpus_size(session: Session) -> int:
    return session.execute(select(func.count(PolicyChunk.id))).scalar() or 0
