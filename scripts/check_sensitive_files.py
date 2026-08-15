from pathlib import Path
import sys

from oslt_research.governance.preflight import run_preflight

root = Path(__file__).resolve().parents[1]
codes = {"ENV_FILE_PRESENT", "CREDENTIAL_LIKE_FILENAME", "RAW_DATA_PRESENT_IN_REPOSITORY"}
failures = [item for item in run_preflight(root).findings if item.code in codes]
for item in failures:
    print(f"{item.code}: {item.path}: {item.message}")
sys.exit(1 if failures else 0)
