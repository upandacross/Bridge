"""Tests for PlayerCardGenerator table/partner assignment in generate_player_cards.py.

These pin the *invariants* the card generator must always satisfy, since the
generated cards go to real players:

- every player sits at exactly one table per game;
- a table always has exactly 4 players;
- partners are mutual and never self;
- a player's "teammates" are the other 3 at the table (and include the partner);
- round 1's partners are deterministic (across-the-table: 1<->3, 2<->4 in a block);
- later rounds avoid repeating the previous round's partnerships.

No files, PDFs, or database are touched. Randomness is seeded per test.

Run:  uv run pytest test/test_player_cards.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from generate_player_cards import PlayerCardGenerator  # noqa: E402


@pytest.fixture(autouse=True)
def _seed_random():
    """Deterministic shuffles so failures are reproducible."""
    random.seed(1234)


def _assignments(games_data, player):
    return games_data[player]


# ---------------------------------------------------------------------------
# basic structure
# ---------------------------------------------------------------------------

def test_default_player_count_is_tables_times_four():
    g = PlayerCardGenerator(tables=5, games=3)
    assert g.num_players == 20
    assert g.players == list(range(1, 21))


def test_explicit_player_names_are_mapped():
    names = ["A", "B", "C", "D", "E", "F", "G", "H"]
    g = PlayerCardGenerator(tables=2, games=1, player_names=names)
    assert g.num_players == 8
    assert g.name_map[1] == "A"
    assert g.name_map[8] == "H"


def test_every_player_has_every_game():
    g = PlayerCardGenerator(tables=3, games=3)
    data = g.generate_cards()
    for p in g.players:
        games_seen = sorted(a["game"] for a in data[p])
        assert games_seen == [1, 2, 3]


def test_each_player_at_exactly_one_table_per_game():
    g = PlayerCardGenerator(tables=4, games=3)
    data = g.generate_cards()
    for p in g.players:
        per_game = {}
        for a in data[p]:
            per_game.setdefault(a["game"], []).append(a["table"])
        for game, tables in per_game.items():
            assert len(tables) == 1, f"player {p} at multiple tables in game {game}"


# ---------------------------------------------------------------------------
# table composition
# ---------------------------------------------------------------------------

def test_each_table_has_exactly_four_players_each_game():
    tables, games = 4, 3
    g = PlayerCardGenerator(tables=tables, games=games)
    data = g.generate_cards()

    for game in range(1, games + 1):
        by_table = {}
        for p in g.players:
            a = next(x for x in data[p] if x["game"] == game)
            by_table.setdefault(a["table"], set()).add(p)
        assert sorted(by_table) == list(range(1, tables + 1))
        for t, players in by_table.items():
            assert len(players) == 4, f"table {t} game {game} has {len(players)} players"


# ---------------------------------------------------------------------------
# partnerships
# ---------------------------------------------------------------------------

def test_partners_are_mutual_and_not_self():
    g = PlayerCardGenerator(tables=4, games=3)
    data = g.generate_cards()
    for p in g.players:
        for a in data[p]:
            partner = a["partner"]
            assert partner != p
            # partner must list p as its partner for the same game
            theirs = next(x for x in data[partner] if x["game"] == a["game"])
            assert theirs["partner"] == p


def test_partner_is_in_teammates():
    g = PlayerCardGenerator(tables=3, games=3)
    data = g.generate_cards()
    for p in g.players:
        for a in data[p]:
            assert a["partner"] in a["teammates"]


def test_teammates_are_the_other_three_at_the_table():
    g = PlayerCardGenerator(tables=3, games=3)
    data = g.generate_cards()
    for p in g.players:
        for a in data[p]:
            assert len(a["teammates"]) == 3
            assert p not in a["teammates"]
            same_table = {
                q for q in g.players
                if next(x for x in data[q] if x["game"] == a["game"])["table"] == a["table"]
            }
            assert set(a["teammates"]) == same_table - {p}


def test_round_one_partners_are_across_the_table():
    """Round 1 is deterministic: within each block of 4, 1<->3 and 2<->4."""
    g = PlayerCardGenerator(tables=3, games=2)
    data = g.generate_cards()
    for table_num in range(1, g.tables + 1):
        start = (table_num - 1) * 4 + 1
        block = [start, start + 1, start + 2, start + 3]
        r1 = {p: next(x for x in data[p] if x["game"] == 1) for p in block}
        assert r1[block[0]]["partner"] == block[2]
        assert r1[block[1]]["partner"] == block[3]
        assert r1[block[2]]["partner"] == block[0]
        assert r1[block[3]]["partner"] == block[1]


def test_later_rounds_avoid_repeating_previous_partnerships():
    g = PlayerCardGenerator(tables=4, games=3)
    data = g.generate_cards()
    for game in (2, 3):
        prev = {tuple(sorted((p, next(x for x in data[p] if x["game"] == game - 1)["partner"])))
                for p in g.players}
        cur = {tuple(sorted((p, next(x for x in data[p] if x["game"] == game)["partner"])))
               for p in g.players}
        assert not (prev & cur), f"game {game} repeats a game {game-1} partnership"


# ---------------------------------------------------------------------------
# naming / custom sizes
# ---------------------------------------------------------------------------

def test_single_table_single_game():
    g = PlayerCardGenerator(tables=1, games=1)
    data = g.generate_cards()
    assert set(data) == {1, 2, 3, 4}
    assert data[1][0]["partner"] == 3


def test_export_csv_writes_one_row_per_player_game(tmp_path):
    import csv as _csv
    g = PlayerCardGenerator(tables=2, games=2)
    g.generate_cards()
    out = tmp_path / "cards.csv"
    g.export_csv(str(out))
    with out.open(newline="") as fh:
        rows = list(_csv.reader(fh))
    assert rows[0] == ["Player", "Game", "Table", "Teammates"]
    # 8 players x 2 games = 16 data rows
    assert len(rows) - 1 == 16
