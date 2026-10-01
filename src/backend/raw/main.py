import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from raw.api.routes import api
from raw.bootstrap import ensure_reference_data
from raw.db import init_db, session_scope
from raw.observability.tracing import setup_tracing
from raw.services.cases import ActionError
from raw.settings import get_settings
from raw.workflow.machine import TransitionError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_tracing()
    init_db()
    with session_scope() as s:
        ensure_reference_data(s)
    yield


app = FastAPI(title="Risk Assessment Workbench", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(api)


@app.exception_handler(TransitionError)
async def _transition(_: Request, e: TransitionError):
    return JSONResponse({"detail": str(e)}, status_code=409)


@app.exception_handler(ActionError)
async def _action(_: Request, e: ActionError):
    return JSONResponse({"detail": str(e)}, status_code=422)


@app.exception_handler(ValueError)
async def _value(_: Request, e: ValueError):
    return JSONResponse({"detail": str(e)}, status_code=422)


@app.get("/health")
def health():
    s = get_settings()
    return {"status": "ok", "llm_mode": s.llm_mode, "providers": [n for n, k in (("gemini", s.gemini_api_key),
                                                                              ("groq", s.groq_api_key)) if k],
            "database": "postgres" if s.is_postgres else "sqlite"}


@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
