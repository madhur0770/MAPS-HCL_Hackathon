"""Runs the supplied kit's own self-tests (data_kit/tests).
Windows will not delete a SQLite file while a connection is open, so the kit's temp folders can fail to clean up AFTER the tests have run.
Cleanup errors are ignored here; test results are not."""
import functools, os, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, "data_kit")
os.chdir(KIT)
sys.path.insert(0, KIT)
tempfile.TemporaryDirectory = functools.partial(tempfile.TemporaryDirectory, ignore_cleanup_errors=True)
suite = unittest.defaultTestLoader.discover(os.path.join(KIT, "tests"), pattern="test_*.py")
res = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(0 if res.wasSuccessful() else 1)
