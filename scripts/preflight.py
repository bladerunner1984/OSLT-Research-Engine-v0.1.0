from __future__ import annotations

import json
import sys
from pathlib import Path

from oslt_research.governance.preflight import run_preflight


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    report = run_preflight(ROOT)
    print(json.dumps(report.as_dict(), indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
