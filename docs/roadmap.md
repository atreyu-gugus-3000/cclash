# cclash roadmap

## Milestone 0, capture concept

- README
- rules v0.1
- ASCII styleguide
- architecture
- initial card ideas

## Milestone 1, offline core

Goal: simulate one training match in Python.

Build:

- 3x3 Grid
- reconfigure moves
- patterns
- card models
- run engine
- output scoring

Tests:

- rotate90
- shift row / column
- outer ring
- adjacent / diagonal / row / column patterns
- simple item buff
- simple code output

## Milestone 2, cardset YAML

Goal: load cards from files.

Build:

- cards/alpha_001/codes.yaml
- cards/alpha_001/items.yaml
- cards/alpha_001/events.yaml
- loader
- validator
- inspect command

## Milestone 3, training mode

Goal: playable solo loop.

Commands:

```text
cclash compile
cclash training
cclash inspect
cclash log
```

## Milestone 4, collection

Goal: feel like a collecting game.

Build:

- SQLite archive
- card instances
- starter cards
- daily claim
- item uses
- highscore persistence

Commands:

```text
cclash claim
cclash archive
cclash audit
```

## Milestone 5, TUI

Goal: it feels like a terminal game.

Build:

- grid view
- inspect view
- compile view
- training view
- run log view

Use Rich first. Textual later if needed.

## Milestone 6, LAN PvP

Goal: two players in the same network.

Build:

- host
- discover
- join
- pairing code
- match protocol
- signed actions, later

Commands:

```text
cclash host
cclash discover
cclash join
cclash fight
```

## Milestone 7, hardcore and rewards

Goal: add risk.

Build:

- hardcore mode
- destroyed Codes
- better rewards
- confirmation UX

## Principle

Keep the first playable version small.

```text
36 cards
training mode
3 runs
highest output wins
```
