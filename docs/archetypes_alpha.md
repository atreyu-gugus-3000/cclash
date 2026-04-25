# Alpha archetypes overview

This document captures the first intended playstyles for Alpha 001.

Purpose:

- guide card design
- keep factions distinct
- avoid random card accumulation
- define what each strategy wants
- define counters and weaknesses

Core rule:

```text
Every archetype must care about position.
```

## 1. Alpha design goal

Alpha 001 should teach the core machine:

```text
Codes produce Output.
Items tune Codes by position.
Events move the grid.
```

Alpha should not contain every possible idea.

Alpha should prove:

- row matters
- column matters
- diagonal matters
- adjacent matters
- reconfigure matters
- stability matters
- output race matters

## 2. Archetype overview

| Archetype | Core fantasy | Main faction | Main pattern | Risk level |
|---|---|---|---|---|
| Row Engine | stable production line | Coder | row | low |
| Column Sync | synchronized vertical stack | Coder / Tooling | column | medium |
| Chaos Diagonal | risky burst combos | Vibecoder | diagonal | high |
| Tank Denial | survive, block, outlast | KI-Verweigerer | adjacent | low |
| Learner Swarm | weak Codes growing through triggers | KI-Noobs | adjacent / column | medium |
| Overclock Highscore | maximum Training Output, risky | Vibecoder / Hardware | diagonal | high |
| Center Machine | protect B2, rotate around it | mixed | outer ring / center | medium |
| Anti-Event Control | punish Reconfigure reliance | KI-Verweigerer | adjacent / global | medium |

## 3. Archetype 1, Row Engine

### Fantasy

A clean production row. Docker, Coder Codes and stable positioning.

### Wants

- Codes in same row as row Items
- Docker-style support
- predictable Output
- low randomness

### Key cards

```text
CC-A001-001 Cronling
CC-A001-006 Patch Goblin
CC-A001-007 Docker
```

### Strengths

- reliable Output
- good Stability
- easy to understand
- strong Training baseline

### Weaknesses

- vulnerable to row disruption
- less explosive than diagonal builds
- predictable

### Design needs

Alpha should include:

- at least 2 row Items
- at least 2 Codes that benefit from row Items
- at least 1 Event that helps restore row alignment

## 4. Archetype 2, Column Sync

### Fantasy

Vertical multiplexing. Tmux splits the board into synchronized execution lanes.

### Wants

- exactly 2 Codes in a column
- column Items
- shift_column / rotate90 decisions

### Key cards

```text
CC-A001-005 Null Imp
CC-A001-008 Tmux
CC-A001-011 Rotate90
```

### Strengths

- strong with planning
- benefits heavily from Reconfigure
- creates satisfying before/after board states

### Weaknesses

- can break itself with bad rotation
- needs exact counts
- more fragile than Row Engine

### Design needs

Alpha should include:

- at least 2 column Items
- at least 2 column-aware Codes
- at least 2 Events that affect columns

## 5. Archetype 3, Chaos Diagonal

### Fantasy

Vibecoder risk build. Huge Output if diagonals line up, self-damage if they do not.

### Wants

- Events diagonally placed to Codes
- Overclock Chip
- diagonal Pattern Items
- risky d6 outcomes

### Key cards

```text
CC-A001-002 Vibe Bug
CC-A001-010 Overclock Chip
CC-A001-011 Rotate90
CC-A001-012 Outer Ring
```

### Strengths

- high Output ceiling
- exciting Training highscores
- rewards clever Reconfigure

### Weaknesses

- self-damage
- bad d6 rolls
- can collapse in Hardcore

### Design needs

Alpha should include:

- at least 2 diagonal payoff Codes
- at least 2 diagonal Items
- at least 1 safe stabilizer so the build is not pure gambling

## 6. Archetype 4, Tank Denial

### Fantasy

A stubborn system that refuses to play along. It blocks Events and survives burst.

### Wants

- high STAB Codes
- Firewall-style adjacent protection
- anti-Event text
- stable positioning

### Key cards

```text
CC-A001-003 Legacy Brick
CC-A001-009 Firewall Cloak
```

### Strengths

- survives burst
- good in Hardcore
- counters Chaos Diagonal

### Weaknesses

- low Output
- can lose Training races
- may be boring if over-supported

### Design needs

Alpha should include:

- at least 2 anti-Event / denial cards
- at least 2 high-STAB Codes
- at least 1 way to slowly convert defense into Output

## 7. Archetype 5, Learner Swarm

### Fantasy

Small KI-Noobs learn from adjacent Items and weird Events.

### Wants

- multiple small Codes
- adjacent Items
- XP triggers
- d6 rerolls

### Key cards

```text
CC-A001-004 Promptling
CC-A001-009 Firewall Cloak
CC-A001-008 Tmux
```

### Strengths

- good progression feeling
- fun in long-term collection
- can turn weak cards into favorites

### Weaknesses

