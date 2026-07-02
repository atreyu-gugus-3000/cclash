"""Solo training mode wrapper around the M5 run engine.

Training is the simplest match shape: one player, no opponent, three
runs with a Reconfigure phase between them (rules §8), score = total
Output. ``play_training`` is a thin convenience over
:func:`cclash.core.engine.play_match`.

Seeding follows randomness_v0_1.md §4: one W6 stream per match, seeded
from the participants, the match id and the cardset. Training has no
client player, so the client slot is fixed to the literal string
``"training"``.

``sample_grid`` builds a deterministic 9-card placement out of the
``alpha_001`` set so ``cclash training --sample`` can produce a
reproducible RunLog without needing user input — both for documentation
and for the CLI smoke test.
"""

from __future__ import annotations

import hashlib

from cclash.cards.models import CardDef, CardSet
from cclash.core.engine import (
    EventPlay,
    GridSpec,
    MatchResult,
    ReconfigureFn,
    ReconfigureView,
    compile_grid,
    play_match,
)
from cclash.core.grid import POSITIONS

# Moves that need no parameters and can therefore be auto-played.
_PARAMLESS_MOVES = frozenset({"rotate90", "rotate90ccw", "outer_ring_rotate", "rollback"})


def play_training(
    player: GridSpec,
    num_runs: int = 3,
    *,
    seed: int = 0,
    reconfigure: ReconfigureFn | None = None,
) -> MatchResult:
    return play_match(player, opponent=None, num_runs=num_runs, seed=seed, reconfigure=reconfigure)


def cardset_hash(cardset: CardSet) -> str:
    """Stable content hash of a card set (used in match seeds).

    Hashes every definition field that affects the engine, in number
    order, so two players with byte-identical cardsets agree on the
    seed while any balance change produces a new stream.
    """
    h = hashlib.sha256()
    h.update(f"{cardset.meta.id}|{cardset.meta.version}".encode())
    for card in sorted(cardset.all_cards(), key=lambda c: c.number):
        h.update(repr((card.number, card.id, card.type, card.pattern, card.effects)).encode())
        for attr in ("out", "stab", "faction", "uses", "family", "move"):
            h.update(repr(getattr(card, attr, None)).encode())
    return h.hexdigest()


def training_seed(player_id: str, match_id: str, cardset: CardSet) -> int:
    """Derive the match seed for a solo training run (randomness §4)."""
    key = f"{player_id}|training|{match_id}|{cardset_hash(cardset)}"
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")


def auto_reconfigure(view: ReconfigureView) -> EventPlay | None:
    """Play the first remaining Event in position order, if its move
    needs no parameters; otherwise pass. Deterministic, used for
    ``--sample`` and ``--auto`` runs."""
    for pos in POSITIONS:
        event = view.events.get(pos)
        if event is None:
            continue
        if event.move in _PARAMLESS_MOVES:
            return EventPlay(event_pos=pos)
        return None
    return None


_SAMPLE_LAYOUT: tuple[tuple[str, str], ...] = (
    ("A1", "cronling"),
    ("A2", "docker"),
    ("A3", "patch_goblin"),
    ("B1", "tmux"),
    ("B2", "vibe_bug"),
    ("B3", "overclock_chip"),
    ("C1", "rotate90"),
    ("C2", "firewall_cloak"),
    ("C3", "outer_ring"),
)


def sample_grid(cardset: CardSet) -> GridSpec:
    """Build the canonical demo grid from a loaded ``alpha_001`` set.

    Layout: 3 Codes (Cronling A1, Patch Goblin A3, Vibe Bug B2),
    4 Items (Docker A2, Tmux B1, Overclock B3, Firewall C2),
    2 Events (Rotate90 C1, Outer Ring C3).
    """
    by_id: dict[str, CardDef] = {c.id: c for c in cardset.all_cards()}
    cells: dict[str, CardDef] = {}
    for pos, card_id in _SAMPLE_LAYOUT:
        if card_id not in by_id:
            raise KeyError(f"sample grid expects card id {card_id!r} in the set")
        cells[pos] = by_id[card_id]
    return compile_grid(cells)


def play_sample(cardset: CardSet) -> MatchResult:
    """The canonical deterministic demo match: sample grid, derived
    seed, Events auto-played."""
    grid = sample_grid(cardset)
    seed = training_seed("local", "sample", cardset)
    return play_training(grid, seed=seed, reconfigure=auto_reconfigure)
