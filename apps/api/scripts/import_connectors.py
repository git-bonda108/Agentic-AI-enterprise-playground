"""Snapshot the official MCP registry into apps/api/catalog/connectors.json.

Run (network required, a few minutes): `uv run python scripts/import_connectors.py`.
The API seeds its connectors table from this file, so the product works offline; admins can sync incrementally at runtime.
Registry API: https://registry.modelcontextprotocol.io/v0.1/servers (no authentication).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.connectors import fetch_registry_page, normalize

OUT = Path(__file__).resolve().parent.parent / "catalog" / "connectors.json"


def main() -> None:
    rows: dict[str, dict] = {}
    cursor: str | None = None
    pages = 0
    while True:
        servers, cursor = fetch_registry_page(cursor=cursor)
        pages += 1
        for item in servers:
            row = normalize(item)
            if row is not None:
                rows[row["id"]] = row
        if pages % 10 == 0:
            print(f"{pages} pages, {len(rows)} servers", file=sys.stderr)
        if not cursor or not servers:
            break
    OUT.write_text(json.dumps(sorted(rows.values(), key=lambda r: r["id"]), ensure_ascii=False, separators=(",", ":")))
    print(f"wrote {len(rows)} -> {OUT} ({OUT.stat().st_size // 1024} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
