# Randomness in cclash v0.1

The cclash engine is deterministic. The same inputs always produce the same outputs.

This is required for:

- testable engine logic
- LAN play with host-authoritative match state
- replay logs that match what really happened
- network sync between host and client

## 1. The W6 rule

Random outcomes on cards are not expressed as percentages. They are expressed as a six-sided die roll, the W6.

Bad:

```text
50% chance: lose 1 STAB after Run.
```

Good:

```text
On Run, roll W6.
On 1-3, lose 1 STAB after Run.
```

Reasons:

- W6 is a tactile concept that fits the lineage from earlier dice-based prototypes.
- W6 outcomes are explicit and easy to read on a card.
- Discrete buckets are easier to balance than continuous probabilities.
- A single shared random source keeps replays deterministic.

## 2. Sparse use

Random outcomes are not on every card.

Suggested cap for the alpha set:

```text
At most 2 of 12 cards use a W6 roll.
```

Random should feel like a flavor element, not a core mechanic. Most cards should have deterministic effects.

## 3. Allowed roll patterns

Cards may use:

```text
roll W6
on N: effect
on N-M: effect
on N or higher: effect
on N or lower: effect
```

Not allowed in v0.1:

```text
multiple dice
exploding dice
re-rolls
custom die faces
```

Keep it simple. One W6, clear thresholds.

## 4. Engine implementation

The engine uses a single `Random` instance per match, seeded from the match ID and turn order.

```text
match_seed = hash(host_player_id, client_player_id, match_id, cardset_hash)
```

Every W6 roll inside the match draws from the same stream. Order of rolls is deterministic and recorded in the run log.

This means:

- the same match replays identically
- host and client agree on roll outcomes
- tests can pin a seed and assert exact results

## 5. Run log entries for rolls

Every roll is logged.

Example:

```text
Vibe Bug at A3: roll W6 -> 4
  -> diagonal Event present, +2 OUT applied
```

Or:

```text
Vibe Bug at A3: roll W6 -> 2
  -> no diagonal Event, lose 1 STAB after Run
```

The number rolled is part of the log. Players can verify outcomes.

## 6. No client-side rolls

In LAN play, only the host rolls. Clients never generate random numbers that affect match state.

This prevents trivial cheating where a client re-rolls until it likes the result.

## 7. Out of scope for v0.1

Not yet decided:

- daily-claim rarity rolls
- card draft randomness
- starter-pack composition

These will get their own seeded streams later, separate from the match stream.
