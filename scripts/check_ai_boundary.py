from pathlib import Path
import sys

from oslt_research.governance.preflight import run_preflight

root = Path(__file__).resolve().parents[1]
failures = [
    item for item in run_preflight(root).findings if item.code == "DIRECT_MODEL_PROVIDER_CALL"
]
for item in failures:
    print(f"{item.code}: {item.path}: {item.message}")
sys.exit(1 if failures else 0)
