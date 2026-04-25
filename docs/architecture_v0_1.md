# cclash architecture v0.1

cclash should start as a small deterministic engine, not as a big UI project.

## 1. Repo layout

```text
cclash/
├─ README.md
├─ pyproject.toml
├─ docs/
│  ├─ rules_v0_1.md
│  ├─ ascii_styleguide.md
│  ├─ architecture_v0_1.md
│  └─ roadmap.md
├─ cardsets/
│  ├─ alpha_001/
│  │  ├─ set.yaml
│  │  ├─ codes.yaml
│  │  ├─ items.yaml
│  │  └─ events.yaml
│  └─ schemas/
├─ src/
│  └─ cclash/
│     ├─ cli/
│     ├─ core/
│     ├─ cards/
│     ├─ game/
│     ├─ storage/
│     ├─ tui/
│     ├─ network/
│     └─ utils/
└─ tests/
```

Naming:

```text
cardsets/             game content / YAML card data
src/cclash/cards/     Python logic for loading, validating and rendering cards
```

## 2. Core modules

```text
core/models.py       card definitions, card instances, player state
core/grid.py         3x3 grid and reconfigure moves
core/patterns.py     affected fields for row, column, adjacent, diagonal
core/effects.py      declarative effect interpreter
core/engine.py       run orchestration
core/scoring.py      output calculation and win conditions
core/validators.py   compile and cardset validation
```

## 3. Strict separation

```text
Card YAML = data
Effect Engine = interprets data
Grid Engine = moves cards
Run Engine = orchestrates match
TUI = displays state
Storage = persists state
Network = transports actions
```

## 4. Card definitions vs card instances

A card definition is the template.

Example: Docker.

A card instance is the owned concrete copy.

Example: Docker instance `card_8f93` with 3 uses left.

Instance fields:

```text
instance_id
card_id
owner_id
created_at
source
xp
level
uses_remaining
status
signature, later
```

## 5. Effect system

Effects must be declarative. Never store executable code in card YAML.

Good:

```yaml
effects:
  - trigger: item_phase
    effect:
      type: modify_stab
      target: friendly_codes_in_row
      amount: 1
```

Bad:

```yaml
effect: enemy.hp -= 3
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

## 6. Run engine

Input:

```text
PlayerState
OpponentState, optional for training
```

Output:

```text
RunResult
├─ output_delta
├─ damage_events
├─ disabled_codes
├─ used_items
├─ triggered_effects
└─ readable_log
```

## 7. First implementation order

1. Grid moves with tests
2. Pattern engine with tests
3. Card model and YAML loader
4. Minimal effect interpreter
5. Training mode simulation
6. Inspect mode
7. Archive and daily claim
8. LAN multiplayer

## 8. MVP boundaries

Do not build first:

- trading
- global online multiplayer
- complex economy
- full TUI
- hardcore permanence
- crafting

Build first:

- deterministic 3x3 engine
- training highscore
- 36-card alpha set
- inspect mode
- clean logs
