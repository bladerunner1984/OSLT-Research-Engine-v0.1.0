from __future__ import annotations

import json
from pathlib import Path

from oslt_research.evidence.provenance import sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "docs/reference/v2.4-rc1"
MANIFEST = REFERENCE / "MANIFEST.sha256.json"


def main() -> None:
    files = []
    for path in sorted(REFERENCE.rglob("*")):
        if not path.is_file() or path == MANIFEST:
            continue
        files.append(
            {
                "path": path.relative_to(REFERENCE).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_bytes(path.read_bytes()),
            }
        )
    payload = {
        "package": "OSLT_Research_Engine_v2_4_RC1",
        "immutability_rule": "reference package changes require an explicit new lineage version",
        "file_count": len(files),
        "files": files,
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {MANIFEST} with {len(files)} files")


if __name__ == "__main__":
    main()