- starts weak
- depends on triggers
- may be hard to balance if XP snowballs

### Design needs

Alpha should include:

- at least 2 KI-Noob Codes
- at least 2 XP-related effects
- at least 1 soft protection Item

## 8. Archetype 6, Overclock Highscore

### Fantasy

Push Output at all costs. Great for Training, risky in PvP, terrifying in Hardcore.

### Wants

- Overclock Chip
- high OUT Codes
- diagonal positioning
- d6 risk cards

### Key cards

```text
CC-A001-002 Vibe Bug
CC-A001-010 Overclock Chip
CC-A001-005 Null Imp
```

### Strengths

- highest Training ceiling
- exciting results
- creates memorable runs

### Weaknesses

- damages own Codes
- bad in grindy matches
- can destroy itself in Hardcore

### Design needs

Alpha should include:

- very clear risk wording
- no free global protection
- at least 1 counter from Tank Denial

## 9. Archetype 7, Center Machine

### Fantasy

The center slot B2 is the stable core. The outer ring rotates around it.

### Wants

- strong center Code or Item
- Outer Ring
- effects that care about adjacent or ring positions

### Key cards

```text
CC-A001-012 Outer Ring
CC-A001-006 Patch Goblin
CC-A001-009 Firewall Cloak
```

### Strengths

- visually satisfying
- easy to understand once seen
- makes the 3x3 grid feel unique

### Weaknesses

- center can become too strong
- needs clear rules
- can become repetitive

### Design needs

Alpha should include:

- at least 1 center payoff
- at least 1 center counter
- clear distinction between center and outer ring

## 10. Archetype 8, Anti-Event Control

### Fantasy

Let the opponent over-plan, then jam their Reconfigure engine.

### Wants

- KI-Verweigerer Codes
- anti-Event text
- high STAB
- effects that punish moved cards

### Key cards

```text
CC-A001-003 Legacy Brick
CC-A001-009 Firewall Cloak
```

### Strengths

- counters Rotate90 / Chaos builds
- good in PvP
- gives defensive players identity

### Weaknesses

- weak in Training mode if too passive
- can feel unfun if it prevents all play

### Design needs

Alpha should include soft denial, not hard locks.

Good:

```text
Ignore first opposing Event affecting this slot.
```

Avoid early:

```text
Opponent cannot play Events.
```

## 11. Alpha skeleton targets

For a 36-card Alpha MVP:

```text
16 Codes
12 Items
8 Events
```

Suggested slot structure:

### Codes, 16

```text
4 Coder
4 Vibecoder
4 KI-Noob
4 KI-Verweigerer
```

Role distribution:

```text
4 basic Output Codes
4 support / stabilizer Codes
4 risk / burst Codes
4 defensive / denial Codes
```

### Items, 12

```text
3 row Items
3 column Items
2 adjacent Items
2 diagonal Items
1 self Item
1 flexible utility Item
```

### Events, 8

```text
2 rotate Events
2 shift Events
2 outer ring / ring Events
1 swap Event
1 rollback Event
```

## 12. Balancing rules

1. Every card should create a positioning decision.
2. No card should be good in every grid.
3. Commons teach one concept.
4. Uncommons combine concept + condition.
5. Rares change topology or bend a rule.
6. Codes should feel emotionally valuable.
7. Items may burn.
8. Events are Reconfigure permissions, not generic spells.
9. Output is the goal, Stability prevents degeneration.
10. Good ideas that do not fit Alpha go to the parking lot.

## 13. Parking lot examples

Do not force these into Alpha unless they serve a slot.

```text
Quantum Fork
Stack Overflow Dragon
Git Rebase Event
Daemon Queen
Memory Leak Curse
Garbage Collector
Kernel Panic
Rubber Duck of Truth
```

## 14. Current Alpha 001 mapping

Current 12-card draft coverage:

```text
Row Engine:
- CC-A001-001 Cronling
- CC-A001-006 Patch Goblin
- CC-A001-007 Docker

Column Sync:
- CC-A001-005 Null Imp
- CC-A001-008 Tmux
- CC-A001-011 Rotate90

Chaos Diagonal:
- CC-A001-002 Vibe Bug
- CC-A001-010 Overclock Chip
- CC-A001-011 Rotate90
- CC-A001-012 Outer Ring

Tank Denial:
- CC-A001-003 Legacy Brick
- CC-A001-009 Firewall Cloak

Learner Swarm:
- CC-A001-004 Promptling
- CC-A001-008 Tmux
- CC-A001-009 Firewall Cloak

Center Machine:
- CC-A001-006 Patch Goblin
- CC-A001-009 Firewall Cloak
- CC-A001-012 Outer Ring
```

Gaps after first 12 cards:

```text
Need more Events, especially shift_row, shift_column, swap_adjacent, rollback.
Need more KI-Noob cards.
Need more KI-Verweigerer cards.
Need second row Item and second column Item.
Need explicit center payoff and center counter.
```
