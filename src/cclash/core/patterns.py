"""Spatial patterns for effect targeting on a 3x3 grid.

Each pattern function takes a source position (``A1..C3``) and returns
the set of positions affected by that pattern, including the source where
the rules call for it (``self``, ``row``, ``column``, ``global``).

These patterns are purely geometric primitives. Filtering by faction, card
type, or ownership belongs in the effect interpreter — the higher-level
target language from ``docs/card_model.md §6`` (e.g. ``friendly_codes_in_row``,
``all_friendly_codes``) maps onto these primitives plus a filter.

The set of names matches ``docs/mvp_tasks.md §M2``: ``self``, ``row``,
``column``, ``adjacent``, ``diagonal``, ``mirror``, ``global``. ``global``
is the engine-side primitive behind ``all_friendly_codes`` and is not
itself a card-facing pattern.

Iteration order over the returned ``frozenset`` is unspecified; callers
that need deterministic order must sort, e.g. by ``POSITIONS`` index.
"""

from __future__ import annotations

from typing import Callable

from cclash.core.grid import COLS, POSITIONS, ROWS


def _check(source: str) -> tuple[str, str]:
    if source not in POSITIONS:
        raise ValueError(f"unknown position: {source!r}")
    return source[0], source[1]


def pattern_self(source: str) -> frozenset[str]:
    _check(source)
    return frozenset({source})


def pattern_row(source: str) -> frozenset[str]:
    row, _ = _check(source)
    return frozenset(f"{row}{c}" for c in COLS)


def pattern_column(source: str) -> frozenset[str]:
    _, col = _check(source)
    return frozenset(f"{r}{col}" for r in ROWS)


def pattern_adjacent(source: str) -> frozenset[str]:
    """Orthogonal neighbours, excluding the source itself."""
    row, col = _check(source)
    r_idx = ROWS.index(row)
    c_idx = COLS.index(col)
    fields: set[str] = set()
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r_idx + dr, c_idx + dc
        if 0 <= nr < len(ROWS) and 0 <= nc < len(COLS):
            fields.add(f"{ROWS[nr]}{COLS[nc]}")
    return frozenset(fields)


def pattern_diagonal(source: str) -> frozenset[str]:
    """Diagonal neighbours, excluding the source itself."""
    row, col = _check(source)
    r_idx = ROWS.index(row)
    c_idx = COLS.index(col)
    fields: set[str] = set()
    for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        nr, nc = r_idx + dr, c_idx + dc
        if 0 <= nr < len(ROWS) and 0 <= nc < len(COLS):
            fields.add(f"{ROWS[nr]}{COLS[nc]}")
    return frozenset(fields)


def pattern_mirror(source: str) -> frozenset[str]:
    """180-degree rotation on the same grid: A1 ↔ C3, B2 maps to itself.

    Cross-grid targeting (``mirrored enemy slot``) is handled by the
    effect interpreter; this function only returns the spatial mapping.
    """
    row, col = _check(source)
    r_idx = ROWS.index(row)
    c_idx = COLS.index(col)
    mirrored = f"{ROWS[len(ROWS) - 1 - r_idx]}{COLS[len(COLS) - 1 - c_idx]}"
    return frozenset({mirrored})


def pattern_global(source: str) -> frozenset[str]:
    _check(source)
    return frozenset(POSITIONS)


PATTERNS: dict[str, Callable[[str], frozenset[str]]] = {
    "self": pattern_self,
    "row": pattern_row,
    "column": pattern_column,
    "adjacent": pattern_adjacent,
    "diagonal": pattern_diagonal,
    "mirror": pattern_mirror,
    "global": pattern_global,
}


def affected_fields(pattern: str, source: str) -> frozenset[str]:
    """Resolve a pattern name to its affected fields for ``source``.

    Raises :class:`ValueError` for unknown patterns or positions.
    """
    if pattern not in PATTERNS:
        raise ValueError(f"unknown pattern: {pattern!r}")
    return PATTERNS[pattern](source)
