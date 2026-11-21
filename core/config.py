"""All settings come from environment variables (see .env.example)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def env(name, default=""):
    return os.getenv(name, default)


def flag(name, default=False):
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def db_path():
    return env("DB_PATH", os.path.join(ROOT, "data", "train.db"))


MOCK_LLM = lambda: flag("MOCK_LLM", False)          # noqa: E731  (read at call time so tests can toggle)
OLLAMA_URL = lambda: env("OLLAMA_URL", "http://localhost:11434")  # noqa: E731
OLLAMA_MODEL = lambda: env("OLLAMA_MODEL", "qwen2.5:7b-instruct")  # noqa: E731
LLM_TIMEOUT = lambda: float(env("LLM_TIMEOUT", "20"))  # noqa: E731
CRITIC_LLM = lambda: flag("CRITIC_LLM", False)       # noqa: E731
ADMIN_KEY = lambda: env("ADMIN_KEY", "admin")        # noqa: E731
PROTECT_ADMIN = lambda: flag("PROTECT_ADMIN", False)  # noqa: E731
PROTECT_TRACE = lambda: flag("PROTECT_TRACE", False)  # noqa: E731
RATE_LIMIT_PER_MIN = lambda: int(env("RATE_LIMIT_PER_MIN", "300"))  # noqa: E731
MAX_BODY_MB = lambda: float(env("MAX_BODY_MB", "5"))  # noqa: E731
OLLAMA_EMBED_MODEL = lambda: env("OLLAMA_EMBED_MODEL", "nomic-embed-text")  # noqa: E731
VECTOR_MIN = lambda: float(env("VECTOR_MIN", "0.65"))  # noqa: E731  (cosine above this lets a paraphrased question through the abstain guard)
USE_VECTORS = lambda: flag("USE_VECTORS", True)  # noqa: E731
