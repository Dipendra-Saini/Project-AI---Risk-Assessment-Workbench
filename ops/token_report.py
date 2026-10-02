"""Token-efficiency report from the LLM ledger (`llm_calls`).

    make tokens        # runs the golden set offline into a scratch DB, then writes ops/token-analysis.md
    PYTHONPATH=src/backend .venv/bin/python ops/token_report.py --db evals/.work/tokens.db

Every LLM request, whether it was answered by a provider, the cache, a replay recording or the deterministic
fallback, writes a ledger row with `estimated_tokens` (rendered prompt / 4 + max output tokens).
So the report measures what the pipeline *would* send even in offline mode, and compares it with
a naive design: one agent that re-sends every document and the whole policy corpus for each task.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "backend"))

from sqlalchemy import create_engine, text  # noqa: E402

from raw.rag.text import estimate_tokens  # noqa: E402

NAIVE_TASKS = {"classify": 1, "extract": 1, "rate factors": 6, "draft": 1, "critique": 1}
NAIVE_OUTPUT = {"classify": 40, "extract": 900, "rate factors": 220, "draft": 1400, "critique": 400}


def q(conn, sql, **kw):
    return conn.execute(text(sql), kw).mappings().all()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "evals/.work/tokens.db"))
    ap.add_argument("--out", default=str(ROOT / "ops/token-analysis.md"))
    args = ap.parse_args()
    url = args.db if "://" in args.db else f"sqlite:///{Path(args.db).resolve()}"
    eng = create_engine(url)
    with eng.connect() as c:
        calls = q(c, "select cr_id, node, provider, status, cache_hit, input_tokens, output_tokens, estimated_tokens from llm_calls")
        docs = q(c, "select cr_id, text from documents")
        corpus = q(c, "select text from policy_chunks")
        cases = {r["id"]: r for r in q(c, "select id, title, description from change_requests")}
        factors = q(c, """select a.cr_id, f.dimension, f.origin from factor_ratings f
                          join assessments a on a.id = f.assessment_id
                          where a.id in (select max(id) from assessments group by cr_id)""")
        crit = q(c, "select cr_id, critique from assessments where id in (select max(id) from assessments group by cr_id)")

    n_cases = len({r["cr_id"] for r in calls if r["cr_id"] is not None}) or 1
    corpus_tok = sum(estimate_tokens(r["text"]) for r in corpus)
    doc_tok = defaultdict(int)
    for d in docs:
        doc_tok[d["cr_id"]] += estimate_tokens(d["text"] or "")
    for cid, cr in cases.items():
        doc_tok[cid] += estimate_tokens(f"{cr['title']} {cr['description']}")
    avg_doc = sum(doc_tok.values()) / max(1, len(doc_tok))

    by_node = defaultdict(lambda: {"calls": 0, "est": 0, "real": 0, "cache": 0, "fallback": 0})
    for r in calls:
        n = by_node[r["node"]]
        n["calls"] += 1
        n["est"] += r["estimated_tokens"] or 0
        n["real"] += (r["input_tokens"] or 0) + (r["output_tokens"] or 0)
        n["cache"] += bool(r["cache_hit"])
        n["fallback"] += r["status"] == "fallback"
    est_total = sum(n["est"] for n in by_node.values())
    real_total = sum(n["real"] for n in by_node.values())
    ours_per_case = est_total / n_cases

    naive_in = avg_doc + corpus_tok + 250  # instructions
    naive_calls = sum(NAIVE_TASKS.values())
    naive_per_case = sum(k * (naive_in + NAIVE_OUTPUT[t]) for t, k in NAIVE_TASKS.items())

    origins = Counter(f["origin"] for f in factors)
    rule_dims = origins.get("rule", 0) + origins.get("human", 0)
    total_dims = sum(origins.values()) or 1
    sf = by_node.get("assess_factors", {"calls": 0, "est": 0})
    avg_sf = sf["est"] / sf["calls"] if sf["calls"] else 400
    claims = doubtful_cases = 0
    for r in crit:
        cr = r["critique"]
        cr = json.loads(cr) if isinstance(cr, str) else (cr or {})
        claims += len(cr.get("claims", []))
        doubtful_cases += "+" in cr.get("checked_by", "")
    draft = by_node.get("draft_assessment", {"calls": 0, "est": 0})
    avg_draft = draft["est"] / draft["calls"] if draft["calls"] else 0

    crit_node = by_node.get("critique", {"calls": 0, "est": 0})
    avg_crit = crit_node["est"] / crit_node["calls"] if crit_node["calls"] else 900
    case_totals = [sum(r["estimated_tokens"] or 0 for r in calls if r["cr_id"] == cid) for cid in doc_tok]
    classify_calls = by_node.get("classify_change", {}).get("calls", 0)
    levers = [
        ("Change-type classification only when the product owner picks 'other'; the form field is authoritative",
         f"{classify_calls} classify requests for {n_cases} cases", None),
        ("Deterministic rules rate the factor where a rule fires; the LLM only suggests for uncovered dimensions",
         f"{rule_dims}/{total_dims} dimension ratings came from rules ({rule_dims / total_dims:.0%})",
         round((rule_dims / n_cases) * avg_sf)),
        ("Critic runs deterministic checks first; the LLM critic only sees 'doubtful' claims",
         f"{claims} claims checked deterministically; LLM critic needed on {doubtful_cases}/{len(crit)} cases "
         "(offline drafts quote their sources, so live drafts will need it more often; saving assumes one 900-token call per case)",
         round((len(crit) - doubtful_cases) / n_cases * avg_crit)),
        ("Context pack (~150 tokens) replaces raw documents in every node after extraction",
         f"golden briefs average {avg_doc:.0f} tokens; a real 10-page product brief is ~5,000, "
         "so this lever grows linearly with document size",
         round(avg_doc * 3)),
        ("Top-3 policy passages per dimension (hybrid BM25 + vector) instead of the whole corpus",
         f"corpus is {corpus_tok:,} tokens; the drafter sees about 12 passages x 350 characters",
         round(corpus_tok - 12 * 90)),
        ("Small model (Groq Qwen3.8 27B) for extract/classify/suggest; Gemini Flash only for draft and critique, "
         "thinking budget 0",
         "routing by prompt tier in ai/prompts/*.yaml", None),
        ("Response cache keyed on sha256(prompt id, version, rendered text): reruns, the consistency evals and "
         "identical cases cost 0",
         "measured in live mode (cache_hit column); replay in CI is a cache by construction", None),
        ("Per-case token budget (12k): past it the node uses the deterministic fallback instead of failing",
         f"max estimated case total in this run: {max(case_totals, default=0):,}",
         None),
    ]

    md = [
        "# Token analysis",
        "",
        f"Source: LLM ledger in `{Path(args.db).name}`, {n_cases} cases, {len(calls)} ledger rows. "
        "Generated by `ops/token_report.py` (`make tokens`). Do not edit by hand.",
        "",
        "## Headline",
        "",
        "| | per case | LLM requests per case |",
        "|---|---|---|",
        "| Naive design (every task re-sends all documents and the full policy corpus) | "
        f"{naive_per_case:,.0f} tokens | {naive_calls} |",
        "| This system, upper bound (prompt estimate + max output for every request) | "
        f"{ours_per_case:,.0f} tokens | {len(calls) / n_cases:.1f} |",
        f"| Reduction | **{1 - ours_per_case / naive_per_case:.0%}** | |",
        "",
        f"Real provider tokens in this run: {real_total:,}"
        + (" (offline / replay run: no provider was called; the estimate is what live mode would send)." if real_total == 0 else "."),
        "Cost: $0. Gemini Flash and Groq free tiers only. Tokens matter here because free tiers are rate-limited:",
        "fewer tokens and requests per case means more cases per day inside the quota "
        f"(cases/day = daily request quota / {len(calls) / n_cases:.1f}).",
        "",
        "## By graph node",
        "",
        "| node | requests | est. tokens | est. per request | real tokens | cache hits | fallbacks |",
        "|---|---|---|---|---|---|---|",
    ]
    for node, n in sorted(by_node.items(), key=lambda kv: -kv[1]["est"]):
        per = n["est"] // max(1, n["calls"])
        md.append(f"| {node} | {n['calls']} | {n['est']:,} | {per:,} | {n['real']:,} | {n['cache']} | {n['fallback']} |")
    md += [
        "",
        "## Where the savings come from",
        "",
        "| lever | evidence in this run | est. tokens saved per case |",
        "|---|---|---|",
    ]
    for lever, ev, saved in levers:
        md.append(f"| {lever} | {ev} | {'-' if saved is None else f'{saved:,}'} |")
    md += [
        "",
        "## Draft prompt budget",
        "",
        f"The draft is the largest request (about {avg_draft:,.0f} estimated tokens, of which 1,400 is the output cap). Its input is the",
        "context pack, the score table (numbers come from the engine, never from the model) and two passages per dimension.",
        "Passages are capped at 350 characters each; the cap and the passage count are the main knobs if a free-tier",
        "token-per-minute limit is hit (see `ops/runbook.md#llmfallbackratehigh`).",
        "",
        "## Build-time tokens (the AI that built this)",
        "",
        "Build-time usage happened in Cursor agent sessions and isn't metered by this ledger. What kept it down:",
        "`AGENTS.md` + `.cursor/rules` as a short always-on context instead of re-explaining the project;",
        "role prompts in `ai/agents/` scoped to one stage each; failures logged once in `ai/failure-log.md` and",
        "encoded as rules so they don't recur.",
        "",
    ]
    Path(args.out).write_text("\n".join(md))
    print("\n".join(md[:14]))
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
