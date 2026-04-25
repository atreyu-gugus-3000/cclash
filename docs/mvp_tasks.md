# MVP tasks

The first playable cclash should be small.

Target:

```text
36 cards
training mode
3 runs
highest output wins
inspect mode
clean logs
```

## M1, grid engine

Files:

```text
src/cclash/core/grid.py
tests/test_grid.py
```

Build:

- Grid positions A1..C3
- rotate90
- rotate90ccw
- shift_row
- shift_column
- outer_ring_rotate
- swap_adjacent
- rollback support

Done when:

- all moves are deterministic
- tests cover every move

## M2, pattern engine

Files:

```text
src/cclash/core/patterns.py
tests/test_patterns.py
```

Build patterns:

```text
self
row
column
adjacent
diagonal
mirror
global
```

Done when:

- a card at any slot can ask which fields it affects

## M3, card loader

Files:

```text
src/cclash/cards/loader.py
src/cclash/cards/registry.py
tests/test_card_loader.py
```

Build:

- load YAML card definitions
- validate unique card numbers
- validate unique IDs
- validate required fields
- render ASCII

Done when:

```text
cclash cards list
cclash inspect CC-A001-001
```

can work, even simply.

## M4, effect interpreter

Files:

```text
src/cclash/core/effects.py
tests/test_effects.py
```

Initial effect types:

```text
modify_out
modify_stab
damage
prevent_damage
rotate_grid
shift_column
shift_row
outer_ring_rotate
swap_adjacent
rollback
```

Done when:

- Docker can buff row Codes
- Tmux can buff column Codes
- Cronling can produce Output and mirror damage

## M5, training simulation

Files:

```text
src/cclash/core/engine.py
src/cclash/game/training.py
tests/test_engine.py
```

Build:

- compile a 3x3 grid
- run 3 cycles
- apply optional Events
- calculate total Output
- produce readable RunLog

Done when:

```text
cclash training --sample
```

prints a 3-run result.

## M6, inspect CLI

Files:

```text
src/cclash/cli/app.py
src/cclash/tui/inspect_view.py
```

Build:

- inspect by card number
- inspect by card ID
- inspect grid slot, later
- show affected fields
- show incoming effects, later

Done when:

```text
cclash inspect CC-A001-007
```

shows Docker with ASCII and rules text.

## M7, archive and daily claim

Files:

```text
src/cclash/storage/db.py
src/cclash/game/archive.py
src/cclash/game/daily_claim.py
```

Build:

- SQLite database
- starter cards
- one daily claim
- card instances
- item uses

Done when:

```text
cclash claim
cclash archive
```

work locally.

## M8, LAN prototype

Files:

```text
src/cclash/network/host.py
src/cclash/network/client.py
src/cclash/network/discovery.py
src/cclash/network/pairing.py
src/cclash/network/protocol.py
```

Build:

- host
- discover
- join by IP
- pairing code
- submit compile
- run match

Done when:

Two machines in the same LAN can play one Standard Match.
