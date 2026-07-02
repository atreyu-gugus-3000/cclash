# cclash rules v0.1

Terminal-native grid TCG.

```text
Compile once.
Reconfigure three times.
Highest output wins.
```

## 1. Goal

Each player compiles a 3x3 grid once. The grid then runs three times. Between runs, Events may reconfigure the grid. After the third run, the player with the highest total Output wins.

## 2. Loadout

A compiled grid contains exactly 9 cards:

```text
3 Codes
4 Items
2 Events
```

Grid:

```text
+------+------+------+
| A1   | A2   | A3   |
+------+------+------+
| B1   | B2   | B3   |
+------+------+------+
| C1   | C2   | C3   |
+------+------+------+
```

Compile happens once per match. After compile, cards only move through Events.

## 3. Card types

### Codes

Codes are the active program creatures. They produce Output, can deal damage, gain XP, and level up.

Core attributes:

- `OUT`, base Output per Run
- `STAB`, Stability / HP
- `pattern`, how effects or targeting works
- `xp`, experience
- `level`, progression
- `status`, active, disabled, corrupted, destroyed

### Items

Items are modules and tools. They modify Codes by position.

Items usually have `uses`. When uses reach 0, the Item is burned.

### Events

Events are one-shot topology actions. They do not mainly deal damage, they change the grid.

Events are consumed after use. Consuming empties the Event's slot first,
then the move applies to the grid — the freed slot moves with everything
else. Empty slots stay in play and can be repositioned by later Events.

## 4. Match flow

```text
1. Compile
2. Cycle 1
   2.1 Reconfigure
   2.2 Run
3. Cycle 2
   3.1 Reconfigure
   3.2 Run
4. Cycle 3
   4.1 Reconfigure
   4.2 Run
5. Score
```

In each Reconfigure phase, a player may play one Event or pass.

## 5. Run order

Each Run resolves in this order:

```text
1. Item Effects
2. Code Execution
3. Damage / Disable
4. Output Scoring
```

### Item Effects

Items check their position and apply effects to valid Codes according to their pattern.

Allowed v0.1 patterns:

```text
self
adjacent
diagonal
row
column
```

### Code Execution

Codes produce Output.

```text
Output = OUT + buffs - debuffs
```

If no target is specified, a Code targets the mirrored enemy slot.

### Damage / Disable

Damage reduces STAB. A Code at 0 STAB becomes disabled.

Disabled Codes:

- produce no Output
- do not trigger active effects
- remain in the grid

In Hardcore mode, disabled Codes may be destroyed.

## 6. Reconfigure moves

### rotate90

```text
A B C      G D A
D E F  ->  H E B
G H I      I F C
```

### rotate90ccw

```text
A B C      C F I
D E F  ->  B E H
G H I      A D G
```

### shift_column

Example, column 3 to column 1:

```text
A B C      C A B
D E F  ->  F D E
G H I      I G H
```

### shift_row

Example, row 3 to row 1:

```text
A B C      G H I
D E F  ->  A B C
G H I      D E F
```

### outer_ring_rotate

```text
A B C      D A B
D E F  ->  G E C
G H I      H I F
```

### swap_adjacent

```text
A B C      A E C
D E F  ->  D B F
G H I      G H I
```

### rollback

Restores the grid state from before the last Reconfigure action. Output and damage are not undone.

## 7. Win conditions

### Standard win

After 3 Runs, highest total Output wins.

### Crash win

If a player has no active Codes, the opponent wins immediately.

### Tie breakers

1. More active Codes
2. Higher total remaining STAB
3. More remaining Item uses
4. Draw

## 8. Modes

### Training

Solo highscore mode.

```text
Compile
Run 1
Reconfigure
Run 2
Reconfigure
Run 3
Save highscore
```

### Standard Match

LAN PvP.

- no permanent Code loss
- XP enabled
- Items lose uses
- Events are consumed

### Hardcore Match

Optional risk mode.

- disabled Codes can be destroyed
- destroyed Codes are lost
- higher XP
- better rewards
- possible high-win bonus

Hardcore must always require explicit confirmation.

```text
Hardcore mode may destroy Codes.
Continue?
1 yes
2 yes, always in this game
3 no
>
```

## 9. Progression

### Daily drop

One card per player per day.

Suggested type distribution:

```text
45 % Code
35 % Item
20 % Event
```

Suggested rarity distribution:

```text
70 % Common
20 % Uncommon
9 % Rare
1 % Legendary
```

### Start cards

Each player starts with 20 Common cards:

```text
8 Codes
8 Items
4 Events
```

### XP

Suggested XP:

```text
+1 XP per match
+1 XP if Code survives active
+1 XP if Code deals damage
+2 XP for win
+3 XP for Hardcore win
```

### Item uses

Suggested uses:

```text
Common: 3
Uncommon: 6
Rare: 12
Legendary: repairable
```

## 10. Inspect mode

Vim/nano-style card inspector.

```text
h j k l     move cursor
Enter       inspect card
Tab         next panel
q           back
:           command mode
:fight      start match
:training   start training
:compile    build grid
:archive    show collection
:grid       show grid
:log        show run log
```
