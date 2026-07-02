"""M5 run engine for cclash.

Compiles a 3x3 grid from card placements and plays a match in the
training shape (rules §8): Run 1 → Reconfigure → Run 2 → Reconfigure →
Run 3. Each Run resolves in the fixed order (rules §5):

    Item Effects → Code Execution → before_damage → Damage / Disable
    → Output Scoring → end_of_run

``before_damage`` and ``end_of_run`` fire the corresponding effect
triggers; damage accumulated in the end_of_run phase is resolved after
scoring ("lose 1 STAB after the Run") and can disable a Code before the
next Run starts.

Grid cells hold :class:`RuntimeCard` wrappers so persistent state
(``damage_taken``, ``disabled``) travels with the card when Events
reconfigure the grid — STAB belongs to the Code, not to the slot it
happens to occupy. Card *definitions* stay immutable.

Reconfigure: between Runs a player may play one Event or pass. Playing
an Event consumes it — its slot empties first, then the Event's move
applies to the grid (rules §3: "Events are consumed after use").
Decisions come from a ``reconfigure`` callback so the CLI can prompt
interactively while tests replay scripted plans.

Randomness: one W6 stream per match, seeded via the ``seed`` parameter
(randomness_v0_1.md §4). Rolls happen only for effects with a ``roll``
clause, in deterministic position order, and every roll is logged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from cclash.cards.models import CardDef, CodeDef, EventDef, ItemDef
from cclash.core.dice import Dice
from cclash.core.effects import (
    EffectSpec,
    MatchContext,
    Side,
    SideState,
    SlotState,
    affected_targets,
    apply_effect,
    condition_holds,
)
from cclash.core.grid import POSITIONS, Grid

_LOADOUT = {"code": 3, "item": 4, "event": 2}


class CompileError(ValueError):
    """Raised when a compiled grid does not satisfy the §2 loadout."""


class ReconfigureError(ValueError):
    """Raised when a Reconfigure decision is invalid (host-authoritative:
    bad intentions are rejected, never silently corrected)."""


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


@dataclass(eq=False)
class RuntimeCard:
    """A card definition placed in a live grid, plus its match state.

    Identity semantics (``eq=False``): two copies of the same definition
    are distinct pieces on the board.
    """

    card: CardDef
    damage_taken: int = 0
    disabled: bool = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self.card, name)


@dataclass(frozen=True)
class EventPlay:
    """Reconfigure decision: play the Event currently at ``event_pos``."""

    event_pos: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReconfigureView:
    """Read-only snapshot handed to the reconfigure callback.

    ``last_run_log`` holds the formatted log lines of the run that just
    finished, so an interactive player can read them before deciding.
    """

    phase: int
    cells: dict[str, CardDef | None]
    events: dict[str, EventDef]
    total_output: int
    last_run_log: tuple[str, ...] = ()


ReconfigureFn = Callable[[ReconfigureView], EventPlay | None]


def scripted_reconfigure(decisions: list[EventPlay | None]) -> ReconfigureFn:
    """Replay a fixed list of decisions, one per reconfigure phase."""
    seq = list(decisions)

    def decide(view: ReconfigureView) -> EventPlay | None:
        i = view.phase - 1
        return seq[i] if i < len(seq) else None

    return decide


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
    end_of_run: list[str] = field(default_factory=list)
    disabled_after_run: list[str] = field(default_factory=list)
    total_output: int = 0


@dataclass
class MatchResult:
    runs: list[RunResult]
    total_output: int
    log: str
    seed: int = 0
    reconfigures: list[str] = field(default_factory=list)
    final_cells: dict[str, CardDef | None] = field(default_factory=dict)


def play_match(
    player: GridSpec,
    opponent: GridSpec | None = None,
    num_runs: int = 3,
    *,
    seed: int = 0,
    reconfigure: ReconfigureFn | None = None,
) -> MatchResult:
    """Play a match end-to-end and produce a :class:`MatchResult`.

    ``opponent=None`` is training mode; mirror damage lands in vacant
    enemy slots and is logged but does not change scoring.
    ``reconfigure=None`` passes every reconfigure phase.
    """
    dice = Dice(seed=seed)
    ctx = _new_context(player, opponent)
    runs: list[RunResult] = []
    log_lines: list[str] = []
    reconfig_lines: list[str] = []
    for i in range(1, num_runs + 1):
        _reset_run_deltas(ctx)
        result = _run_cycle(ctx, dice, run_index=i)
        runs.append(result)
        log_lines.extend(_format_run(result))
        log_lines.append("")
        if i < num_runs:
            line = _reconfigure_phase(
                ctx,
                reconfigure,
                phase=i,
                total_so_far=_total(runs),
                last_run_log=tuple(_format_run(result)),
            )
            reconfig_lines.append(line)
            log_lines.extend([line, ""])
    total = _total(runs)
    log_lines.append(f"Final: {total} Output across {num_runs} runs")
    return MatchResult(
        runs=runs,
        total_output=total,
        log="\n".join(log_lines).rstrip(),
        seed=seed,
        reconfigures=reconfig_lines,
        final_cells={p: (rc.card if rc is not None else None) for p, rc in _cells(ctx).items()},
    )


def _total(runs: list[RunResult]) -> int:
    return sum(r.total_output for r in runs)


def _new_context(player: GridSpec, opponent: GridSpec | None) -> MatchContext:
    friendly = SideState(grid=_runtime_grid(player))
    enemy_grid = _runtime_grid(opponent) if opponent is not None else _empty_grid()
    return MatchContext(friendly=friendly, enemy=SideState(grid=enemy_grid))


def _runtime_grid(spec: GridSpec) -> Grid:
    rows = [
        [RuntimeCard(card=spec.cells[f"{r}{c}"]) for c in ("1", "2", "3")] for r in ("A", "B", "C")
    ]
    return Grid.from_rows(rows)


def _empty_grid() -> Grid:
    return Grid.from_rows([[None, None, None] for _ in range(3)])


def _cells(ctx: MatchContext) -> dict[str, RuntimeCard | None]:
    return ctx.friendly.grid.cells


def _cards_of_type(ctx: MatchContext, card_type: str) -> list[tuple[str, RuntimeCard]]:
    return [
        (p, rc) for p in POSITIONS if (rc := _cells(ctx)[p]) is not None and rc.type == card_type
    ]


def _reset_run_deltas(ctx: MatchContext) -> None:
    for pos in POSITIONS:
        ctx.friendly.slots[pos] = SlotState()
        ctx.enemy.slots[pos] = SlotState()


def _run_cycle(ctx: MatchContext, dice: Dice, *, run_index: int) -> RunResult:
    result = RunResult(index=run_index)

    _fire_phase(
        _cards_of_type(ctx, "item"), trigger="item_phase", ctx=ctx, dice=dice, log=result.item_phase
    )
    _fire_phase(
        _cards_of_type(ctx, "code"),
        trigger="code_execution",
        ctx=ctx,
        dice=dice,
        log=result.code_execution,
    )
    _fire_phase(
        _cards_of_type(ctx, "item") + _cards_of_type(ctx, "code"),
        trigger="before_damage",
        ctx=ctx,
        dice=dice,
        log=result.code_execution,
    )

    _resolve_damage(ctx, result)
    _check_disable(ctx, result)

    for pos, rc in _cards_of_type(ctx, "code"):
        if rc.disabled:
            continue
        delta = ctx.friendly.slots[pos].out_delta
        final = max(0, rc.out + delta)
        result.outputs.append(
            CodeOutput(pos=pos, name=rc.name, base_out=rc.out, delta=delta, final_out=final)
        )
    result.total_output = sum(o.final_out for o in result.outputs)

    _fire_phase(
        _cards_of_type(ctx, "item") + _cards_of_type(ctx, "code"),
        trigger="end_of_run",
        ctx=ctx,
        dice=dice,
        log=result.end_of_run,
    )
    _resolve_damage(ctx, result)
    _check_disable(ctx, result)
    return result


def _resolve_damage(ctx: MatchContext, result: RunResult) -> None:
    """Apply accumulated incoming/prevented damage, then reset the
    accumulators so a later phase in the same run only sees its own."""
    for pos in POSITIONS:
        for side_label, side_state in (("friendly", ctx.friendly), ("enemy", ctx.enemy)):
            slot = side_state.slots[pos]
            if slot.incoming_damage == 0 and slot.prevented_damage == 0:
                continue
            net = max(0, slot.incoming_damage - slot.prevented_damage)
            rc = side_state.grid.cells.get(pos)
            if rc is not None:
                rc.damage_taken += net
            result.damage.append(
                DamageEntry(
                    side=side_label,
                    pos=pos,
                    incoming=slot.incoming_damage,
                    prevented=slot.prevented_damage,
                    net=net,
                )
            )
            slot.incoming_damage = 0
            slot.prevented_damage = 0


def _check_disable(ctx: MatchContext, result: RunResult) -> None:
    for pos, rc in _cards_of_type(ctx, "code"):
        if rc.disabled:
            continue
        threshold = rc.stab + ctx.friendly.slots[pos].stab_delta
        if rc.damage_taken >= threshold:
            rc.disabled = True
            result.disabled_after_run.append(pos)


def _reconfigure_phase(
    ctx: MatchContext,
    decide: ReconfigureFn | None,
    *,
    phase: int,
    total_so_far: int,
    last_run_log: tuple[str, ...] = (),
) -> str:
    view = ReconfigureView(
        phase=phase,
        cells={p: (rc.card if rc is not None else None) for p, rc in _cells(ctx).items()},
        events={p: rc.card for p, rc in _cards_of_type(ctx, "event")},
        total_output=total_so_far,
        last_run_log=last_run_log,
    )
    decision = decide(view) if decide is not None else None
    if decision is None:
        return f"Reconfigure {phase}: pass"

    pos = decision.event_pos
    rc = _cells(ctx).get(pos)
    if rc is None or rc.type != "event":
        raise ReconfigureError(f"no playable Event at {pos}")
    event: EventDef = rc.card
    # Consume first — the slot empties, then the move applies (rules §3).
    _cells(ctx)[pos] = None
    _apply_move(ctx.friendly.grid, event.move, decision.params)
    params = f" {decision.params}" if decision.params else ""
    return f"Reconfigure {phase}: play {event.name} at {pos} -> {event.move}{params}"


def _apply_move(grid: Grid, move: str, params: dict[str, Any]) -> None:
    try:
        if move == "rotate90":
            grid.rotate90()
        elif move == "rotate90ccw":
            grid.rotate90ccw()
        elif move == "shift_row":
            grid.shift_row(str(params["source"]), str(params["target"]))
        elif move == "shift_column":
            grid.shift_column(str(params["source"]), str(params["target"]))
        elif move == "outer_ring_rotate":
            grid.outer_ring_rotate(1)
        elif move == "swap_adjacent":
            grid.swap_adjacent(str(params["a"]), str(params["b"]))
        elif move == "rollback":
            grid.rollback()
        else:
            raise ReconfigureError(f"unknown move: {move!r}")
    except KeyError as e:
        raise ReconfigureError(f"move {move!r} missing parameter {e.args[0]!r}") from e
    except ValueError as e:
        raise ReconfigureError(f"move {move!r} rejected: {e}") from e


def _fire_phase(
    cards: list[tuple[str, RuntimeCard]],
    *,
    trigger: str,
    ctx: MatchContext,
    dice: Dice,
    log: list[str],
) -> None:
    for pos, rc in cards:
        if rc.type == "code" and rc.disabled:
            continue
        any_fired = False
        for effect in rc.effects:
            if effect.trigger != trigger:
                continue
            if effect.condition is not None and not condition_holds(effect.condition, pos, ctx):
                continue
            if effect.roll is not None:
                face = dice.d6()
                log.append(f"{rc.name} at {pos}: roll W6 -> {face}")
                if face not in effect.roll:
                    log.append(f"  -> no effect (fires on {', '.join(map(str, effect.roll))})")
                    continue
                log.append(f"  -> {effect.type} {effect.amount} applied")
            else:
                log.extend(_describe_effect(rc, pos, effect, ctx))
            any_fired = True
            apply_effect(effect, pos, ctx)
        if not any_fired and rc.type == "code" and trigger == "code_execution":
            log.append(f"{rc.name} at {pos} produces base Output")


def _describe_effect(
    rc: RuntimeCard,
    pos: str,
    effect: EffectSpec,
    ctx: MatchContext,
) -> list[str]:
    side, targets = affected_targets(effect, pos, ctx)
    if not targets:
        return [f"{rc.name} at {pos}: {effect.type} {effect.amount} (no valid targets)"]
    lines: list[str] = []
    side_state = ctx.friendly if side == "friendly" else ctx.enemy
    for target_pos in sorted(targets):
        cell = side_state.grid.cells.get(target_pos)
        target_label = getattr(cell, "name", None) or f"{side} {target_pos}"
        lines.append(_format_effect_line(rc.name, pos, effect, target_label, side, target_pos))
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
    if result.end_of_run:
        lines.append("")
        lines.append("End of Run:")
        for line in result.end_of_run:
            lines.append(f"- {line}")
    if result.disabled_after_run:
        lines.append("")
        lines.append(f"Disabled: {', '.join(result.disabled_after_run)}")
    lines.append("")
    lines.append("Output Scoring:")
    for o in result.outputs:
        lines.append(f"- {o.name} at {o.pos}: {o.base_out} base + {o.delta} delta = {o.final_out}")
    lines.append(f"Run {result.index} total: {result.total_output} Output")
    return lines
