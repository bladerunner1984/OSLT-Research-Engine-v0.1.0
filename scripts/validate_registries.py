from __future__ import annotations

import json
import sys
from pathlib import Path

from oslt_research.pipelines.registries import registry_summary


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    summary = registry_summary(ROOT / "registries")
    print(json.dumps({"counts": summary.counts, "failures": summary.failures}, indent=2))
    return 0 if summary.valid else 1


if __name__ == "__main__":
    sys.exit(main())
