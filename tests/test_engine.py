"""Tests for the M5 run engine and training mode."""

from __future__ import annotations

from pathlib import Path

import pytest

from cclash.cards.loader import load_set
from cclash.cards.models import CardDef, CodeDef, EventDef, ItemDef
from cclash.core.effects import EffectSpec
from cclash.core.engine import (
    CompileError,
    EventPlay,
    GridSpec,
    ReconfigureError,
    compile_grid,
    play_match,
    scripted_reconfigure,
)
from cclash.core.grid import POSITIONS
from cclash.game.training import play_sample, play_training, sample_grid, training_seed

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


def test_training_sample_has_three_runs_with_total_39():
    """Pinned baseline: sample grid, no reconfigure. Per run: Cronling
    2+3, Patch Goblin 1+2, Vibe Bug 3+2 = 13."""
    cardset = load_set(ALPHA_DIR)
    grid = sample_grid(cardset)
    result = play_training(grid)
    assert len(result.runs) == 3
    assert [r.total_output for r in result.runs] == [13, 13, 13]
    assert result.total_output == 39


def test_training_run_log_contains_phase_headers():
    cardset = load_set(ALPHA_DIR)
    result = play_training(sample_grid(cardset))
    assert "Run 1" in result.log
    assert "Item Effects:" in result.log
    assert "Code Execution:" in result.log
    assert "Damage:" in result.log
    assert "Output Scoring:" in result.log
    assert "Final: 39 Output" in result.log


def test_play_sample_is_deterministic_and_plays_both_events():
    cardset = load_set(ALPHA_DIR)
    a = play_sample(cardset)
    b = play_sample(cardset)
    assert a.log == b.log
    assert a.seed == training_seed("local", "sample", cardset)
    assert len(a.reconfigures) == 2
    assert all("play" in line for line in a.reconfigures)
    # both events consumed: none left on the final grid
    assert not [c for c in a.final_cells.values() if c is not None and c.type == "event"]


def test_docker_buffs_only_codes_in_its_row_in_first_run():
    cardset = load_set(ALPHA_DIR)
    result = play_training(sample_grid(cardset))
    item_log = "\n".join(result.runs[0].item_phase)
    assert "Docker at A2 buffs Cronling (A1), +1 STAB" in item_log
    assert "Docker at A2 buffs Patch Goblin (A3), +1 STAB" in item_log
    assert "Docker at A2 buffs Vibe Bug" not in item_log  # row B, not row A; not a coder


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


# -- reconfigure --------------------------------------------------------


def _basic_cells(code_a1: CodeDef) -> dict[str, CardDef]:
    """3 Codes / 4 Items / 2 Events with the interesting Code at A1."""
    plain = _make_code(out=1, stab=9, suffix="pl")
    item = _make_dummy_item()
    return {
        "A1": code_a1,
        "A2": item,
        "A3": plain,
        "B1": item,
        "B2": plain,
        "B3": item,
        "C1": _make_dummy_event(),
        "C2": item,
        "C3": _make_dummy_event(),
    }


def test_reconfigure_plays_event_and_moves_cards():
    """Playing the rotate90 Event between runs rotates the grid; the
    consumed Event leaves an empty slot before the move applies."""
    cron = _make_code(out=2, stab=9, suffix="a")
    player = compile_grid(_basic_cells(cron))
    plan = scripted_reconfigure([EventPlay(event_pos="C1"), None])
    result = play_match(player, opponent=None, seed=0, reconfigure=plan)

    # rotate90 cw: A1 -> A3
    assert any(o.pos == "A1" and o.name == "T-a" for o in result.runs[0].outputs)
    assert any(o.pos == "A3" and o.name == "T-a" for o in result.runs[1].outputs)
    assert any("rotate90" in line for line in result.reconfigures)
    # 2 Events compiled, 1 consumed
    remaining_events = [
        c for c in result.final_cells.values() if c is not None and c.type == "event"
    ]
    assert len(remaining_events) == 1
    # one slot is now empty
    assert sum(1 for c in result.final_cells.values() if c is None) == 1


def test_reconfigure_pass_keeps_grid_stable():
    cron = _make_code(out=2, stab=9, suffix="a")
    player = compile_grid(_basic_cells(cron))
    result = play_match(player, opponent=None, seed=0, reconfigure=None)
    for run in result.runs:
        assert any(o.pos == "A1" and o.name == "T-a" for o in run.outputs)
    assert all("pass" in line for line in result.reconfigures)


def test_reconfigure_with_params_shifts_row():
    cron = _make_code(out=2, stab=9, suffix="a")
    cells = _basic_cells(cron)
    cells["C1"] = _make_event(move="shift_row", suffix="sr")
    player = compile_grid(cells)
    plan = scripted_reconfigure(
        [EventPlay(event_pos="C1", params={"source": "A", "target": "C"}), None]
    )
    result = play_match(player, opponent=None, seed=0, reconfigure=plan)
    # row A moved to row C: the A1 code now scores from C1
    assert any(o.pos == "C1" and o.name == "T-a" for o in result.runs[1].outputs)


def test_reconfigure_rejects_slot_without_event():
    cron = _make_code(out=2, stab=9, suffix="a")
    player = compile_grid(_basic_cells(cron))
    plan = scripted_reconfigure([EventPlay(event_pos="A1"), None])
    with pytest.raises(ReconfigureError, match="A1"):
        play_match(player, opponent=None, seed=0, reconfigure=plan)


