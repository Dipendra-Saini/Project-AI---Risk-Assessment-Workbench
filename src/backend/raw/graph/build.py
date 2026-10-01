"""Assemble the assessment graph (see docs/architecture/overview.md)."""

import sqlite3
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from raw.graph import nodes
from raw.graph.state import CaseState
from raw.settings import REPO_ROOT, get_settings


def make_checkpointer():
    s = get_settings()
    url = s.checkpoint_url
    if url == "memory":
        return InMemorySaver()
    if url.startswith("postgres") or (not url and s.is_postgres):
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg_pool import ConnectionPool

        conninfo = (url or s.database_url).replace("postgresql+psycopg://", "postgresql://")
        pool = ConnectionPool(conninfo=conninfo, max_size=5, kwargs={"autocommit": True, "prepare_threshold": 0})
        saver = PostgresSaver(pool)
        saver.setup()
        return saver
    from langgraph.checkpoint.sqlite import SqliteSaver

    path = Path(url) if url else REPO_ROOT / "raw_checkpoints.db"
    return SqliteSaver(sqlite3.connect(str(path), check_same_thread=False))


def build_graph(checkpointer=None):
    g = StateGraph(CaseState)
    g.add_node("classify_change", nodes.classify_change)
    g.add_node("extract_documents", nodes.extract_documents)
    g.add_node("po_gate", nodes.po_gate)
    g.add_node("retrieve_policy", nodes.retrieve_policy)
    g.add_node("assess_factors", nodes.assess_factors)
    g.add_node("score", nodes.score_node)
    g.add_node("draft_assessment", nodes.draft_assessment)
    g.add_node("critique", nodes.critique)
    g.add_node("handoff_to_analyst", nodes.handoff_to_analyst)
    g.add_node("analyst_gate", nodes.analyst_gate)

    g.add_conditional_edges(START, lambda s: "classify_change" if s.get("entry", "intake") == "intake" else "retrieve_policy",
                            ["classify_change", "retrieve_policy"])
    g.add_edge("classify_change", "extract_documents")
    g.add_edge("extract_documents", "po_gate")
    g.add_conditional_edges("po_gate", lambda s: "extract_documents" if s.get("action") == "re_extract" else "retrieve_policy",
                            ["extract_documents", "retrieve_policy"])
    g.add_edge("retrieve_policy", "assess_factors")
    g.add_edge("assess_factors", "score")
    g.add_edge("score", "draft_assessment")
    g.add_edge("draft_assessment", "critique")
    g.add_conditional_edges("critique", lambda s: "draft_assessment" if s.get("loop") else "handoff_to_analyst",
                            ["draft_assessment", "handoff_to_analyst"])
    g.add_edge("handoff_to_analyst", "analyst_gate")
    g.add_conditional_edges(
        "analyst_gate",
        lambda s: {"redraft": "draft_assessment", "rerun": "retrieve_policy", "request_info": "po_gate"}.get(
            s.get("action", ""), END),
        ["draft_assessment", "retrieve_policy", "po_gate", END],
    )
    return g.compile(checkpointer=checkpointer if checkpointer is not None else make_checkpointer())


def mermaid() -> str:
    return build_graph(InMemorySaver()).get_graph().draw_mermaid()
