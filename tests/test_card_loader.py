"""Tests for the card YAML loader and Registry."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from cclash.cards.loader import CardSetError, load_set
from cclash.cards.models import CodeDef, EventDef, ItemDef
from cclash.cards.registry import Registry

ALPHA_DIR = Path(__file__).resolve().parents[1] / "cardsets" / "alpha_001"


def test_loads_alpha_001_with_correct_counts():
    cardset = load_set(ALPHA_DIR)
    assert cardset.meta.id == "alpha_001"
    assert cardset.meta.card_count == 12
    assert len(cardset.codes) == 6
    assert len(cardset.items) == 4
    assert len(cardset.events) == 2


def test_alpha_001_first_code_fields():
    cardset = load_set(ALPHA_DIR)
    cron = cardset.codes[0]
    assert isinstance(cron, CodeDef)
    assert cron.number == "CC-A001-001"
    assert cron.id == "cronling"
    assert cron.faction == "coder"
    assert cron.out == 2
    assert cron.stab == 4
    assert cron.pattern == "row"
    assert cron.ascii[0].startswith(" /|__|")


def test_alpha_001_docker_item_fields():
    cardset = load_set(ALPHA_DIR)
    docker = next(c for c in cardset.items if c.id == "docker")
    assert isinstance(docker, ItemDef)
    assert docker.number == "CC-A001-007"
    assert docker.uses == 5
    assert docker.family == "infra"
    assert docker.pattern == "row"


def test_alpha_001_event_fields():
    cardset = load_set(ALPHA_DIR)
    rotate = next(e for e in cardset.events if e.id == "rotate90")
    assert isinstance(rotate, EventDef)
    assert rotate.move == "rotate90"


def test_registry_find_by_number_or_id():
    registry = Registry([load_set(ALPHA_DIR)])
    assert registry.find("CC-A001-007").id == "docker"
    assert registry.find("docker").number == "CC-A001-007"
    assert len(registry) == 12


def test_registry_unknown_key_raises():
    registry = Registry([load_set(ALPHA_DIR)])
    with pytest.raises(KeyError):
        registry.find("not-a-card")


def test_registry_rejects_duplicate_set():
    cardset = load_set(ALPHA_DIR)
    registry = Registry([cardset])
    with pytest.raises(ValueError, match="duplicate"):
        registry.register(cardset)


def test_loader_rejects_unknown_pattern(tmp_path: Path):
    _seed_minimal_set(tmp_path, code_pattern="not-a-pattern")
    with pytest.raises(CardSetError, match="pattern"):
        load_set(tmp_path)


def test_loader_rejects_duplicate_card_number(tmp_path: Path):
    _seed_minimal_set(tmp_path, duplicate_number=True)
    with pytest.raises(CardSetError, match="duplicate"):
        load_set(tmp_path)


def test_loader_rejects_card_count_mismatch(tmp_path: Path):
    _seed_minimal_set(tmp_path, declared_count=99)
    with pytest.raises(CardSetError, match="card_count"):
        load_set(tmp_path)


def test_loader_rejects_missing_required_field(tmp_path: Path):
    _seed_minimal_set(tmp_path, drop_field="out")
    with pytest.raises(CardSetError, match="out"):
        load_set(tmp_path)


def test_loader_rejects_range_mismatch(tmp_path: Path):
    _seed_minimal_set(tmp_path, mismatched_range=True)
    with pytest.raises(CardSetError, match="range"):
        load_set(tmp_path)


def test_loader_rejects_unknown_event_move(tmp_path: Path):
    _seed_minimal_set(tmp_path, with_event=True, event_move="bogus_move")
    with pytest.raises(CardSetError, match="move"):
        load_set(tmp_path)


def _seed_minimal_set(
    tmp_path: Path,
    *,
    code_pattern: str = "row",
    duplicate_number: bool = False,
    declared_count: int = 2,
    drop_field: str | None = None,
    mismatched_range: bool = False,
    with_event: bool = False,
    event_move: str = "rotate90",
) -> None:
    code_a: dict = {
        "number": "CC-T001-001",
        "id": "test_a",
        "name": "Test A",
        "type": "code",
        "faction": "coder",
        "rarity": "common",
        "out": 1,
        "stab": 1,
        "pattern": code_pattern,
        "ascii": ["[A]"],
        "text": ["Test."],
    }
    code_b: dict = {
        "number": "CC-T001-001" if duplicate_number else "CC-T001-002",
        "id": "test_b",
        "name": "Test B",
        "type": "code",
        "faction": "coder",
        "rarity": "common",
        "out": 1,
        "stab": 1,
        "pattern": "row",
        "ascii": ["[B]"],
        "text": ["Test."],
    }
    if drop_field is not None:
        code_a.pop(drop_field, None)

    if with_event:
        events_payload = {
            "cards": [
                {
                    "number": "CC-T001-003",
                    "id": "test_evt",
                    "name": "Test Event",
                    "type": "event",
                    "rarity": "rare",
                    "move": event_move,
                    "pattern": "global",
                    "ascii": ["[E]"],
                    "text": ["Test."],
                }
            ]
        }
        end_n = 3
    else:
        events_payload = {"cards": []}
        end_n = 2

    range_str = f"CC-T001-001..CC-T001-{end_n:03d}"
    if mismatched_range:
        range_str = "CC-T001-001..CC-T001-009"

    effective_count = declared_count if declared_count != 2 else (3 if with_event else 2)

    (tmp_path / "set.yaml").write_text(
        "id: test_001\n"
        "name: Test\n"
        "version: 0.0.1\n"
        "status: draft\n"
        f"card_count: {effective_count if declared_count == 2 else declared_count}\n"
        "numbering:\n"
        "  format: CC-T001-###\n"
        f"  range: {range_str}\n",
        encoding="utf-8",
    )
    (tmp_path / "codes.yaml").write_text(
        yaml.safe_dump({"cards": [code_a, code_b]}),
        encoding="utf-8",
    )
    (tmp_path / "items.yaml").write_text("cards: []\n", encoding="utf-8")
    (tmp_path / "events.yaml").write_text(
        yaml.safe_dump(events_payload),
        encoding="utf-8",
    )
