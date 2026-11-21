"""Put the demo data back to the start (also: POST /admin/reset_demo on a running API)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.generate_data import main
main()
