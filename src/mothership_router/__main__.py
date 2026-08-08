from __future__ import annotations

import json
from pathlib import Path
import sys

from .core import advisory_route


def main(argv: list[str] | None = None) -> int:
    values = sys.argv[1:] if argv is None else argv
    if len(values) != 2:
        print("usage: python -m mothership_router TASK.json REGISTRY.json", file=sys.stderr)
        return 2
    try:
        task = json.loads(Path(values[0]).read_text(encoding="utf-8"))
        registry = json.loads(Path(values[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"input_error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(advisory_route(task, registry), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
