"""End-to-end tests for the playable CLI loop: compile → training → log."""

from __future__ import annotations

import json
from pathlib import Path

from cclash.cli.app import main

REPO = Path(__file__).resolve().parents[1]
CARDSETS = str(REPO / "cardsets")

PLACES = [
    "A1=cronling",
    "A2=docker",
    "A3=legacy_brick",
    "B1=tmux",
    "B2=null_imp",
    "B3=overclock_chip",
    "C1=rotate90",
    "C2=firewall_cloak",
    "C3=outer_ring",
]


def _place_args() -> list[str]:
    out: list[str] = []
    for p in PLACES:
        out.extend(["--place", p])
    return out


def test_compile_writes_grid_file(tmp_path, capsys):
    grid_file = tmp_path / "grid.json"
    rc = main(["--cardsets", CARDSETS, "compile", *_place_args(), "--out", str(grid_file)])
    assert rc == 0
    data = json.loads(grid_file.read_text())
    assert data["cells"]["A1"] == "cronling"
    assert len(data["cells"]) == 9
    assert "Grid saved" in capsys.readouterr().out


def test_compile_rejects_bad_loadout(tmp_path, capsys):
    places = [p if not p.endswith("cronling") else "A1=docker" for p in PLACES]
    args = []
    for p in places:
        args.extend(["--place", p])
    rc = main(["--cardsets", CARDSETS, "compile", *args, "--out", str(tmp_path / "g.json")])
    assert rc == 1
    out = capsys.readouterr().out
    assert "error" in out


def test_training_plays_saved_grid_and_logs_result(tmp_path, capsys):
    grid_file = tmp_path / "grid.json"
    log_file = tmp_path / "log.jsonl"
    assert main(["--cardsets", CARDSETS, "compile", *_place_args(), "--out", str(grid_file)]) == 0
    capsys.readouterr()

    rc = main(
        [
            "--cardsets",
            CARDSETS,
            "training",
            "--grid",
            str(grid_file),
            "--match-id",
            "test-1",
            "--auto",
            "--log-file",
            str(log_file),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "Run 1" in out
    assert "Final:" in out
    assert "New highscore" in out

    entries = [json.loads(line) for line in log_file.read_text().splitlines()]
    assert len(entries) == 1
    assert entries[0]["match_id"] == "test-1"
    assert entries[0]["total"] > 0
    assert entries[0]["grid"]["A1"] == "cronling"


def test_training_same_match_id_replays_identically(tmp_path, capsys):
    grid_file = tmp_path / "grid.json"
    log_file = tmp_path / "log.jsonl"
    assert main(["--cardsets", CARDSETS, "compile", *_place_args(), "--out", str(grid_file)]) == 0
    base = [
        "--cardsets",
        CARDSETS,
        "training",
        "--grid",
        str(grid_file),
        "--match-id",
        "replay",
        "--auto",
        "--log-file",
        str(log_file),
    ]
    capsys.readouterr()
    assert main(base) == 0
    first = capsys.readouterr().out
    assert main(base) == 0
    second = capsys.readouterr().out
    # identical match log; only the highscore trailer may differ
    assert first.split("Final:")[0] == second.split("Final:")[0]


def test_training_without_grid_points_to_compile(tmp_path, capsys):
    rc = main(
        ["--cardsets", CARDSETS, "training", "--grid", str(tmp_path / "missing.json"), "--auto"]
    )
    assert rc == 1
    assert "cclash compile" in capsys.readouterr().out


def test_training_sample_still_works(tmp_path, capsys):
    rc = main(
        ["--cardsets", CARDSETS, "training", "--sample", "--log-file", str(tmp_path / "log.jsonl")]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "Final: " in out
    assert "Reconfigure 1: play" in out


def test_log_shows_highscore(tmp_path, capsys):
    grid_file = tmp_path / "grid.json"
    log_file = tmp_path / "log.jsonl"
    assert main(["--cardsets", CARDSETS, "compile", *_place_args(), "--out", str(grid_file)]) == 0
    for match_id in ("m1", "m2"):
        assert (
            main(
                [
                    "--cardsets",
                    CARDSETS,
                    "training",
                    "--grid",
                    str(grid_file),
                    "--match-id",
                    match_id,
                    "--auto",
                    "--log-file",
                    str(log_file),
                ]
            )
            == 0
        )
    capsys.readouterr()

    rc = main(["log", "--log-file", str(log_file)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Highscore:" in out
    assert "m1" in out and "m2" in out


def test_log_with_no_entries(tmp_path, capsys):
    rc = main(["log", "--log-file", str(tmp_path / "empty.jsonl")])
    assert rc == 0
    assert "No training runs" in capsys.readouterr().out
