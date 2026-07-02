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
    condition_holds,
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
    vibe = next(c for c in cardset.codes if c.id == "vibe_bug")
    assert [e.type for e in cron.effects] == ["modify_out", "damage"]
    assert cron.effects[0].condition == ("row_has_item", True)
    assert [e.type for e in docker.effects] == ["modify_stab", "modify_out"]
    assert docker.effects[1].target == "adjacent_coder_codes"
    assert len(tmux.effects) == 1
    assert tmux.effects[0].type == "modify_out"
    assert vibe.effects[1].roll == (1, 2, 3)
    assert vibe.effects[1].condition == ("diagonal_has_event", False)


def test_alpha_001_only_promptling_lacks_machine_effects():
    """Every alpha card except Promptling is machine-readable (Promptling
    is blocked on XP/M7 and a randomness rules decision, see its notes)."""
    cardset = load_set(ALPHA_DIR)
    without_effects = [c.id for c in cardset.codes + cardset.items if not c.effects]
    assert without_effects == ["promptling"]


# -- conditions ---------------------------------------------------------


def test_parse_condition_single_key():
    spec = parse_effect_entry(
        {
            "trigger": "code_execution",
            "condition": {"row_has_item": True},
            "effect": {"type": "modify_out", "target": "self", "amount": 1},
        }
    )
    assert spec.condition == ("row_has_item", True)


def test_parse_rejects_unknown_condition():
    with pytest.raises(EffectError, match="condition"):
        parse_effect_entry(
            {
                "trigger": "code_execution",
                "condition": {"moon_phase": "full"},
                "effect": {"type": "modify_out", "target": "self", "amount": 1},
            }
        )


def test_parse_rejects_multi_key_condition():
    with pytest.raises(EffectError, match="condition"):
        parse_effect_entry(
            {
                "trigger": "code_execution",
                "condition": {"row_has_item": True, "diagonal_has_event": True},
                "effect": {"type": "modify_out", "target": "self", "amount": 1},
            }
        )


def test_parse_rejects_wrong_condition_value_type():
    with pytest.raises(EffectError, match="condition"):
        parse_effect_entry(
            {
                "trigger": "code_execution",
                "condition": {"column_items_exactly": "one"},
                "effect": {"type": "modify_out", "target": "self", "amount": 1},
            }
        )


def test_condition_row_has_item():
    ctx = _empty_context()
    _put(ctx.friendly, "A1", _make_code(out=1, stab=1))
    assert not condition_holds(("row_has_item", True), "A1", ctx)
    _put(ctx.friendly, "A3", _make_item())
    assert condition_holds(("row_has_item", True), "A1", ctx)
    # source slot itself never satisfies the condition
    assert not condition_holds(("row_has_item", True), "B1", ctx)


def test_condition_diagonal_has_event_true_and_false():
    cardset = load_set(ALPHA_DIR)
    event = next(e for e in cardset.events if e.id == "rotate90")
    ctx = _empty_context()
    _put(ctx.friendly, "B2", _make_code(out=1, stab=1))
    assert condition_holds(("diagonal_has_event", False), "B2", ctx)
    _put(ctx.friendly, "A1", event)
    assert condition_holds(("diagonal_has_event", True), "B2", ctx)
    assert not condition_holds(("diagonal_has_event", False), "B2", ctx)


def test_condition_adjacent_faction_and_negation():
    coder = _make_code(out=1, stab=1)  # faction coder
    ctx = _empty_context()
    _put(ctx.friendly, "B2", coder)
    assert not condition_holds(("adjacent_faction", "coder"), "B2", ctx)
    assert condition_holds(("not_adjacent_faction", "coder"), "B2", ctx)
    _put(ctx.friendly, "B1", coder)
    assert condition_holds(("adjacent_faction", "coder"), "B2", ctx)
    assert not condition_holds(("not_adjacent_faction", "coder"), "B2", ctx)


