# CLAUDE.md — cclash

Terminal-natives Grid-TCG. Python 3.11+. Status: Design-Phase, MVP-Engine kommt als Nächstes.

> Compile once. Reconfigure three times. Highest output wins.

## Vor jeder Code-Änderung lesen

- `docs/rules_v0_1.md` — Spielregeln
- `docs/architecture_v0_1.md` — Modul-Layout, MVP-Grenzen, Bauabfolge
- `docs/card_model.md` — Definition vs. Instance, Effekt- und Target-Sprache
- `docs/randomness_v0_1.md` — W6, Determinismus, Seed-Regeln
- `docs/networking_security.md` — host-authoritative, signed actions
- `docs/ascii_styleguide.md` — Karten-Grammatik, ist *nicht* Deko
- `docs/mvp_tasks.md` / `docs/roadmap.md` — was wann gebaut wird

## Architektur in einem Satz

```
YAML (data) → Loader → Registry → Effect Engine → Grid Engine → Run Engine → TUI / CLI
                                                                          → Storage
                                                                          → Network
```

Modul-Layout liegt unter `src/cclash/{cli,core,cards,game,storage,tui,network,utils}` und ist in `architecture_v0_1.md §1` festgeschrieben. Nicht ohne Grund verschieben.

## Karten-Daten

Karten-YAMLs liegen in `cardsets/<set_id>/{set,codes,items,events}.yaml`.

Der Ordner `cards/` ist *nicht* mehr in Verwendung. Nichts dort hinein schreiben oder daraus lesen. Falls du den Ordner siehst: ignorieren oder zur Löschung vorschlagen.

## Harte Invarianten — niemals brechen

1. **Effekte sind Daten.** Kein `eval`, kein `exec`, keine Code-Strings in YAML. Die Engine interpretiert eine Whitelist von `type:`-Werten (`modify_out`, `modify_stab`, `damage`, `prevent_damage`, `rotate_grid`, `shift_column`, `shift_row`, `outer_ring_rotate`, `swap_adjacent`, `rollback`).
2. **Engine ist deterministisch.** Same Input → same Output. Kein `time.time()`, kein ungeseedetes `random`, keine Reihenfolgen-Abhängigkeit von `dict`-Iterationen in der Effekt-Resolution.
3. **Random = W6, ein Stream pro Match.** Match-Seed aus `(host_player_id, client_player_id, match_id, cardset_hash)`. Jeder Roll wandert ins Run-Log. Keine Prozentzahlen, keine multiplen Würfel, keine Re-Rolls (siehe `randomness_v0_1.md §3`).
4. **Card Numbers sind stabil.** `CC-A001-###` ändert sich nie, auch wenn Name oder Stats sich ändern. Sie sind Diskussions- und Balance-Anker.
5. **Definition ≠ Instance.** Templates leben unter `cardsets/`, owned Copies unter Storage mit `instance_id`, `uses_remaining`, `xp`, `status`.
6. **Host-authoritative.** Clients senden Intentionen, nie Resultate. Nur der Host würfelt und mutiert State.
7. **Keine Secrets übers Netz.** Ein lokaler `private_key` verlässt die Maschine nie.

## MVP-Scope — bewusst NICHT bauen

Ohne explizites Go nicht anfangen mit:

- Trading
- Globalem Online-Multiplayer
- Crafting
- Komplexer Economy
- Voller TUI (Rich reicht, Textual später)
- Hardcore-Permanenz
- Daily-Claim-Rarity-Rolls (eigener Stream, später)

## Bauabfolge — nicht überspringen

1. **M1 grid** — `core/grid.py` + Tests für jede Reconfigure-Move
2. **M2 patterns** — `core/patterns.py` + Tests für `self/row/column/adjacent/diagonal/mirror/global`
3. **M3 card loader** — `cards/loader.py`, `cards/registry.py`, validiert eindeutige Numbers und IDs
4. **M4 effect interpreter** — `core/effects.py`, nur Whitelist-Typen
5. **M5 training engine** — `core/engine.py` + `game/training.py`, produziert RunLog
6. **M6 inspect CLI** — `cli/app.py`, `tui/inspect_view.py`
7. **M7 archive** — SQLite, Starter, Daily Claim, Item-Uses
8. **M8 LAN** — host / client / discovery / pairing / protocol

Tests-first für M1–M5. Engine-Logik ohne Tests landet nicht.

## Workflow

```bash
pip install -e ".[dev]"
python -m pytest                # alles
python -m pytest tests/test_grid.py -k rotate90
ruff check src tests
ruff format src tests
cclash                          # CLI-Entrypoint
```

Style: `ruff` mit `line-length = 100`, Python-3.11+-Features erlaubt (PEP-604-Unions, `match`, etc.).

## YAML-Konventionen für Karten

- Pflichtfelder: `number`, `id`, `name`, `type`, `rarity`, `pattern`, `ascii`, `text`, plus typ-spezifische Stats
- ASCII-Strings: Backslashes in YAML korrekt escapen (`\\`). Beim Editieren prüfen, dass die Zeilenbreite zum Inspect-Frame passt.
- Beim Hinzufügen einer Karte: `set.yaml.card_count` und `numbering.range` mitziehen.

## Stil im Code

- Keine Backwards-Compat-Shims, kein toter Code: das Projekt ist Pre-1.0, lieber sauber löschen statt deprecaten.
- Kommentare nur, wenn das *Warum* nicht-offensichtlich ist (z. B. Determinismus-Constraint, Reihenfolgen-Abhängigkeit). Niemals erklären *was* der Code tut.
- Effekt-Reihenfolge in einem Run ist fix: `Item Effects → Code Execution → Damage/Disable → Output Scoring`. Nicht durch Umsortieren „optimieren".
- Grid-Koordinaten: `A1..C3` (Zeile A/B/C, Spalte 1/2/3). Intern darf 0-indiziert sein, an der Grenze immer mappen.

## Wenn unsicher

- Lieber Frage stellen als Annahme treffen — die Specs sind dünn und werden gerade gebaut.
- Spec-Lücken nicht still im Code festschreiben; stattdessen Vorschlag in den passenden `docs/*.md`.
