"""Effect interpreter for cclash.

Effects are declarative data; this module is the only place that turns
that data into state mutations. Card YAML files describe each effect
as a (trigger, effect) pair; the interpreter resolves the effect's
target into a set of grid positions and applies the corresponding
delta to a :class:`MatchContext`.

Scope in M4: stat modifiers (``modify_out``, ``modify_stab``) and damage
(``damage``, ``prevent_damage``). Grid-mutating effects (``rotate_grid``,
``shift_row`` etc.) are part of the whitelist for forward compatibility
but are not interpreted yet — they land with M5 alongside the run
engine, where event ordering and rollback semantics belong.

Determinism: the interpreter never reads time or random state. Iteration
over affected positions is sorted to keep run logs reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from cclash.cards.models import CardDef, CodeDef
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
        "all_friendly_codes",
    }
)

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


def parse_effect_entry(raw: Any) -> EffectSpec:
    """Parse one entry from a card's ``effects`` YAML list.

    Schema (matches ``docs/card_model.md §5``):

    .. code-block:: yaml

        - trigger: item_phase
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

    return EffectSpec(trigger=trigger, type=etype, target=target, amount=amount)


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
    if target == "all_friendly_codes":
        return "friendly", pattern_global(source_pos)
    raise EffectError(f"unknown target: {target!r}")


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
    affected = _filter_positions(positions, side_state, _restrict_to_codes(effect.target))

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

    Card-internal effect order is preserved.
    """
    if trigger not in VALID_TRIGGERS:
        raise EffectError(f"unknown trigger: {trigger!r}")
    for effect in card.effects:
        if effect.trigger == trigger:
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
    return side, _filter_positions(positions, side_state, _restrict_to_codes(effect.target))


def _restrict_to_codes(target: str) -> bool:
    return target.startswith("friendly_codes_") or target == "all_friendly_codes"


def _filter_positions(
    positions: frozenset[str],
    side_state: SideState,
    only_codes: bool,
) -> set[str]:
    if not only_codes:
        return set(positions)
    out: set[str] = set()
    for pos in positions:
        cell = side_state.grid.cells.get(pos)
        if isinstance(cell, CodeDef):
            out.add(pos)
    return out
