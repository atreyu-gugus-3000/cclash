"""Dice utilities for cclash.

Use one RNG object per game/match so rolls can be reproducible in tests
and inspectable in logs.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Dice:
    """Small deterministic dice roller.

    In normal play, instantiate without a seed.
    In tests or replay/debug mode, pass a seed.
    """

    seed: int | None = None
    rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)

    def d6(self) -> int:
        """Roll one six-sided die, returning 1..6 inclusive."""
        return self.rng.randint(1, 6)

    def roll(self, sides: int) -> int:
        """Roll one die with `sides` sides, returning 1..sides inclusive."""
        if sides < 2:
            raise ValueError("dice must have at least 2 sides")
        return self.rng.randint(1, sides)
