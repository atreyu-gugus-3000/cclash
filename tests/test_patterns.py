"""Tests for the geometric pattern engine."""

from __future__ import annotations

import pytest

from cclash.core.grid import POSITIONS
from cclash.core.patterns import affected_fields


def test_self_returns_only_source():
    assert affected_fields("self", "A1") == frozenset({"A1"})
    assert affected_fields("self", "B2") == frozenset({"B2"})


def test_row_includes_self_and_full_row():
    assert affected_fields("row", "A2") == frozenset({"A1", "A2", "A3"})
    assert affected_fields("row", "C1") == frozenset({"C1", "C2", "C3"})


def test_column_includes_self_and_full_column():
    assert affected_fields("column", "B2") == frozenset({"A2", "B2", "C2"})
    assert affected_fields("column", "A3") == frozenset({"A3", "B3", "C3"})


def test_adjacent_at_center_has_four_neighbours():
    assert affected_fields("adjacent", "B2") == frozenset({"A2", "B1", "B3", "C2"})


def test_adjacent_at_corner_has_two_neighbours():
    assert affected_fields("adjacent", "A1") == frozenset({"A2", "B1"})
    assert affected_fields("adjacent", "C3") == frozenset({"B3", "C2"})


def test_adjacent_at_edge_has_three_neighbours():
    assert affected_fields("adjacent", "A2") == frozenset({"A1", "A3", "B2"})


def test_adjacent_excludes_self():
    for pos in POSITIONS:
        assert pos not in affected_fields("adjacent", pos)


def test_diagonal_at_center_has_four():
    assert affected_fields("diagonal", "B2") == frozenset({"A1", "A3", "C1", "C3"})


def test_diagonal_at_corner_has_one():
    assert affected_fields("diagonal", "A1") == frozenset({"B2"})
    assert affected_fields("diagonal", "C3") == frozenset({"B2"})


def test_diagonal_at_edge_has_two():
    assert affected_fields("diagonal", "A2") == frozenset({"B1", "B3"})
    assert affected_fields("diagonal", "B1") == frozenset({"A2", "C2"})


def test_diagonal_excludes_self():
    for pos in POSITIONS:
        assert pos not in affected_fields("diagonal", pos)


def test_mirror_corners_swap():
    assert affected_fields("mirror", "A1") == frozenset({"C3"})
    assert affected_fields("mirror", "C3") == frozenset({"A1"})
    assert affected_fields("mirror", "A3") == frozenset({"C1"})
    assert affected_fields("mirror", "C1") == frozenset({"A3"})


def test_mirror_center_is_self():
    assert affected_fields("mirror", "B2") == frozenset({"B2"})


def test_mirror_is_involutive():
    for pos in POSITIONS:
        (mirrored,) = affected_fields("mirror", pos)
        (back,) = affected_fields("mirror", mirrored)
        assert back == pos


def test_global_returns_all_positions():
    expected = frozenset(POSITIONS)
    for pos in ("A1", "B2", "C3"):
        assert affected_fields("global", pos) == expected


def test_unknown_pattern_raises():
    with pytest.raises(ValueError):
        affected_fields("teleport", "A1")


def test_unknown_position_raises():
    with pytest.raises(ValueError):
        affected_fields("row", "Z9")