def test_damage_travels_with_the_card_through_reconfigure():
    """Persistent damage belongs to the card, not the slot it happens
    to occupy (rules §5: STAB is a Code attribute)."""
    damaged = _make_code(out=2, stab=3, self_damage=2, suffix="dm")
    player = compile_grid(_basic_cells(damaged))
    plan = scripted_reconfigure([EventPlay(event_pos="C1"), None])
    result = play_match(player, opponent=None, seed=0, reconfigure=plan)

    # run 1: 2 damage at A1, survives (2 < 3). rotate90 moves it to A3.
    # run 2: 2 more damage -> 4 >= 3, disabled at its *new* position.
    assert "A3" in result.runs[1].disabled_after_run
    assert all(o.name != "T-dm" for o in result.runs[2].outputs)


# -- W6 rolls -----------------------------------------------------------


def test_roll_effect_is_seeded_and_logged():
    from cclash.core.dice import Dice

    roller = CodeDef(
        number="CC-T999-rl1",
        id="t_roller",
        name="T-rl",
        rarity="common",
        pattern="self",
        ascii=("[T]",),
        text=("Test.",),
        effects=(
            EffectSpec(
                trigger="end_of_run",
                type="damage",
                target="self",
                amount=1,
                roll=(1, 2, 3),
            ),
        ),
        faction="coder",
        out=1,
        stab=9,
    )
    player = compile_grid(_basic_cells(roller))
    seed = 42
    result = play_match(player, opponent=None, seed=seed, reconfigure=None)

    # the engine draws exactly one W6 per run for this card, same stream
    dice = Dice(seed=seed)
    expected_faces = [dice.d6() for _ in range(3)]
    expected_damage = sum(1 for f in expected_faces if f in (1, 2, 3))

    assert result.log.count("roll W6 ->") == 3
    for face in expected_faces:
        assert f"roll W6 -> {face}" in result.log
    total_damage = sum(
        d.net for run in result.runs for d in run.damage if d.side == "friendly" and d.pos == "A1"
    )
    assert total_damage == expected_damage


def test_same_seed_same_log_different_seed_may_differ():
    cardset = load_set(ALPHA_DIR)
    grid = sample_grid(cardset)
    a = play_match(grid, opponent=None, seed=7)
    b = play_match(grid, opponent=None, seed=7)
    assert a.log == b.log
    assert a.total_output == b.total_output


# -- new phases ---------------------------------------------------------


def test_before_damage_stab_buff_prevents_disable():
    """A +1 STAB buff fired in the before_damage phase raises the disable
    threshold for damage resolved in the same run."""
    fragile = _make_code(out=1, stab=2, self_damage=2, suffix="fg")
    buffer_code = CodeDef(
        number="CC-T999-bf1",
        id="t_buffer",
        name="T-buffer",
        rarity="common",
        pattern="adjacent",
        ascii=("[T]",),
        text=("Test.",),
        effects=(
            EffectSpec(
                trigger="before_damage",
                type="modify_stab",
                target="friendly_codes_adjacent",
                amount=1,
            ),
        ),
        faction="coder",
        out=1,
        stab=9,
    )
    item = _make_dummy_item()
    cells: dict[str, CardDef] = {
        "A1": fragile,
        "A2": buffer_code,
        "A3": _make_code(out=1, stab=9, suffix="pl"),
        "B1": item,
        "B2": item,
        "B3": item,
        "C1": _make_dummy_event(),
        "C2": item,
        "C3": _make_dummy_event(),
    }
    player = compile_grid(cells)
    result = play_match(player, opponent=None, seed=0)
    # 2 self damage vs stab 2+1: survives run 1, disabled in run 2 (4 >= 3)
    assert "A1" not in result.runs[0].disabled_after_run
    assert "A1" in result.runs[1].disabled_after_run


def test_end_of_run_damage_applies_after_scoring():
    """'lose 1 STAB after the Run' must not affect the run's own Output,
    but counts before the next run starts."""
    glass = CodeDef(
        number="CC-T999-eor",
        id="t_glass",
        name="T-glass",
        rarity="common",
        pattern="self",
        ascii=("[T]",),
        text=("Test.",),
        effects=(
            EffectSpec(
                trigger="end_of_run",
                type="damage",
                target="self",
                amount=1,
            ),
        ),
        faction="coder",
        out=3,
        stab=1,
    )
    player = compile_grid(_basic_cells(glass))
    result = play_match(player, opponent=None, seed=0)
    # scores in run 1, then takes the end-of-run hit and is disabled
    assert any(o.name == "T-glass" and o.final_out == 3 for o in result.runs[0].outputs)
    assert "A1" in result.runs[0].disabled_after_run
    assert all(o.name != "T-glass" for o in result.runs[1].outputs)


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
    return _make_event(move="rotate90", suffix="ev")


def _make_event(*, move: str, suffix: str) -> EventDef:
    return EventDef(
        number=f"CC-T999-{suffix}",
        id=f"t_event_{suffix}",
        name=f"TE-{suffix}",
        rarity="common",
        pattern="global",
        ascii=("[E]",),
        text=("Test.",),
        move=move,
    )
