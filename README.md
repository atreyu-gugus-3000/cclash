# cclash

Terminal-native grid TCG.

```text
Compile once.
Reconfigure three times.
Highest output wins.
```

## Concept

cclash is a fast local terminal card game. Players collect cards and compile a 3x3 grid from:

```text
3 Codes
4 Items
2 Events
```

The grid is compiled once. Then it runs three times. Between runs, Events can reconfigure the grid by rotating, shifting, swapping, or rolling back positions. Items modify Codes by position. Codes produce Output. After three Runs, the highest Output wins.

## Card types

- **Codes**, small ASCII program creatures, persistent, XP, levels
- **Items**, modules and tools, positional buffs, uses, burn out
- **Events**, one-shot grid reconfiguration actions

## Modes

- **Training**, solo highscore mode
- **Standard match**, LAN PvP without permanent Code loss
- **Hardcore match**, optional risk mode with destroyed Codes and better rewards

## Status

Design prototype. Rules and architecture are being captured first, then a Python MVP follows.

## Repo layout

```text
docs/                 rules, styleguide, design notes
cardsets/alpha_001/   first card set in YAML
src/cclash/           Python package, later
tests/                engine tests, later
```

## Naming

```text
cardsets/             game content / card data
src/cclash/cards/     Python logic for loading and rendering cards
```

## License

MIT, planned.
