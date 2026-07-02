"""CLI entrypoint for cclash.

Subcommands:

- ``cclash``                  — version banner
- ``cclash cards list``       — list every card across registered sets
- ``cclash inspect <key>``    — show one card by number (``CC-A001-007``)
                                 or by id (``docker``)
- ``cclash training --sample`` — run a deterministic 3-run training match
                                 against the canonical alpha_001 sample grid

The ``cardsets/`` directory is auto-discovered by walking up from the
current working directory and from this file's location. Override with
``--cardsets <path>`` if auto-detection picks the wrong tree (e.g. when
running from outside the repo).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cclash import __version__
from cclash.cards.loader import load_set
from cclash.cards.registry import Registry
from cclash.game.training import play_training, sample_grid
from cclash.tui.inspect_view import render_card


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        _print_banner()
        return 0

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

    if args.command == "training":
        return _cmd_training(registry, sample=args.sample)

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

    training = sub.add_parser("training", help="run a solo training match")
    training.add_argument(
        "--sample",
        action="store_true",
        help="play the canonical alpha_001 sample grid (3 runs, deterministic)",
    )

    return parser


def _print_banner() -> None:
    print(f"cclash {__version__}")
    print("Compile once. Reconfigure three times. Highest output wins.")
    print("MVP engine coming next.")


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


def _cmd_training(registry: Registry, *, sample: bool) -> int:
    if not sample:
        print("error: training currently requires --sample (custom grids land later)")
        return 2
    if not registry.sets:
        print("error: no card sets loaded")
        return 1
    cardset = registry.sets[0]
    grid = sample_grid(cardset)
    result = play_training(grid)
    print(result.log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
