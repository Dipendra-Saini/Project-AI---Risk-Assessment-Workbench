"""Start and resume assessment graph threads (one thread per case run)."""

import logging
import threading
from collections import defaultdict
from typing import Any

from langgraph.types import Command

from raw.audit import chain
from raw.db import session_scope
from raw.graph.build import build_graph
from raw.models import ChangeRequest
from raw.settings import get_settings

log = logging.getLogger(__name__)
_graph = None
_graph_lock = threading.Lock()
_case_locks: dict[int, threading.Lock] = defaultdict(threading.Lock)


def get_graph():
    global _graph
    with _graph_lock:
        if _graph is None:
            _graph = build_graph()
        return _graph


def reset_graph() -> None:
    global _graph
    with _graph_lock:
        _graph = None


def thread_config(cr: ChangeRequest) -> dict[str, Any]:
    return {"configurable": {"thread_id": f"cr-{cr.id}-run-{cr.graph_run}"}}


def waiting_at(cr: ChangeRequest) -> str | None:
    if cr.graph_run == 0:
        return None
    snap = get_graph().get_state(thread_config(cr))
    return snap.next[0] if snap.next else None


def _run(cr_id: int, payload: Any) -> None:
    with _case_locks[cr_id]:
        with session_scope() as s:
            cr = s.get(ChangeRequest, cr_id)
            cfg = thread_config(cr)
            cr.pipeline_state = "running"
        graph = get_graph()
        try:
            graph.invoke(payload, cfg)
            snap = graph.get_state(cfg)
            with session_scope() as s:
                cr = s.get(ChangeRequest, cr_id)
                cr.pipeline_state = "waiting" if snap.next else "idle"
                cr.pipeline_step = snap.next[0] if snap.next else "done"
        except Exception as e:
            log.exception("pipeline failed for case %s", cr_id)
            with session_scope() as s:
                cr = s.get(ChangeRequest, cr_id)
                cr.pipeline_state = "failed"
                cr.needs_human = True
                cr.warnings = [*(cr.warnings or []), f"pipeline failed: {type(e).__name__}: {str(e)[:160]}"]
                chain.record(s, "pipeline", "pipeline.failed", "change_request", cr_id, {"error": str(e)[:300]})


def _dispatch(cr_id: int, payload: Any) -> None:
    if get_settings().pipeline_sync:
        _run(cr_id, payload)
    else:
        threading.Thread(target=_run, args=(cr_id, payload), daemon=True, name=f"pipeline-{cr_id}").start()


def start(cr_id: int, entry: str = "intake") -> None:
    with session_scope() as s:
        cr = s.get(ChangeRequest, cr_id)
        cr.graph_run += 1
        cr.pipeline_state = "running"
        chain.record(s, "pipeline", "pipeline.started", "change_request", cr_id, {"run": cr.graph_run, "entry": entry})
    _dispatch(cr_id, {"cr_id": cr_id, "entry": entry, "warnings": [], "redraft_count": 0})


def resume(cr_id: int, action: str, **extra: Any) -> None:
    with session_scope() as s:
        cr = s.get(ChangeRequest, cr_id)
        cr.pipeline_state = "running"
        chain.record(s, "pipeline", "pipeline.resumed", "change_request", cr_id, {"action": action, **extra})
    _dispatch(cr_id, Command(resume={"action": action, **extra}))
