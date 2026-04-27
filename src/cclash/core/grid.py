"""3x3 grid for cclash with deterministic Reconfigure moves.

Positions are addressed as ``A1..C3`` where the row is one of ``A/B/C``
and the column is one of ``1/2/3``. Every move snapshots the previous
state so a single :meth:`Grid.rollback` step can undo it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

ROWS: tuple[str, ...] = ("A", "B", "C")
COLS: tuple[str, ...] = ("1", "2", "3")
POSITIONS: tuple[str, ...] = tuple(f"{r}{c}" for r in ROWS for c in COLS)

# Outer ring traversed clockwise, starting at A1.
OUTER_RING_CW: tuple[str, ...] = ("A1", "A2", "A3", "B3", "C3", "C2", "C1", "B1")


@dataclass
class Grid:
    """3x3 grid with cell values keyed by position.

    Cells are kept in a plain dict so any value type works (card instance,
    string, ``None``). Use :meth:`from_rows` to build a grid from row-major
    input.
    """

    cells: dict[str, Any] = field(default_factory=dict)
    _previous: dict[str, Any] | None = field(default=None, repr=False)

    @classmethod
    def from_rows(cls, rows: Iterable[Iterable[Any]]) -> Grid:
        rows = [list(r) for r in rows]
        if len(rows) != 3 or any(len(r) != 3 for r in rows):
            raise ValueError("Grid requires a 3x3 input")
        cells: dict[str, Any] = {}
        for r, row in zip(ROWS, rows):
            for c, val in zip(COLS, row):
                cells[f"{r}{c}"] = val
        return cls(cells=cells)

    def as_rows(self) -> list[list[Any]]:
        return [[self.cells[f"{r}{c}"] for c in COLS] for r in ROWS]

    def __getitem__(self, pos: str) -> Any:
        if pos not in POSITIONS:
            raise ValueError(f"unknown position: {pos!r}")
        return self.cells[pos]

    def _snapshot(self) -> None:
        self._previous = dict(self.cells)

    def _write_rows(self, rows: list[list[Any]]) -> None:
        for r, row in zip(ROWS, rows):
            for c, val in zip(COLS, row):
                self.cells[f"{r}{c}"] = val

    # -- Moves --------------------------------------------------------

    def rotate90(self) -> None:
        """Rotate the grid 90 degrees clockwise."""
        self._snapshot()
        rows = self.as_rows()
        rotated = [list(reversed(col)) for col in zip(*rows)]
        self._write_rows(rotated)

    def rotate90ccw(self) -> None:
        """Rotate the grid 90 degrees counter-clockwise."""
        self._snapshot()
        rows = self.as_rows()
        rotated = list(reversed([list(col) for col in zip(*rows)]))
        self._write_rows(rotated)

    def shift_row(self, source: str, target: str) -> None:
        """Move row ``source`` to index ``target``; remaining rows keep their relative order."""
        if source not in ROWS or target not in ROWS:
            raise ValueError(f"row must be one of {ROWS}")
        if source == target:
            return
        self._snapshot()
        rows = self.as_rows()
        moved = rows.pop(ROWS.index(source))
        rows.insert(ROWS.index(target), moved)
        self._write_rows(rows)

    def shift_column(self, source: str, target: str) -> None:
        """Move column ``source`` to index ``target``; remaining columns keep their relative order."""
        if source not in COLS or target not in COLS:
            raise ValueError(f"column must be one of {COLS}")
        if source == target:
            return
        self._snapshot()
        rows = self.as_rows()
        src_idx = COLS.index(source)
        tgt_idx = COLS.index(target)
        for row in rows:
            row.insert(tgt_idx, row.pop(src_idx))
        self._write_rows(rows)

    def outer_ring_rotate(self, steps: int = 1) -> None:
        """Rotate the outer ring clockwise by ``steps`` positions.

        The center cell ``B2`` is not affected. ``steps`` may be negative
        (rotates counter-clockwise) and is taken modulo 8; a no-op rotation
        does not consume rollback history.
        """
        n = len(OUTER_RING_CW)
        steps = steps % n
        if steps == 0:
            return
        self._snapshot()
        values = [self.cells[p] for p in OUTER_RING_CW]
        rotated = values[-steps:] + values[:-steps]
        for p, v in zip(OUTER_RING_CW, rotated):
            self.cells[p] = v

    def swap_adjacent(self, a: str, b: str) -> None:
        """Swap two orthogonally adjacent cells."""
        if not _adjacent(a, b):
            raise ValueError(f"{a} and {b} are not orthogonally adjacent")
        self._snapshot()
        self.cells[a], self.cells[b] = self.cells[b], self.cells[a]

    def rollback(self) -> None:
        """Restore the state from before the last move.

        Only one step of history is kept; calling rollback twice in a row
        is an error. Output and damage are not undone — see rules §6.
        """
        if self._previous is None:
            raise ValueError("nothing to rollback")
        self.cells = dict(self._previous)
        self._previous = None


def _adjacent(a: str, b: str) -> bool:
    if a not in POSITIONS or b not in POSITIONS:
        raise ValueError(f"unknown positions: {a!r}, {b!r}")
    if a == b:
        return False
    ra, ca = a[0], a[1]
    rb, cb = b[0], b[1]
    same_row_neighbour = ra == rb and abs(int(ca) - int(cb)) == 1
    same_col_neighbour = ca == cb and abs(ROWS.index(ra) - ROWS.index(rb)) == 1
    return same_row_neighbour or same_col_neighbour
