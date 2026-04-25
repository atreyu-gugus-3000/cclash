# cclash ASCII styleguide v0.1

The ASCII is not decoration. It is the interface language of the cards.

The goal is a small visual grammar that is easy to combine, easy to inspect, and recognizable in a terminal.

## 1. Codes

A Code has 4 required zones and 2 optional zones.

```text
[HAT]        optional, rarity / class / title
[ZONE 1]     head / faction
[ZONE 2]     eyes / status / attitude
[ZONE 3]     core / ability type
[ZONE 4]     legs / role / movement
[TAIL]       optional, secondary effect / activity
```

Example:

```text
 /^\
 /|__|\
(x.  .x)
< !! >
:;;;  ;;;: ==>
```

Meaning:

- rare Coder
- aggressive
- attack core
- claw / melee feet
- output tail

## 2. Code heads, faction

```text
 /|__|\     Coder
 /|~~|\     Vibecoder
 /|oo|\     KI-Noob
 [____]     KI-Verweigerer
```

## 3. Code eyes, attitude / status

```text
(o.  .o)    neutral
(x.  .x)    aggressive
(^.  .^)    support
(-.  .-)    defensive
(X.  .X)    corrupted / stunned
(*.  .*)    rare / mystic
```

## 4. Code core, ability type

```text
< == >      compute / boost
< !! >      attack / burst
< ## >      defense / shield
< ~~ >      heal / support
< ?! >      chaos / random
< :: >      speed / utility
```

## 5. Code legs, role

```text
:;;__;;:      basic
:;;;  ;;;:    claws / melee
:==:  :==:    tank
::.    .::    swift
:~:    :~:    stealth / virus
```

## 6. Optional hats

```text
  ^          uncommon
 /^\        rare
 /*\        legendary
 [~]        specialist
 {#}        elite / armored
```

## 7. Optional tails

```text
~>>         network / data stream
==>         output / attack boost
+++         regen / heal
...         stealth / idle
{o}         equipped module / drone
```

## 8. Items

Items also have 4 zones, but with different semantics.

```text
[ZONE 1]    item family / short code
[ZONE 2]    icon / shape
[ZONE 3]    effect core
[ZONE 4]    pattern / range
```

Docker:

```text
[DKR]
/ffx\
\xss/
=row=
```

Tmux:

```text
[TMX]
  ^
  ||
~<>~
|col|
```

Firewall Cloak:

```text
[FW]
/###\
\###/
+adj+
```

Overclock Chip:

```text
[CLK]
/*!*\
\!!!/
diag
```

## 9. Events

Events have 4 zones.

```text
[ZONE 1]    event type
[ZONE 2]    signal
[ZONE 3]    movement icon
[ZONE 4]    move / mode
```

Rotate90:

```text
[EVT]
 !90!
 <()>
|rot|
```

Outer Ring:

```text
[EVT]
 !OR!
 <[]>
|rng|
```

Rollback:

```text
[EVT]
 !<<!
 <()>
|bak|
```

Column Shift:

```text
[EVT]
 !C3!
 <||>
|shf|
```

## 10. Design rules

Keep it small.

- 4 zones per card are enough.
- Codes may have hat and tail.
- Items and Events should stay compact.
- ASCII must be readable in narrow terminal cells.
- The same symbols should always mean the same thing.
- Position and pattern matter more than visual complexity.

## 11. First visual vocabulary

Start with:

```text
4 faction heads
6 eye states
6 cores
5 legs
5 hats
5 tails
```

This already gives enough variety for a first set.
