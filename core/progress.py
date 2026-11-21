"""Live progress bar with percent and time left (no dependencies)."""
import sys
import time


class Progress:
    def __init__(self, total: int, label: str = "", width: int = 28):
        self.total = max(1, total)
        self.done = 0
        self.label = label
        self.width = width
        self.t0 = time.time()
        self.tty = sys.stdout.isatty()
        self._last = -1

    def step(self, n: int = 1, note: str = ""):
        self.done = min(self.total, self.done + n)
        pct = int(100 * self.done / self.total)
        el = time.time() - self.t0
        left = int(el / self.done * (self.total - self.done)) if self.done else 0
        filled = int(self.width * self.done / self.total)
        line = "[%s%s] %3d%% %d/%d ~%ds left  %s %s" % (
            "#" * filled, "." * (self.width - filled), pct, self.done, self.total, left, self.label, note)
        if self.tty:
            sys.stdout.write("\r" + line[:118].ljust(118))
            sys.stdout.flush()
        elif self.total <= 40 or pct != self._last and (pct % 10 == 0 or self.done == self.total):
            print(line[:118])
        self._last = pct

    def finish(self, note: str = "done"):
        if self.tty:
            sys.stdout.write("\n")
        print("%s: %s in %.1fs" % (self.label, note, time.time() - self.t0))
