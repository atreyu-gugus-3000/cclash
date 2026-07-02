"""Append-only training run log (JSONL).

The minimal persistence needed for the training loop ("Save highscore",
rules §8): every finished training match appends one JSON line. The
full archive (card instances, SQLite) is M7 and lives elsewhere later;
this file format is intentionally throwaway-simple.

Default location is ``~/.cclash/training_log.jsonl``; the CLI accepts
``--log-file`` so tests can redirect it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_DIR = Path.home() / ".cclash"


def default_log_path() -> Path:
    return DEFAULT_DIR / "training_log.jsonl"


def default_grid_path() -> Path:
    return DEFAULT_DIR / "grid.json"


def append_entry(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def read_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def highscore(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    scored = [e for e in entries if isinstance(e.get("total"), int)]
    if not scored:
        return None
    return max(scored, key=lambda e: e["total"])
