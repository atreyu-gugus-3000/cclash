"""Effect interpreter for cclash.

Effects are declarative data; this module is the only place that turns
that data into state mutations. Card YAML files describe each effect
as a (trigger, effect) pair; the interpreter resolves the effect's
target into a set of grid positions and applies the corresponding
delta to a :class:`MatchContext`.

Slot effects here are stat modifiers (``modify_out``, ``modify_stab``)
and damage (``damage``, ``prevent_damage``), optionally gated by a
``condition`` and/or a W6 ``roll`` clause. Grid-mutating effect types
(``rotate_grid``, ``shift_row`` etc.) are whitelisted for the schema but
have no slot target; the run engine applies them as Event *moves* during
the Reconfigure phase (see ``cclash.core.engine._apply_move``), so
``apply_effect`` rejects them.

Determinism: the interpreter never reads time or random state — roll
clauses are resolved by the run engine, which owns the single match
dice stream. Iteration over affected positions is sorted to keep run
logs reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from cclash.cards.models import CardDef
from cclash.core.grid import POSITIONS, Grid
from cclash.core.patterns import (
    pattern_adjacent,
    pattern_column,
    pattern_diagonal,
    pattern_global,
    pattern_mirror,
    pattern_row,
    pattern_self,
)

VALID_EFFECT_TYPES: frozenset[str] = frozenset(
    {
        "modify_out",
        "modify_stab",
        "damage",
        "prevent_damage",
        "rotate_grid",
        "shift_column",
        "shift_row",
        "outer_ring_rotate",
        "swap_adjacent",
        "rollback",
    }
)

VALID_TRIGGERS: frozenset[str] = frozenset(
    {
        "item_phase",
        "code_execution",
        "before_damage",
        "after_damage",
        "end_of_run",
        "reconfigure",
        "on_disable",
    }
)

VALID_TARGETS: frozenset[str] = frozenset(
    {
        "self",
        "mirror",
        "friendly_codes_in_row",
        "friendly_codes_in_column",
        "friendly_codes_adjacent",
        "friendly_codes_diagonal",
        "adjacent_coder_codes",
        "all_friendly_codes",
    }
)

# Condition kinds with their expected value type (card_model.md §5).
# All conditions are evaluated on the friendly grid relative to the
# effect's source position; row/column/diagonal kinds ignore the source
# slot itself except column_items_exactly, which counts the full column.
VALID_CONDITIONS: dict[str, type] = {
    "adjacent_faction": str,
    "not_adjacent_faction": str,
    "row_has_item": bool,
    "diagonal_has_event": bool,
    "row_has_card": str,
    "column_items_exactly": int,
}

_STAT_OR_DAMAGE_TYPES: frozenset[str] = frozenset(
    {"modify_out", "modify_stab", "damage", "prevent_damage"}
)

_GRID_EFFECT_TYPES: frozenset[str] = frozenset(
    {"rotate_grid", "shift_column", "shift_row", "outer_ring_rotate", "swap_adjacent", "rollback"}
)


Side = Literal["friendly", "enemy"]


class EffectError(ValueError):
    """Raised when an effect spec is malformed or refers to unknown names."""


@dataclass(frozen=True, kw_only=True)
class EffectSpec:
    trigger: str
    type: str
    target: str | None = None
    amount: int = 0
    condition: tuple[str, str | int | bool] | None = None
    roll: tuple[int, ...] | None = None


def parse_effect_entry(raw: Any) -> EffectSpec:
    """Parse one entry from a card's ``effects`` YAML list.

    Schema (matches ``docs/card_model.md §5``):

    .. code-block:: yaml

        - trigger: item_phase
          condition:            # optional, single key from VALID_CONDITIONS
            adjacent_faction: coder
          roll:                 # optional, W6 faces on which the effect fires
            on: [1, 2, 3]
          effect:
            type: modify_stab
            target: friendly_codes_in_row
            amount: 1
    """
    if not isinstance(raw, dict):
        raise EffectError(f"effect entry must be a mapping, got {type(raw).__name__}")
    if "trigger" not in raw:
        raise EffectError("effect entry missing 'trigger'")
    if "effect" not in raw:
        raise EffectError("effect entry missing 'effect'")
    trigger = str(raw["trigger"])
    if trigger not in VALID_TRIGGERS:
        raise EffectError(f"unknown trigger: {trigger!r}")

    eff = raw["effect"]
    if not isinstance(eff, dict):
        raise EffectError("'effect' must be a mapping")
    if "type" not in eff:
        raise EffectError("effect missing 'type'")
    etype = str(eff["type"])
    if etype not in VALID_EFFECT_TYPES:
        raise EffectError(f"unknown effect type: {etype!r}")

    target: str | None = None
    amount = 0
    if etype in _STAT_OR_DAMAGE_TYPES:
        if "target" not in eff:
            raise EffectError(f"{etype} requires 'target'")
        target = str(eff["target"])
        if target not in VALID_TARGETS:
            raise EffectError(f"unknown target: {target!r}")
        if "amount" not in eff:
            raise EffectError(f"{etype} requires 'amount'")
        amount = int(eff["amount"])

    return EffectSpec(
        trigger=trigger,
        type=etype,
        target=target,
        amount=amount,
        condition=_parse_condition(raw.get("condition")),
        roll=_parse_roll(raw.get("roll")),
    )


def _parse_condition(raw: Any) -> tuple[str, str | int | bool] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict) or len(raw) != 1:
        raise EffectError("condition must be a mapping with exactly one key")
    kind, value = next(iter(raw.items()))
    kind = str(kind)
    if kind not in VALID_CONDITIONS:
        raise EffectError(f"unknown condition: {kind!r}")
    expected = VALID_CONDITIONS[kind]
    # bool is a subclass of int; require an exact match either way
    if type(value) is not expected:
        raise EffectError(f"condition {kind!r} expects a {expected.__name__} value, got {value!r}")
    return (kind, value)


def _parse_roll(raw: Any) -> tuple[int, ...] | None:
    if raw is None:
        return None
    # YAML 1.1 parses a bare `on:` key as boolean True; accept both spellings.
    if isinstance(raw, dict):
        raw = {("on" if k is True else k): v for k, v in raw.items()}
    if not isinstance(raw, dict) or set(raw) != {"on"}:
        raise EffectError("roll must be a mapping with exactly the key 'on'")
    faces = raw["on"]
    if not isinstance(faces, list) or not faces:
        raise EffectError("roll 'on' must be a non-empty list of W6 faces")
    out: set[int] = set()
    for f in faces:
        if type(f) is not int or not 1 <= f <= 6:
            raise EffectError(f"roll face must be an int in 1..6, got {f!r}")
        out.add(f)
    return tuple(sorted(out))


@dataclass
class SlotState:
    out_delta: int = 0
    stab_delta: int = 0
    incoming_damage: int = 0
    prevented_damage: int = 0


@dataclass
class SideState:
    """One player's side of the match, paired with per-slot accumulators.

    ``grid.cells[pos]`` holds the card definition currently in that slot
    (or ``None`` for empty). The interpreter never mutates the grid for
    stat/damage effects — only ``slots`` is updated.
    """

    grid: Grid
    slots: dict[str, SlotState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for pos in POSITIONS:
            self.slots.setdefault(pos, SlotState())


@dataclass
class MatchContext:
    friendly: SideState
    enemy: SideState


def resolve_target(target: str, source_pos: str) -> tuple[Side, frozenset[str]]:
    """Resolve a target name to (side, positions) without filtering by content.

    Filtering ("only Codes" for ``friendly_codes_*``) happens in
    :func:`apply_effect`, after the side has been picked.
    """
    if source_pos not in POSITIONS:
        raise EffectError(f"unknown source position: {source_pos!r}")

    if target == "self":
        return "friendly", pattern_self(source_pos)
    if target == "mirror":
        return "enemy", pattern_mirror(source_pos)
    if target == "friendly_codes_in_row":
        return "friendly", pattern_row(source_pos)
    if target == "friendly_codes_in_column":
        return "friendly", pattern_column(source_pos)
    if target == "friendly_codes_adjacent":
        return "friendly", pattern_adjacent(source_pos)
    if target == "friendly_codes_diagonal":
        return "friendly", pattern_diagonal(source_pos)
    if target == "adjacent_coder_codes":
        return "friendly", pattern_adjacent(source_pos)
    if target == "all_friendly_codes":
        return "friendly", pattern_global(source_pos)
    raise EffectError(f"unknown target: {target!r}")


def condition_holds(
    condition: tuple[str, str | int | bool],
    source_pos: str,
    ctx: MatchContext,
) -> bool:
    """Evaluate a parsed effect condition against the friendly grid."""
    kind, value = condition
    grid = ctx.friendly.grid

    def cells_at(positions: frozenset[str], *, include_source: bool = False) -> list[Any]:
        return [
            grid.cells.get(p)
            for p in positions
            if (include_source or p != source_pos) and grid.cells.get(p) is not None
        ]

    if kind == "adjacent_faction":
        return any(
            _card_type(c) == "code" and getattr(c, "faction", None) == value
            for c in cells_at(pattern_adjacent(source_pos))
        )
    if kind == "not_adjacent_faction":
        return not condition_holds(("adjacent_faction", value), source_pos, ctx)
    if kind == "row_has_item":
        found = any(_card_type(c) == "item" for c in cells_at(pattern_row(source_pos)))
        return found is value
    if kind == "diagonal_has_event":
        found = any(_card_type(c) == "event" for c in cells_at(pattern_diagonal(source_pos)))
        return found is value
    if kind == "row_has_card":
        return any(getattr(c, "id", None) == value for c in cells_at(pattern_row(source_pos)))
    if kind == "column_items_exactly":
        count = sum(
            1
            for c in cells_at(pattern_column(source_pos), include_source=True)
            if _card_type(c) == "item"
        )
        return count == value
    raise EffectError(f"unknown condition: {kind!r}")


def apply_effect(effect: EffectSpec, source_pos: str, ctx: MatchContext) -> None:
    """Apply a single effect to the match context.

    Stat and damage effects accumulate on the target slots' :class:`SlotState`.
    Grid effects are accepted by the schema but raise :class:`NotImplementedError`
    here; the run engine in M5 owns grid mutation.
    """
    if effect.type in _GRID_EFFECT_TYPES:
        raise NotImplementedError(f"grid-mutating effect {effect.type!r} is not interpreted in M4")
    if effect.type not in _STAT_OR_DAMAGE_TYPES:
        raise EffectError(f"unsupported effect type: {effect.type!r}")
    if effect.target is None:
        raise EffectError(f"{effect.type} requires a target")

    side, positions = resolve_target(effect.target, source_pos)
    side_state = ctx.friendly if side == "friendly" else ctx.enemy
    affected = _filter_positions(
        positions, side_state, _restrict_to_codes(effect.target), _required_faction(effect.target)
    )

    for pos in sorted(affected):
        slot = side_state.slots[pos]
        if effect.type == "modify_out":
            slot.out_delta += effect.amount
        elif effect.type == "modify_stab":
            slot.stab_delta += effect.amount
        elif effect.type == "damage":
            slot.incoming_damage += effect.amount
        elif effect.type == "prevent_damage":
            slot.prevented_damage += effect.amount


def apply_card_effects(
    card: CardDef,
    source_pos: str,
    trigger: str,
    ctx: MatchContext,
) -> None:
    """Apply every effect on ``card`` whose trigger matches ``trigger``.

    Card-internal effect order is preserved. Effects whose condition does
    not hold are skipped. Roll-gated effects are rejected here: only the
    run engine owns the match dice stream (randomness_v0_1.md §4).
    """
    if trigger not in VALID_TRIGGERS:
        raise EffectError(f"unknown trigger: {trigger!r}")
    for effect in card.effects:
        if effect.trigger != trigger:
            continue
        if effect.roll is not None:
            raise EffectError("roll effects are resolved by the run engine, not apply_card_effects")
        if effect.condition is not None and not condition_holds(effect.condition, source_pos, ctx):
            continue
        apply_effect(effect, source_pos, ctx)


def affected_targets(
    effect: EffectSpec,
    source_pos: str,
    ctx: MatchContext,
) -> tuple[Side, set[str]]:
    """Resolve the slots an effect would touch given the current grid state.

    Returns the (side, positions) pair the run engine uses for logging
    and for previewing what an effect would do without applying it.
    Grid-mutating effects have no positional target and yield ``("friendly", set())``.
    """
    if effect.type in _GRID_EFFECT_TYPES or effect.target is None:
        return "friendly", set()
    side, positions = resolve_target(effect.target, source_pos)
    side_state = ctx.friendly if side == "friendly" else ctx.enemy
    return side, _filter_positions(
        positions, side_state, _restrict_to_codes(effect.target), _required_faction(effect.target)
    )


def _restrict_to_codes(target: str) -> bool:
    return (
        target.startswith("friendly_codes_")
        or target == "all_friendly_codes"
        or target == "adjacent_coder_codes"
    )


def _required_faction(target: str) -> str | None:
    return "coder" if target == "adjacent_coder_codes" else None


def _card_type(cell: Any) -> str | None:
    # Duck-typed so the run engine can put runtime wrappers (card + damage
    # state) into grid cells instead of bare CardDef objects.
    return getattr(cell, "type", None)


def _filter_positions(
    positions: frozenset[str],
    side_state: SideState,
    only_codes: bool,
    faction: str | None = None,
) -> set[str]:
    if not only_codes:
        return set(positions)
    out: set[str] = set()
    for pos in positions:
        cell = side_state.grid.cells.get(pos)
        if _card_type(cell) != "code":
            continue
        if faction is not None and getattr(cell, "faction", None) != faction:
            continue
        out.add(pos)
    return out
