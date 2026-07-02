"""Tests for the M5 run engine and training mode."""

from __future__ import annotations

from pathlib import Path

import pytest

from cclash.cards.loader import load_set
from cclash.cards.models import CardDef, CodeDef, EventDef, ItemDef
from cclash.core.engine import (
    CompileError,
    GridSpec,
    compile_grid,
    play_match,
)
from cclash.core.grid import POSITIONS
from cclash.game.training import play_training, sample_grid

ALPHA_DIR = Path(__file__).resolve().parents[1] / "cardsets" / "alpha_001"


# -- compile -----------------------------------------------------------


def test_compile_accepts_3_codes_4_items_2_events():
    cardset = load_set(ALPHA_DIR)
    grid = sample_grid(cardset)
    spec = grid
    assert isinstance(spec, GridSpec)
    assert len(spec.codes()) == 3
    assert len(spec.items()) == 4
    assert len(spec.events()) == 2


def test_compile_rejects_missing_position():
    cardset = load_set(ALPHA_DIR)
    by_id = {c.id: c for c in cardset.all_cards()}
    cells = {p: by_id["cronling"] for p in POSITIONS if p != "C3"}
    with pytest.raises(CompileError, match="9 positions"):
        compile_grid(cells)


def test_compile_rejects_wrong_loadout():
    cardset = load_set(ALPHA_DIR)
    by_id = {c.id: c for c in cardset.all_cards()}
    cron = by_id["cronling"]
    cells = {p: cron for p in POSITIONS}
    with pytest.raises(CompileError, match="loadout"):
        compile_grid(cells)


# -- training / DoD scenario ------------------------------------------


def test_training_sample_has_three_runs_with_total_21():
    cardset = load_set(ALPHA_DIR)
    grid = sample_grid(cardset)
    result = play_training(grid)
    assert len(result.runs) == 3
    assert [r.total_output for r in result.runs] == [7, 7, 7]
    assert result.total_output == 21


def test_training_run_log_contains_phase_headers():
    cardset = load_set(ALPHA_DIR)
    result = play_training(sample_grid(cardset))
    assert "Run 1" in result.log
    assert "Item Effects:" in result.log
    assert "Code Execution:" in result.log
    assert "Damage:" in result.log
    assert "Output Scoring:" in result.log
    assert "Final: 21 Output" in result.log


def test_docker_buffs_only_codes_in_its_row_in_first_run():
    cardset = load_set(ALPHA_DIR)
    result = play_training(sample_grid(cardset))
    item_log = "\n".join(result.runs[0].item_phase)
    assert "Docker at A2 buffs Cronling (A1), +1 STAB" in item_log
    assert "Docker at A2 buffs Patch Goblin (A3), +1 STAB" in item_log
    assert "Vibe Bug" not in item_log  # row B, not row A


def test_tmux_buffs_only_codes_in_its_column_in_first_run():
    cardset = load_set(ALPHA_DIR)
    result = play_training(sample_grid(cardset))
    item_log = "\n".join(result.runs[0].item_phase)
    assert "Tmux at B1 buffs Cronling (A1), +1 OUT" in item_log
    # Patch Goblin (A3) and Vibe Bug (B2) are not in column 1
    assert "Tmux at B1 buffs Patch Goblin" not in item_log
    assert "Tmux at B1 buffs Vibe Bug" not in item_log


def test_cronling_mirror_damage_lands_on_enemy_c3_each_run():
    cardset = load_set(ALPHA_DIR)
    result = play_training(sample_grid(cardset))
    for run in result.runs:
        assert any(d.side == "enemy" and d.pos == "C3" and d.net == 1 for d in run.damage)


def test_disabled_code_stops_firing_and_scoring():
    """A code whose accumulated damage exceeds STAB is disabled and
    skipped from later runs' outputs and effect firing.
    """
    self_damager = _make_code(out=2, stab=1, self_damage=2, suffix="sd")
    plain_code = _make_code(out=1, stab=5, suffix="plain")
    item = _make_dummy_item()
    event = _make_dummy_event()

    cells: dict[str, CardDef] = {
        "A1": self_damager,
        "A2": item,
        "A3": plain_code,
        "B1": item,
        "B2": plain_code,
        "B3": item,
        "C1": event,
        "C2": item,
        "C3": event,
    }
    player = compile_grid(cells)
    result = play_match(player, opponent=None)

    assert "A1" in result.runs[0].disabled_after_run
    # disable is checked before output scoring (rules §5: damage → disable → score)
    assert all(o.pos != "A1" for o in result.runs[0].outputs)
    assert all(o.pos != "A1" for o in result.runs[1].outputs)
    assert all(o.pos != "A1" for o in result.runs[2].outputs)


# -- helpers -----------------------------------------------------------


def _make_code(
    *,
    out: int,
    stab: int,
    suffix: str,
    self_damage: int = 0,
) -> CodeDef:
    from cclash.core.effects import EffectSpec

    effects: tuple[EffectSpec, ...] = ()
    if self_damage > 0:
        effects = (
            EffectSpec(
                trigger="code_execution",
                type="damage",
                target="self",
                amount=self_damage,
            ),
        )
    return CodeDef(
        number=f"CC-T999-{suffix:>03}",
        id=f"t_code_{suffix}",
        name=f"T-{suffix}",
        rarity="common",
        pattern="self",
        ascii=("[T]",),
        text=("Test.",),
        effects=effects,
        faction="coder",
        out=out,
        stab=stab,
    )


def _make_dummy_item() -> ItemDef:
    return ItemDef(
        number="CC-T999-002",
        id="t_item",
        name="TI",
        rarity="common",
        pattern="self",
        ascii=("[I]",),
        text=("Test.",),
        family="infra",
        uses=1,
    )


def _make_dummy_event() -> EventDef:
    return EventDef(
        number="CC-T999-003",
        id="t_event",
        name="TE",
        rarity="common",
        pattern="global",
        ascii=("[E]",),
        text=("Test.",),
        move="rotate90",
    )
