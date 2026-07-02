"""Card definitions for cclash.

Card definitions are immutable templates loaded from cardset YAML files.
They are not card *instances*; see ``docs/card_model.md §3`` for the
distinction between definition (template, ``CC-A001-007 Docker``) and
instance (a concrete owned copy with ``uses_remaining`` and ``status``).

Codes, Items, and Events share a common base of fields. Type-specific
fields live on the subclasses so the type system enforces, for example,
that only Items have ``uses`` and only Codes have ``out``/``stab``.

All definition classes are frozen dataclasses with ``kw_only=True``;
loaders construct them by keyword and the engine treats them as values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from cclash.core.effects import EffectSpec


@dataclass(frozen=True, kw_only=True)
class CardDef:
    number: str
    id: str
    name: str
    type: Literal["code", "item", "event"]
    rarity: str
    pattern: str
    ascii: tuple[str, ...]
    text: tuple[str, ...]
    notes: str | None = None
    effects: tuple[EffectSpec, ...] = ()


@dataclass(frozen=True, kw_only=True)
class CodeDef(CardDef):
    type: Literal["code"] = "code"
    faction: str
    out: int
    stab: int


@dataclass(frozen=True, kw_only=True)
class ItemDef(CardDef):
    type: Literal["item"] = "item"
    family: str
    uses: int


@dataclass(frozen=True, kw_only=True)
class EventDef(CardDef):
    type: Literal["event"] = "event"
    move: str


@dataclass(frozen=True, kw_only=True)
class CardSetMeta:
    id: str
    name: str
    version: str
    status: str
    card_count: int
    number_format: str
    number_range: tuple[str, str]


@dataclass(frozen=True, kw_only=True)
class CardSet:
    meta: CardSetMeta
    codes: tuple[CodeDef, ...]
    items: tuple[ItemDef, ...]
    events: tuple[EventDef, ...]

    def all_cards(self) -> tuple[CardDef, ...]:
        return self.codes + self.items + self.events
