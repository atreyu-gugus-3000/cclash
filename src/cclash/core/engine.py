"""M5 run engine for cclash.

Compiles a 3x3 grid from card placements, runs three cycles in the
fixed order (rules §5):

    Item Effects → Code Execution → Damage / Disable → Output Scoring

and returns a :class:`MatchResult` with a readable ``RunLog``. Training
mode (see ``cclash.game.training``) is solo — opponent grid is empty,
so mirror damage from friendly Codes lands in vacant enemy slots and
contributes only to the log, not to disable state.

Reconfigure (Event firing) is *intentionally* out of scope for M5: the
two Event slots are reserved by ``compile_grid`` so the loadout stays
legal, but their grid-mutating effects are not interpreted yet — they
return with ``rollback`` semantics in a follow-up milestone.

Persistent state across runs: cumulative ``damage_taken`` per slot and
the set of ``disabled`` slots. Per-run ``SlotState`` accumulators are
reset at the start of each cycle. Determinism is inherited from the
effect interpreter and Grid; nothing in the engine reads time or RNG.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from cclash.cards.models import CardDef, CodeDef, EventDef, ItemDef
from cclash.core.effects import (
    EffectSpec,
    MatchContext,
    Side,
    SideState,
    SlotState,
    affected_targets,
    apply_effect,
)
from cclash.core.grid import POSITIONS, Grid

_LOADOUT = {"code": 3, "item": 4, "event": 2}


class CompileError(ValueError):
    """Raised when a compiled grid does not satisfy the §2 loadout."""


@dataclass(frozen=True)
class GridSpec:
    """A compiled 3x3 grid: every position holds exactly one CardDef."""

    cells: dict[str, CardDef]

    def codes(self) -> list[tuple[str, CodeDef]]:
        return [(p, c) for p in POSITIONS if isinstance((c := self.cells[p]), CodeDef)]

    def items(self) -> list[tuple[str, ItemDef]]:
        return [(p, c) for p in POSITIONS if isinstance((c := self.cells[p]), ItemDef)]

    def events(self) -> list[tuple[str, EventDef]]:
        return [(p, c) for p in POSITIONS if isinstance((c := self.cells[p]), EventDef)]


def compile_grid(cells: dict[str, CardDef]) -> GridSpec:
    """Validate a placement against §2 loadout (3 Codes / 4 Items / 2 Events)."""
    if set(cells.keys()) != set(POSITIONS):
        missing = sorted(set(POSITIONS) - set(cells.keys()))
        extra = sorted(set(cells.keys()) - set(POSITIONS))
        raise CompileError(
            f"grid must fill exactly the 9 positions; missing={missing}, extra={extra}"
        )
    counts = {"code": 0, "item": 0, "event": 0}
    for c in cells.values():
        counts[c.type] += 1
    if counts != _LOADOUT:
        raise CompileError(
            f"grid loadout must be 3 codes / 4 items / 2 events; got "
            f"{counts['code']}/{counts['item']}/{counts['event']}"
        )
    return GridSpec(cells=dict(cells))


@dataclass
class CodeOutput:
    pos: str
    name: str
    base_out: int
    delta: int
    final_out: int


@dataclass
class DamageEntry:
    side: Side
    pos: str
    incoming: int
    prevented: int
    net: int


@dataclass
class RunResult:
    index: int
    item_phase: list[str] = field(default_factory=list)
    code_execution: list[str] = field(default_factory=list)
    damage: list[DamageEntry] = field(default_factory=list)
    outputs: list[CodeOutput] = field(default_factory=list)
    disabled_after_run: list[str] = field(default_factory=list)
    total_output: int = 0


@dataclass
class MatchResult:
    runs: list[RunResult]
    total_output: int
    log: str


@dataclass
class _PersistentSide:
    damage_taken: dict[str, int] = field(default_factory=lambda: {p: 0 for p in POSITIONS})
    disabled: set[str] = field(default_factory=set)


def play_match(
    player: GridSpec,
    opponent: GridSpec | None = None,
    num_runs: int = 3,
) -> MatchResult:
    """Run a match end-to-end and produce a :class:`MatchResult`.

    ``opponent=None`` is training mode; mirror damage lands in vacant
    enemy slots and is logged but does not change scoring.
    """
    ctx = _new_context(player, opponent)
    pf = _PersistentSide()
    pe = _PersistentSide()
    runs: list[RunResult] = []
    log_lines: list[str] = []
    for i in range(1, num_runs + 1):
        _reset_run_deltas(ctx)
        result = _run_cycle(player, ctx, pf, pe, run_index=i)
        runs.append(result)
        log_lines.extend(_format_run(result))
        log_lines.append("")
    total = sum(r.total_output for r in runs)
    log_lines.append(f"Final: {total} Output across {num_runs} runs")
    return MatchResult(runs=runs, total_output=total, log="\n".join(log_lines).rstrip())


def _new_context(player: GridSpec, opponent: GridSpec | None) -> MatchContext:
    friendly = SideState(grid=_grid_from_spec(player))
    enemy_grid = _grid_from_spec(opponent) if opponent is not None else _empty_grid()
    return MatchContext(friendly=friendly, enemy=SideState(grid=enemy_grid))


def _grid_from_spec(spec: GridSpec) -> Grid:
    rows = [[spec.cells[f"{r}{c}"] for c in ("1", "2", "3")] for r in ("A", "B", "C")]
    return Grid.from_rows(rows)


def _empty_grid() -> Grid:
    return Grid.from_rows([[None, None, None] for _ in range(3)])


def _reset_run_deltas(ctx: MatchContext) -> None:
    for pos in POSITIONS:
        ctx.friendly.slots[pos] = SlotState()
        ctx.enemy.slots[pos] = SlotState()


def _run_cycle(
    player: GridSpec,
    ctx: MatchContext,
    pf: _PersistentSide,
    pe: _PersistentSide,
    *,
    run_index: int,
) -> RunResult:
    result = RunResult(index=run_index)

    _fire_phase(
        player.items(), trigger="item_phase", ctx=ctx, log=result.item_phase, disabled=pf.disabled
    )
    _fire_phase(
        player.codes(),
        trigger="code_execution",
        ctx=ctx,
        log=result.code_execution,
        disabled=pf.disabled,
    )

    for pos in POSITIONS:
        for side_label, side_state, persistent in (
            ("friendly", ctx.friendly, pf),
            ("enemy", ctx.enemy, pe),
        ):
            slot = side_state.slots[pos]
            net = max(0, slot.incoming_damage - slot.prevented_damage)
            if slot.incoming_damage == 0 and slot.prevented_damage == 0:
                continue
            persistent.damage_taken[pos] += net
            result.damage.append(
                DamageEntry(
                    side=side_label,
                    pos=pos,
                    incoming=slot.incoming_damage,
                    prevented=slot.prevented_damage,
                    net=net,
                )
            )

    for pos, code in player.codes():
        if pos in pf.disabled:
            continue
        threshold = code.stab + ctx.friendly.slots[pos].stab_delta
        if pf.damage_taken[pos] >= threshold:
            pf.disabled.add(pos)
            result.disabled_after_run.append(pos)

    for pos, code in player.codes():
        if pos in pf.disabled:
            continue
        delta = ctx.friendly.slots[pos].out_delta
        final = max(0, code.out + delta)
        result.outputs.append(
            CodeOutput(pos=pos, name=code.name, base_out=code.out, delta=delta, final_out=final)
        )
    result.total_output = sum(o.final_out for o in result.outputs)
    return result


def _fire_phase(
    cards: Iterable[tuple[str, CardDef]],
    *,
    trigger: str,
    ctx: MatchContext,
    log: list[str],
    disabled: set[str],
) -> None:
    for pos, card in cards:
        if pos in disabled:
            continue
        any_fired = False
        for effect in card.effects:
            if effect.trigger != trigger:
                continue
            any_fired = True
            log.extend(_describe_effect(card, pos, effect, ctx))
            apply_effect(effect, pos, ctx)
        if not any_fired and isinstance(card, CodeDef) and trigger == "code_execution":
            log.append(f"{card.name} at {pos} produces base Output")


def _describe_effect(
    card: CardDef,
    pos: str,
    effect: EffectSpec,
    ctx: MatchContext,
) -> list[str]:
    side, targets = affected_targets(effect, pos, ctx)
    if not targets:
        return [f"{card.name} at {pos}: {effect.type} {effect.amount} (no valid targets)"]
    lines: list[str] = []
    side_state = ctx.friendly if side == "friendly" else ctx.enemy
    for target_pos in sorted(targets):
        cell = side_state.grid.cells.get(target_pos)
        target_label = cell.name if isinstance(cell, CardDef) else f"{side} {target_pos}"
        lines.append(_format_effect_line(card.name, pos, effect, target_label, side, target_pos))
    return lines


def _format_effect_line(
    source_name: str,
    source_pos: str,
    effect: EffectSpec,
    target_label: str,
    side: Side,
    target_pos: str,
) -> str:
    sign = "+" if effect.amount >= 0 else ""
    if effect.type == "modify_out":
        return f"{source_name} at {source_pos} buffs {target_label} ({target_pos}), {sign}{effect.amount} OUT"
    if effect.type == "modify_stab":
        return f"{source_name} at {source_pos} buffs {target_label} ({target_pos}), {sign}{effect.amount} STAB"
    if effect.type == "damage":
        return f"{source_name} at {source_pos} hits {side} {target_pos} for {effect.amount} damage"
    if effect.type == "prevent_damage":
        return f"{source_name} at {source_pos} shields {target_label} ({target_pos}) for {effect.amount}"
    return f"{source_name} at {source_pos}: {effect.type} {effect.amount} on {side} {target_pos}"


def _format_run(result: RunResult) -> list[str]:
    lines = [f"Run {result.index}", ""]
    lines.append("Item Effects:" if result.item_phase else "Item Effects: (none)")
    for line in result.item_phase:
        lines.append(f"- {line}")
    lines.append("")
    lines.append("Code Execution:")
    for line in result.code_execution:
        lines.append(f"- {line}")
    if result.damage:
        lines.append("")
        lines.append("Damage:")
        for d in result.damage:
            lines.append(
                f"- {d.side} {d.pos}: {d.incoming} dmg, {d.prevented} prevented, net {d.net}"
            )
    if result.disabled_after_run:
        lines.append("")
        lines.append(f"Disabled: {', '.join(result.disabled_after_run)}")
    lines.append("")
    lines.append("Output Scoring:")
    for o in result.outputs:
        lines.append(f"- {o.name} at {o.pos}: {o.base_out} base + {o.delta} delta = {o.final_out}")
    lines.append(f"Run {result.index} total: {result.total_output} Output")
    return lines
