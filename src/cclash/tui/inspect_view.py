"""Plain-text inspect rendering for card definitions.

Layout follows ``docs/inspect_mode.md §4`` closely enough for the M3
inspect CLI to be useful on its own; richer TUI concerns (grid view,
incoming effects, run preview) come later via ``rich`` / textual.

The frame is portrait by default: a fixed inner width with rules text
wrapped at word boundaries. Stats and ASCII art are not wrapped — if a
stat label or art line is wider than the default, the frame expands so
the content stays intact.
"""

from __future__ import annotations

from cclash.cards.models import CardDef, CodeDef, EventDef, ItemDef

DEFAULT_WIDTH = 28


def render_card(card: CardDef, width: int = DEFAULT_WIDTH) -> str:
    stat_lines = [f"{k}: {v}" for k, v in _stat_rows(card)]
    ascii_lines = list(card.ascii)
    title = f"-- {card.name} "

    inner_width = max(
        width,
        len(title) + 1,
        max((len(s) for s in stat_lines), default=0),
        max((len(s) for s in ascii_lines), default=0),
    )
    text_width = inner_width - 2

    body: list[str] = []
    body.extend(stat_lines)
    body.append("")
    body.extend(ascii_lines)
    body.append("")
    for line in card.text:
        body.extend(_wrap(line, text_width))

    out = ["+" + title + "-" * (inner_width - len(title)) + "+"]
    for line in body:
        out.append("| " + line.ljust(inner_width - 2) + " |")
    out.append("+" + "-" * inner_width + "+")
    return "\n".join(out)


def _stat_rows(card: CardDef) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = [
        ("Number", card.number),
        ("Type", card.type.title()),
    ]
    if isinstance(card, CodeDef):
        rows.append(("Faction", card.faction))
        rows.append(("Rarity", card.rarity.title()))
        rows.append(("Pattern", card.pattern))
        rows.append(("OUT", str(card.out)))
        rows.append(("STAB", str(card.stab)))
    elif isinstance(card, ItemDef):
        rows.append(("Family", card.family))
        rows.append(("Rarity", card.rarity.title()))
        rows.append(("Pattern", card.pattern))
        rows.append(("Uses", str(card.uses)))
    elif isinstance(card, EventDef):
        rows.append(("Rarity", card.rarity.title()))
        rows.append(("Move", card.move))
        rows.append(("Pattern", card.pattern))
    return rows


def _wrap(text: str, width: int) -> list[str]:
    """Greedy word-wrap. A single word longer than ``width`` is kept
    on its own line; callers should pick a width that fits realistic
    rules text rather than relying on hard truncation."""
    if not text:
        return [""]
    out: list[str] = []
    line = ""
    for word in text.split():
        if not line:
            line = word
        elif len(line) + 1 + len(word) <= width:
            line = f"{line} {word}"
        else:
            out.append(line)
            line = word
    if line:
        out.append(line)
    return out
