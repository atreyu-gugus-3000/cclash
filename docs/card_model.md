# Card model v0.1

cclash separates card definitions from card instances.

## 1. Card definition

A card definition is the template shipped with a card set.

Example:

```text
Docker
CC-A001-007
Item
Uncommon
Pattern: row
```

Definition fields:

```text
number
id
name
type
rarity
ascii
text
notes
```

Type-specific fields:

```text
Code: faction, out, stab, pattern
Item: family, uses, pattern
Event: move, pattern
```

## 2. Card number

Every card has a stable printed number.

Format:

```text
CC-A001-001
```

Meaning:

```text
CC       cclash
A001     Alpha 001 set
001      card number in set
```

Card numbers are used for discussion and balancing.

Example:

```text
CC-A001-008 Tmux needs a nerf.
```

## 3. Card instance

A card instance is a concrete owned copy.

Example:

```text
Docker #card_8f93
uses_remaining: 3
owner: player_123
```

Instance fields:

```text
instance_id
card_id
card_number
owner_id
created_at
source
xp
level
uses_remaining
status
signature, later
```

## 4. Status

Possible statuses:

```text
active
archived
disabled
corrupted
burned
destroyed
spent
```

Suggested usage:

- Codes can be active, disabled, corrupted, destroyed
- Items can be active, burned, archived
- Events can be active, spent, archived

## 5. Effects

Effects are declarative data.

Example:

```yaml
effects:
  - trigger: item_phase
    condition:
      adjacent_faction: coder
    effect:
      type: modify_out
      target: adjacent_coder_codes
      amount: 1
```

The engine interprets known effect types only.

### Conditions (v0.1)

`condition` is optional and holds exactly one key. All conditions are
evaluated on the friendly grid relative to the card's position; row and
diagonal kinds ignore the source slot itself, `column_items_exactly`
counts the full column.

```text
adjacent_faction: <faction>       at least one adjacent Code of that faction
not_adjacent_faction: <faction>   no adjacent Code of that faction
row_has_item: true                at least one Item in this row
diagonal_has_event: true|false    an Event is (not) diagonal to this card
row_has_card: <card_id>           a specific card is in this row
column_items_exactly: <n>         this column contains exactly n Items
```

### Roll clause (v0.1)

`roll` is optional and machine-encodes the W6 patterns from
`randomness_v0_1.md §3`. The effect fires only when the match W6 lands
on one of the listed faces; the engine rolls once per evaluation and
logs every roll.

```yaml
- trigger: end_of_run
  condition:
    diagonal_has_event: false
  roll:
    on: [1, 2, 3]       # "on 1-3: effect"
  effect:
    type: damage
    target: self
    amount: 1
```

## 6. Target language

Initial targets:

```text
self
mirror
friendly_codes_in_row
friendly_codes_in_column
friendly_codes_adjacent
friendly_codes_diagonal
adjacent_coder_codes
all_friendly_codes
```

## 7. Trigger language

Initial triggers:

```text
item_phase
code_execution
before_damage
after_damage
end_of_run
reconfigure
on_disable
```

## 8. Source

A card instance can come from:

```text
starter
daily_claim
reward
hardcore_reward
trade, later
admin_seed, dev only
```

## 9. Draft rule

During early design, cards may be incomplete.

Required for discussion:

```text
number
id
name
type
ascii
text
```

Required for engine:

```text
number
id
name
type
rarity
pattern
all type-specific stats
machine-readable effects
```
