"""Print a markdown coverage summary from a Cobertura ``coverage.xml``."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def summarise(path: Path) -> str:
    root = ET.parse(path).getroot()
    line_rate = float(root.get("line-rate", "0")) * 100
    branch_rate = float(root.get("branch-rate", "0")) * 100
    lines_valid = int(root.get("lines-valid", "0"))
    lines_covered = int(root.get("lines-covered", "0"))

    return (
        "## Coverage summary\n\n"
        f"- Line coverage: **{line_rate:.1f}%** ({lines_covered}/{lines_valid} lines)\n"
        f"- Branch coverage: **{branch_rate:.1f}%**\n"
    )


def main(argv: list) -> int:
    path = Path(argv[1] if len(argv) > 1 else "coverage.xml")
    if not path.is_file():
        print(f"coverage file not found: {path}", file=sys.stderr)
        return 1
    print(summarise(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
