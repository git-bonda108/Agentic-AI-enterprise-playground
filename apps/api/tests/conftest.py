import os

os.environ["PLAYGROUND_FAKE_LLM"] = "true"
os.environ["PLAYGROUND_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["PLAYGROUND_INTERNAL_KEY"] = "test-key"
os.environ["PLAYGROUND_CANARY_SCHEDULER"] = "false"
os.environ["PLAYGROUND_RATE_LIMIT_PER_MINUTE"] = "0"  # the suite fires hundreds of requests as one person
import tempfile

os.environ["PLAYGROUND_CHECKPOINT_PATH"] = os.path.join(tempfile.mkdtemp(), "checkpoints.db")

import pytest
from fastapi.testclient import TestClient

from app import db as dbmod
from app.main import app

# One shared database file for the whole test session. A file (not :memory: with a StaticPool) gives every thread its own
# connection: the runtime, the canary scheduler and the sandbox's HTTP server all touch the database concurrently, and a
# single pysqlite connection shared across threads can crash the interpreter.
_DB_FILE = os.path.join(tempfile.mkdtemp(), "test.db")
dbmod.engine = dbmod.create_engine(f"sqlite:///{_DB_FILE}", connect_args={"check_same_thread": False, "timeout": 30}, future=True)
dbmod.SessionLocal.configure(bind=dbmod.engine)

HEADERS = {
    "X-Internal-Key": "test-key",
    "X-User-Id": "u1",
    "X-User-Email": "satya@playground.local",
    "X-User-Name": "Satya Bonda",
    "X-User-Role": "admin",
    "X-User-Department": "AI Platform",
}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def headers():
    return dict(HEADERS)