def test_condition_row_has_card():
    cardset = load_set(ALPHA_DIR)
    docker = next(c for c in cardset.items if c.id == "docker")
    ctx = _empty_context()
    _put(ctx.friendly, "C1", _make_code(out=1, stab=1))
    assert not condition_holds(("row_has_card", "docker"), "C1", ctx)
    _put(ctx.friendly, "C3", docker)
    assert condition_holds(("row_has_card", "docker"), "C1", ctx)


def test_condition_column_items_exactly():
    ctx = _empty_context()
    _put(ctx.friendly, "A2", _make_code(out=1, stab=1))
    assert condition_holds(("column_items_exactly", 0), "A2", ctx)
    _put(ctx.friendly, "B2", _make_item())
    assert condition_holds(("column_items_exactly", 1), "A2", ctx)
    assert not condition_holds(("column_items_exactly", 2), "A2", ctx)


def test_apply_card_effects_skips_effects_with_false_condition():
    conditional = CodeDef(
        number="CC-T001-009",
        id="t9",
        name="T9",
        rarity="common",
        pattern="self",
        ascii=("[T]",),
        text=("Test.",),
        effects=(
            EffectSpec(
                trigger="code_execution",
                type="modify_out",
                target="self",
                amount=2,
                condition=("row_has_item", True),
            ),
        ),
        faction="coder",
        out=1,
        stab=1,
    )
    ctx = _empty_context()
    _put(ctx.friendly, "A1", conditional)
    apply_card_effects(conditional, "A1", trigger="code_execution", ctx=ctx)
    assert ctx.friendly.slots["A1"].out_delta == 0
    _put(ctx.friendly, "A2", _make_item())
    apply_card_effects(conditional, "A1", trigger="code_execution", ctx=ctx)
    assert ctx.friendly.slots["A1"].out_delta == 2


# -- W6 roll clause -----------------------------------------------------


def test_parse_roll_faces():
    spec = parse_effect_entry(
        {
            "trigger": "end_of_run",
            "roll": {"on": [1, 2, 3]},
            "effect": {"type": "damage", "target": "self", "amount": 1},
        }
    )
    assert spec.roll == (1, 2, 3)


def test_parse_rejects_empty_or_invalid_roll_faces():
    for faces in ([], [0], [7], "1-3"):
        with pytest.raises(EffectError, match="roll"):
            parse_effect_entry(
                {
                    "trigger": "end_of_run",
                    "roll": {"on": faces},
                    "effect": {"type": "damage", "target": "self", "amount": 1},
                }
            )


def test_apply_card_effects_refuses_roll_effects():
    """Rolls need the match dice stream; only the run engine resolves them."""
    card = CodeDef(
        number="CC-T001-010",
        id="t10",
        name="T10",
        rarity="common",
        pattern="self",
        ascii=("[T]",),
        text=("Test.",),
        effects=(
            EffectSpec(
                trigger="code_execution",
                type="damage",
                target="self",
                amount=1,
                roll=(1, 2, 3),
            ),
        ),
        faction="coder",
        out=1,
        stab=1,
    )
    ctx = _empty_context()
    _put(ctx.friendly, "A1", card)
    with pytest.raises(EffectError, match="roll"):
        apply_card_effects(card, "A1", trigger="code_execution", ctx=ctx)


# -- adjacent_coder_codes target ----------------------------------------


def test_adjacent_coder_codes_targets_only_adjacent_coder_faction():
    cardset = load_set(ALPHA_DIR)
    cron = next(c for c in cardset.codes if c.id == "cronling")  # coder
    vibe = next(c for c in cardset.codes if c.id == "vibe_bug")  # vibecoder

    ctx = _empty_context()
    _put(ctx.friendly, "B1", cron)
    _put(ctx.friendly, "A2", vibe)
    _put(ctx.friendly, "A1", _make_item())  # source

    spec = EffectSpec(
        trigger="item_phase", type="modify_out", target="adjacent_coder_codes", amount=1
    )
    apply_effect(spec, "A1", ctx)
    assert ctx.friendly.slots["B1"].out_delta == 1  # coder, adjacent
    assert ctx.friendly.slots["A2"].out_delta == 0  # vibecoder, adjacent
    assert ctx.friendly.slots["A1"].out_delta == 0  # source item


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
