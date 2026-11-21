"""One command that checks everything: data, tests, evaluation, safety. Live progress bar with time left."""
import os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.progress import Progress

CORE_PACKAGES = ["fastapi", "uvicorn", "pydantic", "httpx", "pytest", "requests"]   # streamlit is optional and large: not needed for the checks


def ensure_env():
    """Wrong Python (no fastapi/pytest)? Use the project's .venv, creating it and installing the packages on first run, then run again inside it."""
    try:
        import fastapi, pytest, httpx  # noqa: F401
        return
    except ImportError:
        pass
    vpy = os.path.join(ROOT, ".venv", "Scripts" if os.name == "nt" else "bin", "python.exe" if os.name == "nt" else "python")
    if os.environ.get("CHECK_ALL_BOOTSTRAPPED"):
        print("Packages still missing after setup. Run: %s -m pip install %s" % (vpy, " ".join(CORE_PACKAGES)))
        sys.exit(2)
    if not os.path.exists(vpy):
        print("Creating the project's own Python environment (.venv) ...", flush=True)
        subprocess.check_call([sys.executable, "-m", "venv", os.path.join(ROOT, ".venv")])
    print("Installing packages into .venv (first run only, about a minute) ...", flush=True)
    subprocess.check_call([vpy, "-m", "pip", "install", "--disable-pip-version-check", "-q"] + CORE_PACKAGES)
    r = subprocess.run([vpy, os.path.abspath(__file__)] + sys.argv[1:], env=dict(os.environ, CHECK_ALL_BOOTSTRAPPED="1"))
    sys.exit(r.returncode)

STEPS = [
    ("Load the supplied data", [sys.executable, "scripts/generate_data.py"]),
    ("Validate data", [sys.executable, "scripts/validate_data.py"]),
    ("Supplied kit self-tests (21)", [sys.executable, "scripts/run_kit_tests.py"]),
    ("Unit tests (refund boundaries, actions, timetable)", [sys.executable, "-m", "pytest", "tests/unit", "-q"]),
    ("API tests (confirm flow, privacy, live ingest)", [sys.executable, "-m", "pytest", "tests/api", "-q"]),
    ("Red-team tests (injection, privacy, policy)", [sys.executable, "-m", "pytest", "tests/safety", "-q"]),
    ("Evaluation (64 questions)", [sys.executable, "scripts/run_eval.py"]),
    ("Audit samples (3 real runs)", [sys.executable, "scripts/make_audit_samples.py"]),
]

def main():
    ensure_env()
    env = dict(os.environ, MOCK_LLM="true", TRAIN_NO_AUTOAPP="1", PYTHONIOENCODING="utf-8")
    env.pop("DEMO_NOW", None)
    p = Progress(len(STEPS), "check all")
    failed = []
    for step in STEPS:
        name, cmd = step[0], step[1]
        cwd = os.path.join(ROOT, step[2]) if len(step) > 2 else ROOT
        t0 = time.time()
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        ok = r.returncode == 0
        tail = [l for l in (r.stdout + r.stderr).strip().splitlines() if l.strip()][-1:] or [""]
        sys.stdout.write("\r" + " " * 118 + "\r")
        print("%s %-52s %5.1fs  %s" % ("PASS" if ok else "FAIL", name, time.time() - t0, tail[0][:70]))
        if not ok:
            failed.append((name, r.stdout[-1500:] + r.stderr[-800:]))
        p.step(1, name[:30])
    p.finish("all %d steps passed" % len(STEPS) if not failed else "%d step(s) FAILED" % len(failed))
    for n, out in failed:
        print("\n--- %s ---\n%s" % (n, out))
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
