"""Parse policy markdown into stable-id chunks and store them with embeddings.

Embeddings are computed once per chunk and re-used (token efficiency): a chunk
is only re-embedded when its text or the embedding model changes.
"""

import re
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from raw.audit import chain
from raw.models import PolicyChunk
from raw.rag.embeddings import embed_with_fallback, get_embedder
from raw.settings import REPO_ROOT

POLICY_DIR = REPO_ROOT / "data" / "policies"
_SECTION = re.compile(r"^## (?P<id>[A-Z0-9-]+(?:\.\d+)?) (?P<title>.+)$", re.M)


def parse_policy(path: Path) -> list[dict]:
    raw = path.read_text()
    _, front, body = raw.split("---", 2)
    meta = yaml.safe_load(front)
    chunks = []
    matches = list(_SECTION.finditer(body))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        lines = body[m.end() : end].strip().splitlines()
        tags: list[str] = []
        if lines and lines[0].startswith("tags:"):
            tags = lines[0].removeprefix("tags:").split()
            lines = lines[1:]
        chunks.append({
            "id": m.group("id"),
            "doc_id": meta["doc_id"],
            "doc_title": meta["title"],
            "section_title": m.group("title").strip(),
            "text": " ".join(line.strip() for line in lines if line.strip()),
            "tags": tags,
            "source_url": meta.get("source_url", ""),
        })
    return chunks


def ingest(session: Session, policy_dir: Path = POLICY_DIR) -> dict:
    parsed = [c for p in sorted(policy_dir.glob("*.md")) for c in parse_policy(p)]
    model_name = get_embedder().name
    to_embed: list[tuple[PolicyChunk, str]] = []
    created = updated = 0
    for c in parsed:
        row = session.get(PolicyChunk, c["id"])
        if row is None:
            row = PolicyChunk(**c)
            session.add(row)
            created += 1
            to_embed.append((row, f"{c['section_title']}. {c['text']}"))
        elif row.text != c["text"] or row.embed_model != model_name or row.embedding is None:
            for k, v in c.items():
                setattr(row, k, v)
            updated += 1
            to_embed.append((row, f"{c['section_title']}. {c['text']}"))
    if to_embed:
        name, vectors = embed_with_fallback([t for _, t in to_embed])
        for (row, _), vec in zip(to_embed, vectors, strict=True):
            row.embedding = vec
            row.embed_model = name
    session.flush()
    stats = {"chunks": len(parsed), "created": created, "updated": updated, "embedded": len(to_embed), "model": model_name}
    chain.record(session, "system", "policy.ingested", "policy_corpus", "all", stats)
    return stats
