"""Tests for the 3x3 Grid and its Reconfigure moves.

Examples mirror docs/rules_v0_1.md §6 exactly.
"""

from __future__ import annotations

import pytest

from cclash.core.grid import Grid

# Shorthand reference grid:
#   A B C
#   D E F
#   G H I
DEFAULT_ROWS = [
    ["A", "B", "C"],
    ["D", "E", "F"],
    ["G", "H", "I"],
]


def make_grid() -> Grid:
    return Grid.from_rows(DEFAULT_ROWS)


def test_from_rows_indexing():
    grid = make_grid()
    assert grid["A1"] == "A"
    assert grid["B2"] == "E"
    assert grid["C3"] == "I"
    assert grid.as_rows() == DEFAULT_ROWS


def test_from_rows_rejects_wrong_shape():
    with pytest.raises(ValueError):
        Grid.from_rows([["A", "B"], ["C", "D"]])


def test_rotate90_matches_spec():
    grid = make_grid()
    grid.rotate90()
    assert grid.as_rows() == [
        ["G", "D", "A"],
        ["H", "E", "B"],
        ["I", "F", "C"],
    ]


def test_rotate90ccw_matches_spec():
    grid = make_grid()
    grid.rotate90ccw()
    assert grid.as_rows() == [
        ["C", "F", "I"],
        ["B", "E", "H"],
        ["A", "D", "G"],
    ]


def test_rotate90_four_times_is_identity():
    grid = make_grid()
    for _ in range(4):
        grid.rotate90()
    assert grid.as_rows() == DEFAULT_ROWS


def test_rotate90_then_rotate90ccw_is_identity():
    grid = make_grid()
    grid.rotate90()
    grid.rotate90ccw()
    assert grid.as_rows() == DEFAULT_ROWS


def test_shift_row_C_to_A_matches_spec():
    grid = make_grid()
    grid.shift_row("C", "A")
    assert grid.as_rows() == [
        ["G", "H", "I"],
        ["A", "B", "C"],
        ["D", "E", "F"],
    ]


def test_shift_row_same_position_is_noop_and_no_history():
    grid = make_grid()
    grid.shift_row("B", "B")
    assert grid.as_rows() == DEFAULT_ROWS
    with pytest.raises(ValueError):
        grid.rollback()


def test_shift_column_3_to_1_matches_spec():
    grid = make_grid()
    grid.shift_column("3", "1")
    assert grid.as_rows() == [
        ["C", "A", "B"],
        ["F", "D", "E"],
        ["I", "G", "H"],
    ]


def test_shift_column_invalid_raises():
    grid = make_grid()
    with pytest.raises(ValueError):
        grid.shift_column("4", "1")


def test_outer_ring_rotate_one_step_matches_spec():
    grid = make_grid()
    grid.outer_ring_rotate()
    assert grid.as_rows() == [
        ["D", "A", "B"],
        ["G", "E", "C"],
        ["H", "I", "F"],
    ]


def test_outer_ring_rotate_eight_steps_is_identity():
    grid = make_grid()
    grid.outer_ring_rotate(steps=8)
    assert grid.as_rows() == DEFAULT_ROWS


def test_outer_ring_rotate_does_not_touch_center():
    grid = make_grid()
    grid.outer_ring_rotate(steps=3)
    assert grid["B2"] == "E"


def test_swap_adjacent_vertical_matches_spec():
    grid = make_grid()
    grid.swap_adjacent("A2", "B2")
    assert grid.as_rows() == [
        ["A", "E", "C"],
        ["D", "B", "F"],
        ["G", "H", "I"],
    ]


def test_swap_adjacent_horizontal():
    grid = make_grid()
    grid.swap_adjacent("A1", "A2")
    assert grid.as_rows() == [
        ["B", "A", "C"],
        ["D", "E", "F"],
        ["G", "H", "I"],
    ]


def test_swap_diagonal_raises():
    grid = make_grid()
    with pytest.raises(ValueError):
        grid.swap_adjacent("A1", "B2")


def test_swap_non_adjacent_raises():
    grid = make_grid()
    with pytest.raises(ValueError):
        grid.swap_adjacent("A1", "A3")


def test_swap_unknown_position_raises():
    grid = make_grid()
    with pytest.raises(ValueError):
        grid.swap_adjacent("A1", "Z9")


def test_rollback_restores_previous_state():
    grid = make_grid()
    grid.rotate90()
    grid.rollback()
    assert grid.as_rows() == DEFAULT_ROWS


def test_rollback_only_undoes_one_step():
    grid = make_grid()
    grid.rotate90()
    grid.shift_row("C", "A")
    grid.rollback()
    # rollback restored the post-rotate90 state, not the original
    assert grid.as_rows() == [
        ["G", "D", "A"],
        ["H", "E", "B"],
        ["I", "F", "C"],
    ]
    with pytest.raises(ValueError):
        grid.rollback()


def test_rollback_without_history_raises():
    grid = make_grid()
    with pytest.raises(ValueError):
        grid.rollback()


def test_moves_are_deterministic():
    grid_a = make_grid()
    grid_b = make_grid()
    for grid in (grid_a, grid_b):
        grid.rotate90()
        grid.shift_column("3", "1")
        grid.outer_ring_rotate(steps=2)
        grid.swap_adjacent("B2", "B3")
    assert grid_a.as_rows() == grid_b.as_rows()
