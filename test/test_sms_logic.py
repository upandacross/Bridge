"""Unit tests for the pure logic in send_bridge_sms.py.

These cover the decision-making that is easy to get wrong and costly when it
is (the script sends real SMS): audience selection, the always-call rules,
phone normalization, day/column selection, message filling, and the send-log
dedup. Nothing here touches the phone, the ODS sheets, or bridge.db.

Run:  uv run pytest test/test_sms_logic.py
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest

# The script is a top-level module (not a package), so put the project root on
# the path before importing it. Importing it also resolves the phone-mcp
# `kdeconnect` helper via sys.path, so that clone must be present.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import send_bridge_sms as sms  # noqa: E402


# ---------------------------------------------------------------------------
# normalize_phone
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("336-749-2690", "+13367492690"),
    ("(336) 749-2690", "+13367492690"),
    ("3367492690", "+13367492690"),
    ("1-336-749-2690", "+13367492690"),
    ("13367492690", "+13367492690"),
    ("  336.749.2690  ", "+13367492690"),
])
def test_normalize_phone_valid(raw, expected):
    assert sms.normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", [
    "",            # empty
    "12345",       # too short
    "23345678901",  # 11 digits not starting with 1
    "123456789012",  # too long
    "not a phone",
])
def test_normalize_phone_invalid(raw):
    assert sms.normalize_phone(raw) is None


# ---------------------------------------------------------------------------
# parse_always_call_note
# ---------------------------------------------------------------------------

def test_parse_note_extracts_and_cleans_name():
    assert sms.parse_always_call_note("Jane Always call Craver") == ("Jane Craver", True)
    assert sms.parse_always_call_note("Trudy Always call Smith") == ("Trudy Smith", True)


def test_parse_note_case_insensitive():
    assert sms.parse_always_call_note("Trudy always CALL Smith") == ("Trudy Smith", True)


def test_parse_note_absent_leaves_name_untouched():
    assert sms.parse_always_call_note("Milrie Lentz") == ("Milrie Lentz", False)
    assert sms.parse_always_call_note("Bren Letson") == ("Bren Letson", False)


# ---------------------------------------------------------------------------
# is_always_call
# ---------------------------------------------------------------------------

def test_is_always_call_case_and_space_insensitive():
    pool = {"Milrie Lentz", "Trudy Smith"}
    assert sms.is_always_call("milrie lentz", pool)
    assert sms.is_always_call("Milrie   Lentz", pool)
    assert sms.is_always_call("TRUDY SMITH", pool)


def test_is_always_call_negative():
    pool = {"Milrie Lentz"}
    assert not sms.is_always_call("Jane Craver", pool)


# ---------------------------------------------------------------------------
# parse_day_columns
# ---------------------------------------------------------------------------

def test_parse_day_columns_maps_days_to_indices():
    header = ["number", "First", "Last", "1", "8", "15", "22", "29"]
    assert sms.parse_day_columns(header) == {1: 3, 8: 4, 15: 5, 22: 6, 29: 7}


def test_parse_day_columns_ignores_non_numeric_header_cells():
    header = ["number", "First", "Last", "note", "3"]
    assert sms.parse_day_columns(header) == {3: 4}


# ---------------------------------------------------------------------------
# pick_day  (override path only — the date-anchored path is time-dependent)
# ---------------------------------------------------------------------------

def test_pick_day_override_returns_that_day():
    days = {1: 3, 8: 4, 15: 5}
    assert sms.pick_day(days, 15, 2026, 10) == 15


def test_pick_day_override_not_a_column_exits():
    with pytest.raises(SystemExit):
        sms.pick_day({1: 3}, 99, 2026, 10)


def test_pick_day_without_override_selects_next_upcoming(monkeypatch):
    """A sheet whose columns are all in the future picks the earliest."""
    days = {28: 3, 29: 4}
    # Freeze 'today' just before the sheet month so both columns are upcoming.
    real_date = datetime.date

    class _FrozenDate(real_date):
        @classmethod
        def today(cls):
            return real_date(2026, 10, 1)

    monkeypatch.setattr(sms.datetime, "date", _FrozenDate)
    assert sms.pick_day(days, None, 2026, 10) == 28


# ---------------------------------------------------------------------------
# month_from_filename
# ---------------------------------------------------------------------------

def test_month_from_filename_reads_month(monkeypatch):
    real_date = datetime.date

    class _FrozenDate(real_date):
        @classmethod
        def today(cls):
            return real_date(2026, 10, 8)

    monkeypatch.setattr(sms.datetime, "date", _FrozenDate)
    assert sms.month_from_filename(Path("Bridge Signup Thursday October.ods")) == (2026, 10)


def test_month_from_filename_rejects_nameless_file():
    with pytest.raises(SystemExit):
        sms.month_from_filename(Path("signup.ods"))


# ---------------------------------------------------------------------------
# message_hash / render_message
# ---------------------------------------------------------------------------

def test_message_hash_is_deterministic_and_short():
    h1 = sms.message_hash("hello")
    h2 = sms.message_hash("hello")
    assert h1 == h2
    assert len(h1) == 8
    assert h1 != sms.message_hash("hello!")


def test_render_message_substitutes_first():
    r = {"first": "Jane"}
    assert sms.render_message("Hi {first}, see you.", r) == "Hi Jane, see you."


def test_render_message_leaves_template_without_token():
    r = {"first": "Jane"}
    assert sms.render_message("Reminder: game on.", r) == "Reminder: game on."


# ---------------------------------------------------------------------------
# collect_declined  (audience selection, dedup, always-call flag)
# ---------------------------------------------------------------------------

HEADER = ["number", "First", "Last", "1", "8", "15"]
# Column index 5 == day 15, index 4 == day 8.
DAY15 = 5


def _rows():
    return [
        HEADER,
        ["336-111-0001", "Ada", "Attending", "✔", "x", "✔"],
        ["336-111-0002", "Don", "Declined", "✔", "✔", "x"],
        ["336-111-0003", "Jane", "Always call Craver", "✔", "✔", "✔"],
        ["336-111-0004", "Dup", "Share", "✔", "✔", "✔"],
        ["336-111-0004", "Dup2", "Share", "✔", "✔", "✔"],   # same number
        ["", "Aggregate", "Row", "12", "9", "12"],           # blank phone -> skipped
    ]


def test_collect_declined_default_audience_returns_declined():
    recips, invalid = sms.collect_declined(_rows(), 0, DAY15)
    names = {r["name"] for r in recips}
    assert "Don Declined" in names
    assert "Ada Attending" not in names


def test_collect_declined_attending_audience():
    recips, invalid = sms.collect_declined(_rows(), 0, DAY15, sms.MARK_ATTENDING)
    names = {r["name"] for r in recips}
    assert "Ada Attending" in names
    assert "Don Declined" not in names
    assert invalid == []


def test_collect_declined_flags_always_call_note():
    recips, _ = sms.collect_declined(_rows(), 0, DAY15, sms.MARK_ATTENDING)
    craver = next(r for r in recips if "Craver" in r["name"])
    assert craver["call_only"] is True
    assert craver["name"] == "Jane Craver"      # note stripped
    assert craver["first"] == "Jane"


def test_collect_declined_dedups_shared_phone():
    recips, _ = sms.collect_declined(_rows(), 0, DAY15, sms.MARK_ATTENDING)
    shares = [r for r in recips if r["normalized"] == "+13361110004"]
    assert len(shares) == 1                      # household gets one text


def test_collect_declined_skips_blank_phone_rows():
    recips, _ = sms.collect_declined(_rows(), 0, DAY15, sms.MARK_ATTENDING)
    assert all(r["normalized"] for r in recips)


# ---------------------------------------------------------------------------
# send log: write, load, dedup keyed on message hash
# ---------------------------------------------------------------------------

def test_log_send_then_load_roundtrip(tmp_path):
    log = tmp_path / "log.csv"
    rec = {"name": "Jane Doe", "normalized": "+13361110001"}
    h = sms.message_hash("hi")
    sms.log_send(log, h, rec, "sent")
    assert sms.load_sent_log(log, h) == {"+13361110001"}


def test_load_sent_log_scopes_to_message_hash(tmp_path):
    log = tmp_path / "log.csv"
    rec = {"name": "Jane Doe", "normalized": "+13361110001"}
    h1, h2 = sms.message_hash("first"), sms.message_hash("second")
    sms.log_send(log, h1, rec, "sent")
    assert sms.load_sent_log(log, h2) == set()   # different message -> nothing sent


def test_load_sent_log_missing_file_is_empty(tmp_path):
    assert sms.load_sent_log(tmp_path / "nope.csv", "deadbeef") == set()


# ---------------------------------------------------------------------------
# _row_cells  (ODS repeat handling) — build minimal ODS table-row XML
# ---------------------------------------------------------------------------

def _make_row(cells):
    """cells: list of (text, repeat). Builds a table-row Element."""
    ns = sms._NS_TABLE
    row = sms.ET.Element(ns + "table-row")
    for text, repeat in cells:
        cell = sms.ET.SubElement(row, ns + "table-cell")
        if repeat != 1:
            cell.set(ns + "number-columns-repeated", str(repeat))
        if text:
            p = sms.ET.SubElement(cell, sms._NS_TEXT + "p")
            p.text = text
    return row


def test_row_cells_expands_repeats():
    row = _make_row([("a", 1), ("b", 3)])
    assert sms._row_cells(row) == ["a", "b", "b", "b"]


def test_row_cells_trailing_blanks_stripped():
    row = _make_row([("a", 1), ("", 5)])
    assert sms._row_cells(row) == ["a"]
