"""Solo training mode wrapper around the M5 run engine.

Training is the simplest match shape: one player, no opponent, three
runs, score = total Output. ``play_training`` is a thin convenience
over :func:`cclash.core.engine.play_match` that fixes the opponent to
``None`` and locks the run count to three.

``sample_grid`` builds a deterministic 9-card placement out of the
``alpha_001`` set so ``cclash training --sample`` can produce a
reproducible RunLog without needing user input — both for documentation
and for the CLI smoke test.
"""

from __future__ import annotations

from cclash.cards.models import CardDef, CardSet
from cclash.core.engine import GridSpec, MatchResult, compile_grid, play_match


def play_training(player: GridSpec, num_runs: int = 3) -> MatchResult:
    return play_match(player, opponent=None, num_runs=num_runs)


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
    """Build the canonical M5-DoD demo grid from a loaded ``alpha_001`` set.

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
