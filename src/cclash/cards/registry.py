"""Lookup index for loaded card sets.

A :class:`Registry` holds one or more :class:`CardSet` objects and
provides fast lookup by stable card number (``CC-A001-007``) or by id
(``docker``). Numbers and ids must be globally unique across all
registered sets — the loader guarantees uniqueness within a single set;
the Registry extends that guarantee across sets.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from cclash.cards.models import CardDef, CardSet


class Registry:
    def __init__(self, sets: Iterable[CardSet] = ()) -> None:
        self._sets: list[CardSet] = []
        self._by_number: dict[str, CardDef] = {}
        self._by_id: dict[str, CardDef] = {}
        for s in sets:
            self.register(s)

    def register(self, cardset: CardSet) -> None:
        for c in cardset.all_cards():
            if c.number in self._by_number:
                raise ValueError(f"duplicate card number across sets: {c.number}")
            if c.id in self._by_id:
                raise ValueError(f"duplicate card id across sets: {c.id}")
        for c in cardset.all_cards():
            self._by_number[c.number] = c
            self._by_id[c.id] = c
        self._sets.append(cardset)

    def by_number(self, number: str) -> CardDef:
        if number not in self._by_number:
            raise KeyError(f"unknown card number: {number}")
        return self._by_number[number]

    def by_id(self, id_: str) -> CardDef:
        if id_ not in self._by_id:
            raise KeyError(f"unknown card id: {id_}")
        return self._by_id[id_]

    def find(self, key: str) -> CardDef:
        """Look up a card by either its number or its id."""
        if key in self._by_number:
            return self._by_number[key]
        if key in self._by_id:
            return self._by_id[key]
        raise KeyError(f"unknown card key: {key!r}")

    def __len__(self) -> int:
        return len(self._by_number)

    def __iter__(self) -> Iterator[CardDef]:
        return iter(self._by_number.values())

    @property
    def sets(self) -> tuple[CardSet, ...]:
        return tuple(self._sets)
