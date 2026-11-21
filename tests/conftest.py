import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
os.environ.setdefault("MOCK_LLM", "true")
os.environ.setdefault("TRAIN_NO_AUTOAPP", "1")
from core import db as dbm, seed


@pytest.fixture()
def db():
    d = dbm.connect(":memory:")
    seed.seed(d)
    yield d
    d.close()
