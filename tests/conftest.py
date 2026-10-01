import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "backend"))

os.environ.setdefault("LLM_MODE", "offline")
os.environ["CHECKPOINT_URL"] = "memory"
os.environ["PIPELINE_SYNC"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["GROQ_API_KEY"] = ""


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    from raw import db as dbmod
    from raw.settings import get_settings

    get_settings.cache_clear()
    dbmod.reset_engine()
    dbmod.init_db()
    yield dbmod
    dbmod.reset_engine()
    get_settings.cache_clear()


@pytest.fixture()
def session(db):
    s = db.SessionLocal()
    yield s
    s.rollback()
    s.close()
