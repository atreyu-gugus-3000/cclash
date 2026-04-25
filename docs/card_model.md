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
