"""One command that checks everything: data, tests, evaluation, safety. Live progress bar with time left."""
import os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.progress import Progress

STEPS = [
    ("Generate data", [sys.executable, "scripts/generate_data.py"]),
    ("Validate data", [sys.executable, "scripts/validate_data.py"]),
    ("Unit tests (refund boundaries, actions, timetable)", [sys.executable, "-m", "pytest", "tests/unit", "-q"]),
    ("API tests (confirm flow, privacy, live ingest)", [sys.executable, "-m", "pytest", "tests/api", "-q"]),
    ("Red-team tests (injection, privacy, policy)", [sys.executable, "-m", "pytest", "tests/safety", "-q"]),
    ("Evaluation (62 questions)", [sys.executable, "scripts/run_eval.py"]),
]

def main():
    env = dict(os.environ, MOCK_LLM="true", TRAIN_NO_AUTOAPP="1", PYTHONIOENCODING="utf-8")
    env.pop("DEMO_NOW", None)
    p = Progress(len(STEPS), "check all")
    failed = []
    for name, cmd in STEPS:
        t0 = time.time()
        r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
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
