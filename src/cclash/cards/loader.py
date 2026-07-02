"""YAML loader for cclash card sets.

A card set lives under ``cardsets/<set_id>/`` and consists of:

- ``set.yaml`` — set metadata (id, version, card_count, numbering)
- ``codes.yaml`` — Code cards
- ``items.yaml`` — Item cards
- ``events.yaml`` — Event cards

The loader validates required fields, enforces type-specific schemas,
and ensures every card number declared in ``numbering.range`` is present
exactly once and matches ``numbering.format``. Effect blocks are parsed
through ``cclash.core.effects.parse_effect_entry`` and attached to each
:class:`cclash.cards.models.CardDef`.

Pattern validation is type-aware:

- Codes and Items must declare a ``pattern`` from the M2 whitelist
  (``cclash.core.patterns.PATTERNS``).
- Events must declare a ``move`` from the Grid-move whitelist; their
  ``pattern`` field is descriptive only and accepted as-is.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from cclash.cards.models import CardSet, CardSetMeta, CodeDef, EventDef, ItemDef
from cclash.core.effects import EffectError, parse_effect_entry
from cclash.core.patterns import PATTERNS

VALID_RARITIES: frozenset[str] = frozenset({"common", "uncommon", "rare", "epic", "legendary"})
VALID_MOVES: frozenset[str] = frozenset(
    {
        "rotate90",
        "rotate90ccw",
        "shift_row",
        "shift_column",
        "outer_ring_rotate",
        "swap_adjacent",
        "rollback",
    }
)

_NUMBER_FORMAT_RE = re.compile(r"^([A-Z0-9]+(?:-[A-Z0-9]+)+)-(#+)$")


class CardSetError(ValueError):
    """Raised when a card set fails to load or validate."""


def load_set(set_dir: str | Path) -> CardSet:
    """Load and validate a single card set directory.

    Raises :class:`CardSetError` if any file is missing, any required
    field is absent, or the declared numbering does not match the
    cards present.
    """
    set_dir = Path(set_dir)
    if not set_dir.is_dir():
        raise CardSetError(f"card set dir not found: {set_dir}")

    meta = _load_meta(set_dir / "set.yaml")
    codes = tuple(
        _build_code(c, set_dir / "codes.yaml") for c in _load_card_list(set_dir / "codes.yaml")
    )
    items = tuple(
        _build_item(c, set_dir / "items.yaml") for c in _load_card_list(set_dir / "items.yaml")
    )
    events = tuple(
        _build_event(c, set_dir / "events.yaml") for c in _load_card_list(set_dir / "events.yaml")
    )

    cardset = CardSet(meta=meta, codes=codes, items=items, events=events)
    _validate_set_consistency(cardset)
    return cardset


def _load_yaml(path: Path) -> Any:
    if not path.is_file():
        raise CardSetError(f"missing file: {path}")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_meta(path: Path) -> CardSetMeta:
    data = _load_yaml(path)
    _require(data, dict, f"{path.name} must be a mapping")
    for f in ("id", "name", "version", "status", "card_count", "numbering"):
        if f not in data:
            raise CardSetError(f"{path.name}: missing field {f!r}")
    numbering = data["numbering"]
    _require(numbering, dict, f"{path.name}: numbering must be a mapping")
    for f in ("format", "range"):
        if f not in numbering:
            raise CardSetError(f"{path.name}: numbering missing field {f!r}")
    rng = numbering["range"]
    if not isinstance(rng, str) or ".." not in rng:
        raise CardSetError(f"{path.name}: numbering.range must be 'A..B' string")
    start, end = rng.split("..", 1)
    return CardSetMeta(
        id=str(data["id"]),
        name=str(data["name"]),
        version=str(data["version"]),
        status=str(data["status"]),
        card_count=int(data["card_count"]),
        number_format=str(numbering["format"]),
        number_range=(start, end),
    )


def _load_card_list(path: Path) -> list[Any]:
    data = _load_yaml(path)
    _require(data, dict, f"{path.name} must be a mapping")
    if "cards" not in data:
        raise CardSetError(f"{path.name}: missing 'cards' key")
    cards = data["cards"]
    if cards is None:
        return []
    _require(cards, list, f"{path.name}: 'cards' must be a list")
    return cards


def _build_code(raw: Any, path: Path) -> CodeDef:
    _check_common(raw, path, expected_type="code")
    for f in ("faction", "out", "stab", "pattern"):
        if f not in raw:
            raise CardSetError(f"{path.name}: code {raw.get('number', '?')} missing {f!r}")
    pattern = str(raw["pattern"])
    if pattern not in PATTERNS:
        raise CardSetError(f"{path.name}: code {raw['number']} has unknown pattern {pattern!r}")
    return CodeDef(
        number=str(raw["number"]),
        id=str(raw["id"]),
        name=str(raw["name"]),
        rarity=str(raw["rarity"]),
        pattern=pattern,
        ascii=tuple(str(s) for s in raw["ascii"]),
        text=tuple(str(s) for s in raw["text"]),
        notes=str(raw["notes"]) if raw.get("notes") else None,
        effects=_parse_effects(raw, path),
        faction=str(raw["faction"]),
        out=int(raw["out"]),
        stab=int(raw["stab"]),
    )


def _build_item(raw: Any, path: Path) -> ItemDef:
    _check_common(raw, path, expected_type="item")
    for f in ("family", "uses", "pattern"):
        if f not in raw:
            raise CardSetError(f"{path.name}: item {raw.get('number', '?')} missing {f!r}")
    pattern = str(raw["pattern"])
    if pattern not in PATTERNS:
        raise CardSetError(f"{path.name}: item {raw['number']} has unknown pattern {pattern!r}")
    return ItemDef(
        number=str(raw["number"]),
        id=str(raw["id"]),
        name=str(raw["name"]),
        rarity=str(raw["rarity"]),
        pattern=pattern,
        ascii=tuple(str(s) for s in raw["ascii"]),
        text=tuple(str(s) for s in raw["text"]),
        notes=str(raw["notes"]) if raw.get("notes") else None,
        effects=_parse_effects(raw, path),
        family=str(raw["family"]),
        uses=int(raw["uses"]),
    )


def _build_event(raw: Any, path: Path) -> EventDef:
    _check_common(raw, path, expected_type="event")
    for f in ("move", "pattern"):
        if f not in raw:
            raise CardSetError(f"{path.name}: event {raw.get('number', '?')} missing {f!r}")
    move = str(raw["move"])
    if move not in VALID_MOVES:
        raise CardSetError(f"{path.name}: event {raw['number']} has unknown move {move!r}")
    return EventDef(
        number=str(raw["number"]),
        id=str(raw["id"]),
        name=str(raw["name"]),
        rarity=str(raw["rarity"]),
        pattern=str(raw["pattern"]),
        ascii=tuple(str(s) for s in raw["ascii"]),
        text=tuple(str(s) for s in raw["text"]),
        notes=str(raw["notes"]) if raw.get("notes") else None,
        effects=_parse_effects(raw, path),
        move=move,
    )


def _check_common(raw: Any, path: Path, *, expected_type: str) -> None:
    _require(raw, dict, f"{path.name}: card entries must be mappings")
    for f in ("number", "id", "name", "type", "rarity", "ascii", "text"):
        if f not in raw:
            raise CardSetError(f"{path.name}: card missing field {f!r}")
    if raw["type"] != expected_type:
        raise CardSetError(
            f"{path.name}: card {raw['number']} has type {raw['type']!r}, "
            f"expected {expected_type!r}"
        )
    if raw["rarity"] not in VALID_RARITIES:
        raise CardSetError(
            f"{path.name}: card {raw['number']} has unknown rarity {raw['rarity']!r}"
        )
    _require(raw["ascii"], list, f"{path.name}: card {raw['number']} ascii must be a list")
    _require(raw["text"], list, f"{path.name}: card {raw['number']} text must be a list")


def _require(value: Any, expected_type: type, msg: str) -> None:
    if not isinstance(value, expected_type):
        raise CardSetError(msg)


def _validate_set_consistency(cardset: CardSet) -> None:
    cards = cardset.all_cards()

    if len(cards) != cardset.meta.card_count:
        raise CardSetError(
            f"set.yaml card_count={cardset.meta.card_count}, but {len(cards)} cards loaded"
        )

    seen_numbers: set[str] = set()
    seen_ids: set[str] = set()
    for c in cards:
        if c.number in seen_numbers:
            raise CardSetError(f"duplicate card number: {c.number}")
        if c.id in seen_ids:
            raise CardSetError(f"duplicate card id: {c.id}")
        seen_numbers.add(c.number)
        seen_ids.add(c.id)

    expected_numbers = _expand_range(cardset.meta.number_format, cardset.meta.number_range)
    if seen_numbers != expected_numbers:
        missing = sorted(expected_numbers - seen_numbers)
        extra = sorted(seen_numbers - expected_numbers)
        raise CardSetError(
            f"card numbers do not match declared range; missing={missing}, extra={extra}"
        )


def _expand_range(number_format: str, number_range: tuple[str, str]) -> set[str]:
    m = _NUMBER_FORMAT_RE.match(number_format)
    if not m:
        raise CardSetError(f"unsupported numbering.format: {number_format!r}")
    prefix, hashes = m.group(1), m.group(2)
    width = len(hashes)
    start, end = number_range
    sp = f"{prefix}-"
    if not (start.startswith(sp) and end.startswith(sp)):
        raise CardSetError(f"range {number_range} does not match format {number_format!r}")
    try:
        start_n = int(start[len(sp) :])
        end_n = int(end[len(sp) :])
    except ValueError as e:
        raise CardSetError(f"invalid range numbers in {number_range}: {e}") from e
    if start_n > end_n:
        raise CardSetError(f"range start > end: {number_range}")
    return {f"{prefix}-{n:0{width}d}" for n in range(start_n, end_n + 1)}


def _parse_effects(raw: dict, path: Path) -> tuple:
    entries = raw.get("effects")
    if entries is None:
        return ()
    if not isinstance(entries, list):
        raise CardSetError(f"{path.name}: card {raw.get('number', '?')} 'effects' must be a list")
    parsed = []
    for i, entry in enumerate(entries):
        try:
            parsed.append(parse_effect_entry(entry))
        except EffectError as e:
            raise CardSetError(
                f"{path.name}: card {raw.get('number', '?')} effects[{i}]: {e}"
            ) from e
    return tuple(parsed)
