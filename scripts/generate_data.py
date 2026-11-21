"""Create the database with generated data. Shows a live progress bar."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as dbm, seed, config
from core.progress import Progress

STEPS = ["stations", "trains+stops", "fares", "seats", "passengers", "bookings", "settings", "documents"]

def main():
    path = os.getenv("DB_PATH", config.db_path())
    if "--if-missing" in sys.argv and os.path.exists(path) and os.path.getsize(path) > 0:
        print("database already exists at %s: keeping it (bookings, actions and traces survive restarts)" % path)
        return
    for ext in ("", "-wal", "-shm"):
        try: os.remove(path + ext)
        except OSError: pass
    d = dbm.connect(path)
    p = Progress(len(STEPS), "generate data")
    seed.seed(d, anchor=os.getenv("DATA_ANCHOR", seed.ANCHOR_DEFAULT), progress=lambda n: p.step(1, n))
    p.finish("database ready at %s" % path)

if __name__ == "__main__":
    main()
