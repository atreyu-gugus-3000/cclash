"""Tests for the portrait inspect renderer."""

from __future__ import annotations

from pathlib import Path

from cclash.cards.loader import load_set
from cclash.tui.inspect_view import DEFAULT_WIDTH, render_card

ALPHA_DIR = Path(__file__).resolve().parents[1] / "cardsets" / "alpha_001"


def _frame_widths(rendered: str) -> set[int]:
    return {len(line) for line in rendered.splitlines()}


def test_rendered_frame_is_rectangular():
    cardset = load_set(ALPHA_DIR)
    for card in cardset.all_cards():
        rendered = render_card(card)
        widths = _frame_widths(rendered)
        assert len(widths) == 1, f"{card.id}: ragged frame {widths}"


def test_default_width_is_portrait_for_typical_card():
    cardset = load_set(ALPHA_DIR)
    cron = next(c for c in cardset.codes if c.id == "cronling")
    rendered = render_card(cron)
    width = next(iter(_frame_widths(rendered)))
    assert width == DEFAULT_WIDTH + 2


def test_long_text_wraps_within_frame():
    cardset = load_set(ALPHA_DIR)
    cron = next(c for c in cardset.codes if c.id == "cronling")
    rendered = render_card(cron)
    for line in rendered.splitlines():
        assert len(line) <= DEFAULT_WIDTH + 2


def test_wide_ascii_expands_frame_but_text_still_wraps():
    cardset = load_set(ALPHA_DIR)
    vibe = next(c for c in cardset.codes if c.id == "vibe_bug")
    rendered = render_card(vibe)
    width = next(iter(_frame_widths(rendered)))
    assert width >= DEFAULT_WIDTH + 2

    long_line = "If an Event is diagonal to this Code, this Code gets +2 OUT."
    assert long_line not in rendered
