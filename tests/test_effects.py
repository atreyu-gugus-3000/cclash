"""Tests for the M4 effect interpreter.

Covers:

- parsing of YAML effect entries (incl. error paths)
- target resolution to (side, positions)
- application of stat / damage effects to a MatchContext
- the three M4-DoD scenarios (Docker row STAB, Tmux column OUT,
  Cronling mirror damage)
- the explicit M4 boundary: grid-mutating effects raise NotImplementedError
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cclash.cards.loader import load_set
from cclash.cards.models import CodeDef, ItemDef
from cclash.core.effects import (
    EffectError,
    EffectSpec,
    MatchContext,
    SideState,
    apply_card_effects,
    apply_effect,
    parse_effect_entry,
    resolve_target,
)
from cclash.core.grid import POSITIONS, Grid

ALPHA_DIR = Path(__file__).resolve().parents[1] / "cardsets" / "alpha_001"


# -- parsing -----------------------------------------------------------


def test_parse_effect_entry_minimal():
    spec = parse_effect_entry(
        {
            "trigger": "item_phase",
            "effect": {"type": "modify_out", "target": "friendly_codes_in_row", "amount": 1},
        }
    )
    assert spec.trigger == "item_phase"
    assert spec.type == "modify_out"
    assert spec.target == "friendly_codes_in_row"
    assert spec.amount == 1


def test_parse_rejects_unknown_trigger():
    with pytest.raises(EffectError, match="trigger"):
        parse_effect_entry(
            {
                "trigger": "moonrise",
                "effect": {"type": "modify_out", "target": "self", "amount": 1},
            }
        )


def test_parse_rejects_unknown_type():
    with pytest.raises(EffectError, match="type"):
        parse_effect_entry(
            {"trigger": "item_phase", "effect": {"type": "lol", "target": "self", "amount": 1}}
        )


def test_parse_rejects_unknown_target():
    with pytest.raises(EffectError, match="target"):
        parse_effect_entry(
            {
                "trigger": "item_phase",
                "effect": {"type": "modify_out", "target": "everyone", "amount": 1},
            }
        )


def test_parse_rejects_missing_target_for_stat_effect():
    with pytest.raises(EffectError, match="target"):
        parse_effect_entry({"trigger": "item_phase", "effect": {"type": "modify_out", "amount": 1}})


def test_parse_rejects_missing_amount_for_damage():
    with pytest.raises(EffectError, match="amount"):
        parse_effect_entry(
            {"trigger": "code_execution", "effect": {"type": "damage", "target": "mirror"}}
        )


# -- target resolution -------------------------------------------------


def test_resolve_target_self_returns_friendly_source_only():
    side, positions = resolve_target("self", "B2")
    assert side == "friendly"
    assert positions == frozenset({"B2"})


def test_resolve_target_mirror_returns_enemy_mirror():
    side, positions = resolve_target("mirror", "A1")
    assert side == "enemy"
    assert positions == frozenset({"C3"})


def test_resolve_target_row_returns_friendly_row():
    side, positions = resolve_target("friendly_codes_in_row", "B2")
    assert side == "friendly"
    assert positions == frozenset({"B1", "B2", "B3"})


def test_resolve_target_unknown_raises():
    with pytest.raises(EffectError):
        resolve_target("not-a-target", "A1")


def test_resolve_target_invalid_source_raises():
    with pytest.raises(EffectError):
        resolve_target("self", "Z9")


# -- application of M4 effects -----------------------------------------


def _empty_context() -> MatchContext:
    return MatchContext(
        friendly=SideState(grid=_empty_grid()),
        enemy=SideState(grid=_empty_grid()),
    )


def _empty_grid() -> Grid:
    return Grid.from_rows([[None, None, None] for _ in range(3)])


def _put(side: SideState, pos: str, card) -> None:
    side.grid.cells[pos] = card


def test_modify_out_self_only_affects_source_slot():
    ctx = _empty_context()
    cron = _make_code(out=2, stab=4)
    _put(ctx.friendly, "B2", cron)
    apply_effect(EffectSpec(trigger="x", type="modify_out", target="self", amount=2), "B2", ctx)
    assert ctx.friendly.slots["B2"].out_delta == 2
    assert ctx.friendly.slots["A1"].out_delta == 0


def test_docker_row_buff_adds_stab_only_to_codes_in_row():
    """M4 DoD: Docker can buff row Codes."""
    cardset = load_set(ALPHA_DIR)
    docker = next(c for c in cardset.items if c.id == "docker")
    cron = next(c for c in cardset.codes if c.id == "cronling")

    ctx = _empty_context()
    _put(ctx.friendly, "B2", docker)
    _put(ctx.friendly, "B1", cron)
    _put(ctx.friendly, "B3", cron)
    _put(ctx.friendly, "A1", cron)
    _put(ctx.friendly, "C3", docker)  # not a Code, must be ignored

    apply_card_effects(docker, "B2", trigger="item_phase", ctx=ctx)

    assert ctx.friendly.slots["B1"].stab_delta == 1
    assert ctx.friendly.slots["B2"].stab_delta == 0  # docker is not a Code
    assert ctx.friendly.slots["B3"].stab_delta == 1
    assert ctx.friendly.slots["A1"].stab_delta == 0  # different row
    assert ctx.friendly.slots["C3"].stab_delta == 0


def test_tmux_column_buff_adds_out_only_to_codes_in_column():
    """M4 DoD: Tmux can buff column Codes."""
    cardset = load_set(ALPHA_DIR)
    tmux = next(c for c in cardset.items if c.id == "tmux")
    cron = next(c for c in cardset.codes if c.id == "cronling")

    ctx = _empty_context()
    _put(ctx.friendly, "B2", tmux)
    _put(ctx.friendly, "A2", cron)
    _put(ctx.friendly, "C2", cron)
    _put(ctx.friendly, "B1", cron)  # different column

    apply_card_effects(tmux, "B2", trigger="item_phase", ctx=ctx)

    assert ctx.friendly.slots["A2"].out_delta == 1
    assert ctx.friendly.slots["C2"].out_delta == 1
    assert ctx.friendly.slots["B1"].out_delta == 0
    assert ctx.friendly.slots["B2"].out_delta == 0


def test_cronling_mirror_damage_hits_enemy_mirror_slot():
    """M4 DoD: Cronling deals 1 damage to mirrored enemy slot on run."""
    cardset = load_set(ALPHA_DIR)
    cron = next(c for c in cardset.codes if c.id == "cronling")

    ctx = _empty_context()
    _put(ctx.friendly, "A1", cron)

    apply_card_effects(cron, "A1", trigger="code_execution", ctx=ctx)

    assert ctx.enemy.slots["C3"].incoming_damage == 1
    assert ctx.friendly.slots["A1"].incoming_damage == 0


def test_apply_card_effects_filters_by_trigger():
    cardset = load_set(ALPHA_DIR)
    cron = next(c for c in cardset.codes if c.id == "cronling")
    ctx = _empty_context()
    _put(ctx.friendly, "B2", cron)

    apply_card_effects(cron, "B2", trigger="item_phase", ctx=ctx)
    assert ctx.enemy.slots["B2"].incoming_damage == 0

    apply_card_effects(cron, "B2", trigger="code_execution", ctx=ctx)
    assert ctx.enemy.slots["B2"].incoming_damage == 1  # B2 mirrors to itself


def test_grid_mutating_effect_is_not_interpreted_in_m4():
    ctx = _empty_context()
    spec = EffectSpec(trigger="reconfigure", type="rotate_grid", target=None, amount=0)
    with pytest.raises(NotImplementedError, match="rotate_grid"):
        apply_effect(spec, "A1", ctx)


def test_sidestate_initialises_all_nine_slots():
    ctx = _empty_context()
    assert set(ctx.friendly.slots) == set(POSITIONS)
    assert set(ctx.enemy.slots) == set(POSITIONS)


def test_alpha_001_loads_with_parsed_effects():
    cardset = load_set(ALPHA_DIR)
    cron = next(c for c in cardset.codes if c.id == "cronling")
    docker = next(c for c in cardset.items if c.id == "docker")
    tmux = next(c for c in cardset.items if c.id == "tmux")
    assert len(cron.effects) == 1
    assert len(docker.effects) == 1
    assert len(tmux.effects) == 1
    assert cron.effects[0].type == "damage"
    assert docker.effects[0].type == "modify_stab"
    assert tmux.effects[0].type == "modify_out"


def _make_code(*, out: int, stab: int) -> CodeDef:
    return CodeDef(
        number="CC-T001-001",
        id="t",
        name="T",
        rarity="common",
        pattern="self",
        ascii=("[T]",),
        text=("Test.",),
        faction="coder",
        out=out,
        stab=stab,
    )


def _make_item() -> ItemDef:
    return ItemDef(
        number="CC-T001-002",
        id="t2",
        name="T2",
        rarity="common",
        pattern="self",
        ascii=("[I]",),
        text=("Test.",),
        family="infra",
        uses=1,
    )
