# ADR-003: Hybrid retrieval (BM25 + embeddings) on pgvector, no LLM

Status: Accepted

## Context
Analysts need the right policy passage for each risk dimension, with a stable
citation id. Policy text is full of exact terms ("MSB", "PEP", "correspondent")
where lexical match matters, and paraphrases where semantic match matters.

## Options
- BM25 only: great on exact terms, misses paraphrase.
- Vectors only: good on paraphrase, misses acronyms and section codes.
- LLM re-ranking: costs tokens on every case.
- **Hybrid with reciprocal-rank fusion (RRF) and dimension tag boost**: chosen.

## Decision
- Chunks = policy sections with stable ids (e.g. `AML-POL-4.2`).
- Embeddings computed once at ingestion (Gemini embedding, free tier) and
  stored; offline fallback is a deterministic feature-hashing embedder.
- Postgres: pgvector `<=>` cosine search. SQLite: numpy over the stored vectors
  (the corpus is small). Same interface.
- No LLM in retrieval: ranking has a measurable right answer (recall@k).

## Consequences
Zero tokens per retrieval; retrieval quality is tracked in evals
(recall@5, MRR). Accepted risk: tiny corpus means vector index tuning is moot.
