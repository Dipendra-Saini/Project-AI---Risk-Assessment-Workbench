"""Embeddings: Gemini (free tier) when available, deterministic hashing otherwise."""

import hashlib
import logging
from functools import lru_cache

import httpx
import numpy as np

from raw.rag.text import tokenize
from raw.settings import get_settings

log = logging.getLogger(__name__)


class HashEmbedder:
    """Feature-hashing embedder (unigrams + bigrams). Free, offline, deterministic."""

    name = "hash-768"

    def __init__(self, dim: int = 768):
        self.dim = dim

    def _one(self, text: str) -> list[float]:
        v = np.zeros(self.dim, dtype=np.float32)
        toks = tokenize(text)
        feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:], strict=False)]
        for f in feats:
            h = int.from_bytes(hashlib.md5(f.encode()).digest()[:8], "little")
            v[h % self.dim] += 1.0 if (h >> 63) & 1 else -1.0
        n = np.linalg.norm(v)
        return (v / n).tolist() if n else v.tolist()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]


class GeminiEmbedder:
    def __init__(self, api_key: str, model: str, dim: int):
        self.api_key, self.model, self.dim = api_key, model, dim
        self.name = f"gemini:{model}:{dim}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:batchEmbedContents"
        out: list[list[float]] = []
        for i in range(0, len(texts), 50):
            batch = texts[i : i + 50]
            body = {
                "requests": [
                    {"model": f"models/{self.model}", "content": {"parts": [{"text": t}]}, "outputDimensionality": self.dim}
                    for t in batch
                ]
            }
            r = httpx.post(url, params={"key": self.api_key}, json=body, timeout=get_settings().llm_timeout_s)
            r.raise_for_status()
            for e in r.json()["embeddings"]:
                v = np.asarray(e["values"], dtype=np.float32)
                n = np.linalg.norm(v)
                out.append((v / n).tolist() if n else v.tolist())
        return out


@lru_cache
def get_embedder():
    s = get_settings()
    if s.llm_mode == "live" and s.gemini_api_key:
        return GeminiEmbedder(s.gemini_api_key, s.gemini_embed_model, s.embed_dim)
    return HashEmbedder(s.embed_dim)


def embed_with_fallback(texts: list[str]) -> tuple[str, list[list[float]]]:
    emb = get_embedder()
    try:
        return emb.name, emb.embed(texts)
    except Exception as e:  # free-tier quota or network: degrade, never block
        log.warning("embedding provider failed (%s); using hash embedder", e)
        fallback = HashEmbedder(get_settings().embed_dim)
        return fallback.name, fallback.embed(texts)
