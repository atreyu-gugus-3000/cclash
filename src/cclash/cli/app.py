"""CLI entrypoint for cclash.

Subcommands:

- ``cclash``                   — version banner
- ``cclash cards list``        — list every card across registered sets
- ``cclash inspect <key>``     — show one card by number (``CC-A001-007``)
                                  or by id (``docker``)
- ``cclash compile``           — build a 3x3 grid (interactive, or via
                                  ``--place A1=cronling ...``) and save it
- ``cclash training``          — play a solo training match on the saved
                                  grid; Events are played interactively,
                                  or automatically with ``--auto``.
                                  ``--sample`` plays the canonical demo.
- ``cclash log``               — show past training results and the highscore

The ``cardsets/`` directory is auto-discovered by walking up from the
current working directory and from this file's location. Override with
``--cardsets <path>`` if auto-detection picks the wrong tree (e.g. when
running from outside the repo).

The engine itself is deterministic; the only nondeterminism lives here
(default ``match_id`` from the wall clock, interactive decisions). Both
are recorded in the run log, so any match can be replayed exactly.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from cclash import __version__
from cclash.cards.loader import load_set
from cclash.cards.models import CardDef
from cclash.cards.registry import Registry
from cclash.core.engine import (
    CompileError,
    EventPlay,
    ReconfigureError,
    ReconfigureView,
    compile_grid,
)
from cclash.core.grid import COLS, POSITIONS, ROWS
from cclash.game.training import auto_reconfigure, play_sample, play_training, training_seed
from cclash.storage.runlog import (
    append_entry,
    default_grid_path,
    default_log_path,
    highscore,
    read_entries,
)
from cclash.tui.inspect_view import render_card


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        _print_banner()
        return 0

    if args.command == "log":
        return _cmd_log(args.log_file or default_log_path(), limit=args.limit)

    cardsets_dir = args.cardsets or _find_cardsets_dir()
    if cardsets_dir is None:
        parser.error("could not find cardsets/ directory; pass --cardsets <path>")
    registry = _build_registry(cardsets_dir)

    if args.command == "cards":
        if args.cards_command == "list":
            return _cmd_cards_list(registry)
        parser.parse_args(["cards", "--help"])
        return 2

    if args.command == "inspect":
        return _cmd_inspect(registry, args.key)

    if args.command == "compile":
        return _cmd_compile(registry, places=args.place, out=args.out or default_grid_path())

    if args.command == "training":
        return _cmd_training(registry, args)

    parser.print_help()
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cclash",
        description="cclash, terminal-native grid TCG.",
    )
    parser.add_argument(
        "--cardsets",
        type=Path,
        default=None,
        help="path to cardsets/ directory (auto-detected if omitted)",
    )

    sub = parser.add_subparsers(dest="command")

    cards = sub.add_parser("cards", help="card set commands")
    cards_sub = cards.add_subparsers(dest="cards_command")
    cards_sub.add_parser("list", help="list all cards in registered sets")

    inspect = sub.add_parser("inspect", help="inspect a card by number or id")
    inspect.add_argument("key", help="card number (CC-A001-007) or id (docker)")

    compile_p = sub.add_parser("compile", help="build and save a 3x3 grid")
    compile_p.add_argument(
        "--place",
        action="append",
        metavar="POS=ID",
        help="place a card, e.g. --place A1=cronling (9 required; "
        "omit entirely for interactive compile)",
    )
    compile_p.add_argument(
        "--out", type=Path, default=None, help="grid file (default ~/.cclash/grid.json)"
    )

    training = sub.add_parser("training", help="play a solo training match")
    training.add_argument(
        "--sample",
        action="store_true",
        help="play the canonical alpha_001 sample grid (deterministic demo)",
    )
    training.add_argument(
        "--grid", type=Path, default=None, help="grid file (default ~/.cclash/grid.json)"
    )
    training.add_argument(
        "--match-id",
        default=None,
        help="match id for the seed (default: timestamp; same id + same grid replays identically)",
    )
    training.add_argument(
        "--auto",
        action="store_true",
        help="play Events automatically instead of prompting",
    )
    training.add_argument(
        "--no-save", action="store_true", help="do not append the result to the run log"
    )
    training.add_argument(
        "--log-file", type=Path, default=None, help="run log (default ~/.cclash/training_log.jsonl)"
    )

    log_p = sub.add_parser("log", help="show training results and highscore")
    log_p.add_argument("--limit", type=int, default=10, help="entries to show (default 10)")
    log_p.add_argument(
        "--log-file", type=Path, default=None, help="run log (default ~/.cclash/training_log.jsonl)"
    )

    return parser


def _print_banner() -> None:
    print(f"cclash {__version__}")
    print("Compile once. Reconfigure three times. Highest output wins.")
    print("Try: cclash compile, cclash training, cclash inspect CC-A001-007, cclash log")


def _find_cardsets_dir() -> Path | None:
    starts = [Path.cwd(), Path(__file__).resolve().parent]
    for base in starts:
        for d in (base, *base.parents):
            candidate = d / "cardsets"
            if candidate.is_dir():
                return candidate
    return None


def _build_registry(cardsets_dir: Path) -> Registry:
    registry = Registry()
    for sub in sorted(cardsets_dir.iterdir()):
        if sub.is_dir() and (sub / "set.yaml").is_file():
            registry.register(load_set(sub))
    return registry


def _cmd_cards_list(registry: Registry) -> int:
    for c in sorted(registry, key=lambda c: c.number):
        print(f"{c.number}  {c.type:5s}  {c.rarity:9s}  {c.id:20s}  {c.name}")
    return 0


def _cmd_inspect(registry: Registry, key: str) -> int:
    try:
        card = registry.find(key)
    except KeyError as e:
        print(f"error: {e}")
        return 1
    print(render_card(card))
    return 0


# -- compile ------------------------------------------------------------


def _cmd_compile(registry: Registry, *, places: list[str] | None, out: Path) -> int:
    if places:
        try:
            cells = _cells_from_places(registry, places)
        except ValueError as e:
            print(f"error: {e}")
            return 1
    else:
        if not sys.stdin.isatty():
            print("error: interactive compile needs a terminal; use --place A1=cronling ...")
            return 2
        cells = _interactive_compile(registry)
        if cells is None:
            return 1

    try:
        compile_grid(cells)
    except CompileError as e:
        print(f"error: {e}")
        return 1

    layout = {pos: cells[pos].id for pos in POSITIONS}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"cells": layout}, indent=2, sort_keys=True) + "\n", "utf-8")
    print(_render_cells({p: cells[p] for p in POSITIONS}))
    print(f"Grid saved to {out}")
    return 0


def _cells_from_places(registry: Registry, places: list[str]) -> dict[str, CardDef]:
    cells: dict[str, CardDef] = {}
    for item in places:
        pos, sep, key = item.partition("=")
        pos = pos.strip().upper()
        if not sep or pos not in POSITIONS:
            raise ValueError(f"--place must look like A1=cronling, got {item!r}")
        if pos in cells:
            raise ValueError(f"position {pos} placed twice")
        try:
            cells[pos] = registry.find(key.strip())
        except KeyError as e:
            raise ValueError(str(e)) from e
    if len(cells) != 9:
        raise ValueError(f"need 9 --place arguments, got {len(cells)}")
    _reject_duplicate_cards(cells)
    return cells


def _reject_duplicate_cards(cells: dict[str, CardDef]) -> None:
    seen: set[str] = set()
    for c in cells.values():
        if c.id in seen:
            raise ValueError(f"card {c.id!r} placed more than once (only one copy per grid)")
        seen.add(c.id)


def _interactive_compile(registry: Registry) -> dict[str, CardDef] | None:
    codes = sorted((c for c in registry if c.type == "code"), key=lambda c: c.number)
    items = sorted((c for c in registry if c.type == "item"), key=lambda c: c.number)
    events = sorted((c for c in registry if c.type == "event"), key=lambda c: c.number)

    print("Pick 3 Codes:")
    for i, c in enumerate(codes, 1):
        print(f"  {i}) {c.id:16s} OUT {getattr(c, 'out', '?')}  STAB {getattr(c, 'stab', '?')}")
    chosen_codes = _pick_n(codes, 3)
    if chosen_codes is None:
        return None

    pool: list[CardDef] = chosen_codes + items + events
    print("\nPlace your 9 cards (Codes, all Items, all Events):")
    cells: dict[str, CardDef] = {}
    for pos in POSITIONS:
        remaining = [c for c in pool if c not in cells.values()]
        for i, c in enumerate(remaining, 1):
            print(f"  {i}) {c.type:5s} {c.id}")
        idx = _ask_index(f"{pos}> ", len(remaining))
        if idx is None:
            return None
        cells[pos] = remaining[idx]
    return cells


def _pick_n(cards: list[CardDef], n: int) -> list[CardDef] | None:
    while True:
        raw = input(f"numbers, comma-separated (need {n}) > ").strip()
        try:
            picks = [int(p) for p in raw.replace(" ", "").split(",") if p]
        except ValueError:
            print("numbers only, e.g. 1,3,5")
            continue
        if len(set(picks)) != n or not all(1 <= p <= len(cards) for p in picks):
            print(f"pick exactly {n} distinct numbers between 1 and {len(cards)}")
            continue
        return [cards[p - 1] for p in picks]


def _ask_index(prompt: str, upper: int) -> int | None:
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= upper:
            return int(raw) - 1
        print(f"enter a number between 1 and {upper}")


# -- training -----------------------------------------------------------


def _cmd_training(registry: Registry, args: argparse.Namespace) -> int:
    if not registry.sets:
        print("error: no card sets loaded")
        return 1
    cardset = registry.sets[0]
    log_path = args.log_file or default_log_path()

    if args.sample:
        result = play_sample(cardset)
        match_id = "sample"
        layout = {p: (c.id if c else None) for p, c in result.final_cells.items()}
    else:
        grid_path = args.grid or default_grid_path()
        if not grid_path.is_file():
            print(f"error: no grid at {grid_path}; run `cclash compile` first")
            return 1
        try:
            cells = _load_grid_file(registry, grid_path)
            spec = compile_grid(cells)
        except (ValueError, CompileError) as e:
            print(f"error: {e}")
            return 1
        layout = {p: cells[p].id for p in POSITIONS}
        match_id = args.match_id or datetime.now().strftime("%Y%m%d-%H%M%S")
        seed = training_seed("local", match_id, cardset)
        interactive = sys.stdin.isatty() and not args.auto
        reconfigure = _interactive_reconfigure if interactive else auto_reconfigure
        print(_render_cells({p: cells[p] for p in POSITIONS}))
        print(f"match {match_id}, seed {seed}\n")
        try:
            result = play_training(spec, seed=seed, reconfigure=reconfigure)
        except ReconfigureError as e:
            print(f"error: {e}")
            return 1
        if interactive:
            # runs 1 and 2 were already shown at the reconfigure prompts
            print("\n=== Full RunLog ===")

    print(result.log)

    if args.no_save:
        return 0
    previous = read_entries(log_path)
    best = highscore(previous)
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "match_id": match_id,
        "seed": result.seed,
        "cardset": cardset.meta.id,
        "grid": layout,
        "runs": [r.total_output for r in result.runs],
        "total": result.total_output,
    }
    append_entry(log_path, entry)
    print()
    if best is None or result.total_output > best["total"]:
        print(f"New highscore: {result.total_output} Output!")
    else:
        print(f"Score {result.total_output} — highscore is {best['total']}")
    return 0


def _load_grid_file(registry: Registry, path: Path) -> dict[str, CardDef]:
    try:
        data = json.loads(path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"cannot read grid file {path}: {e}") from e
    raw_cells = data.get("cells")
    if not isinstance(raw_cells, dict):
        raise ValueError(f"grid file {path} has no 'cells' mapping")
    cells: dict[str, CardDef] = {}
    for pos, card_id in raw_cells.items():
        if pos not in POSITIONS:
            raise ValueError(f"grid file has unknown position {pos!r}")
        try:
            cells[pos] = registry.find(str(card_id))
        except KeyError as e:
            raise ValueError(str(e)) from e
    if set(cells) != set(POSITIONS):
        raise ValueError("grid file must fill all 9 positions")
    _reject_duplicate_cards(cells)
    return cells


def _interactive_reconfigure(view: ReconfigureView) -> EventPlay | None:
    print()
    for line in view.last_run_log:
        print(line)
    print()
    print(f"— Reconfigure {view.phase} (score so far: {view.total_output}) —")
    print(_render_cells(view.cells))
    if not view.events:
        print("No Events left, passing.")
        return None
    events = sorted(view.events.items())
    for i, (pos, ev) in enumerate(events, 1):
        print(f"  {i}) {ev.name} at {pos} ({ev.move})")
    while True:
        raw = input("Play Event number, or p to pass > ").strip().lower()
        if raw in ("", "p", "pass"):
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(events):
            pos, ev = events[int(raw) - 1]
            params = _prompt_move_params(ev.move)
            return EventPlay(event_pos=pos, params=params)
        print(f"enter 1..{len(events)} or p")


def _prompt_move_params(move: str) -> dict[str, str]:
    if move == "shift_row":
        return {
            "source": _ask_choice("row to move (A/B/C) > ", ROWS),
            "target": _ask_choice("target row (A/B/C) > ", ROWS),
        }
    if move == "shift_column":
        return {
            "source": _ask_choice("column to move (1/2/3) > ", COLS),
            "target": _ask_choice("target column (1/2/3) > ", COLS),
        }
    if move == "swap_adjacent":
        return {
            "a": _ask_choice("first slot (e.g. A1) > ", POSITIONS),
            "b": _ask_choice("second slot > ", POSITIONS),
        }
    return {}


def _ask_choice(prompt: str, valid: tuple[str, ...]) -> str:
    while True:
        raw = input(prompt).strip().upper()
        if raw in valid:
            return raw
        print(f"one of: {', '.join(valid)}")


def _render_cells(cells: dict[str, CardDef | None]) -> str:
    width = 12
    sep = "+" + "+".join(["-" * width] * 3) + "+"
    lines = [sep]
    for r in ROWS:
        row_cells = []
        for c in COLS:
            card = cells.get(f"{r}{c}")
            label = card.id[: width - 2] if card is not None else ""
            row_cells.append(f" {label:<{width - 1}}")
        lines.append("|" + "|".join(row_cells) + "|")
        lines.append(sep)
    return "\n".join(lines)


# -- log ----------------------------------------------------------------


def _cmd_log(log_path: Path, *, limit: int) -> int:
    entries = read_entries(log_path)
    if not entries:
        print(f"No training runs logged yet ({log_path}).")
        return 0
    best = highscore(entries)
    print(f"{'when':20s} {'match':18s} {'runs':12s} total")
    for e in entries[-limit:]:
        runs = "+".join(str(r) for r in e.get("runs", []))
        marker = "  <- best" if best is not None and e is best else ""
        print(
            f"{e.get('ts', '?'):20s} {str(e.get('match_id', '?')):18s} {runs:12s} "
            f"{e.get('total', '?')}{marker}"
        )
    if best is not None:
        print(f"\nHighscore: {best['total']} Output (match {best.get('match_id', '?')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
