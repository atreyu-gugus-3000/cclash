# Inspect mode v0.1

Inspect mode is both player UI and debugging tool.

It should feel like a tiny vim/nano card inspector.

## 1. Goals

Inspect mode should answer:

```text
What is this card?
What does it affect?
What affects it?
What will happen next Run?
Why did Output change?
```

## 2. Controls

```text
h j k l     move cursor
Enter       inspect selected card
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

## 3. Grid view

```text
+----------+----------+----------+
| A1 Cron  | A2 Dkr   | A3 Vibe  |
+----------+----------+----------+
| B1 Tmux  | B2 Patch | B3 Null  |
+----------+----------+----------+
| C1 R90   | C2 Cache | C3 Ring  |
+----------+----------+----------+
```

## 4. Card inspect

Example:

```text
:inspect A2

+-- Docker ------------------------+
| Number: CC-A001-007              |
| Type: Item                       |
| Family: Infra                    |
| Rarity: Uncommon                 |
| Pattern: row                     |
| Uses: 5/5                        |
|                                  |
| [DKR]                            |
| /ffx\                            |
| \xss/                            |
| =row=                            |
|                                  |
| Effect:                          |
| All friendly Codes in this row   |
| gain +1 STAB.                    |
|                                  |
| If adjacent to a Coder Code,     |
| that Code gains +1 OUT.          |
+----------------------------------+
```

## 5. Affected fields

Inspect should show affected fields.

Example:

```text
Docker at A2
Pattern: row
Affected fields: A1, A2, A3
Valid targets: A1 Cronling, A3 Vibe Bug
```

## 6. Incoming effects

Inspect should also show what affects the selected card.

Example:

```text
Cronling at A1
Incoming effects:
- Docker at A2: +1 STAB
- Tmux at B1: +1 OUT
```

## 7. Preview next Run

Later, inspect mode should preview the next Run.

Example:

```text
Next Run preview:
Cronling OUT: 2 base +1 Docker +1 Tmux = 4
Cronling damage: 1 to enemy A1
Cronling STAB: 4 base +1 Docker = 5
```

## 8. Run log

Run log should be readable and deterministic.

Example:

```text
Run 2

Item Effects:
- Docker buffs Cronling, +1 STAB
- Tmux buffs Patch Goblin, +1 OUT

Code Execution:
- Cronling produces 3 Output
- Patch Goblin produces 2 Output
- Null Imp hits enemy B3 for 2 damage

Damage:
- enemy B3 STAB 2 -> 0
- enemy B3 disabled

Score:
- This Run: 9 Output
- Total: 21 Output
```

## 9. Command mode personality

Important prompts use the cclash yes/no style.

```text
Rotate grid 90 degrees clockwise?
1 yes
2 yes, always in this game
3 no
>
```

This is both UX and running gag.
