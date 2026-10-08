"""Tests for the Database CRUD layer in database.py.

Each test gets a fresh SQLite database in the system temp directory (via the
``db`` fixture) — never the real ``bridge.db`` — so tests are isolated and safe
to run repeatedly. The schema is created by ``Database.connect()`` itself.

Run:  uv run pytest test/test_database.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database import Database  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path):
    """A connected Database backed by a throwaway temp file."""
    database = Database(db_path=str(tmp_path / "test.db"))
    database.connect()
    yield database
    database.close()


def _user(db, first="Ada", last="Lovelace", **kw):
    """Create a user with sensible, valid defaults; return its id."""
    kw.setdefault("phone", "336-000-0001")
    kw.setdefault("play_thursdays", True)
    return db.create_user(first, last, **kw)


# ---------------------------------------------------------------------------
# connect / schema
# ---------------------------------------------------------------------------

def test_connect_creates_schema(db):
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r["name"] for r in cursor.fetchall()}
    assert {"Users", "Games", "Attendance", "SQL_Report"} <= tables


def test_row_factory_returns_dict_rows(db):
    cursor = db.conn.cursor()
    cursor.execute("SELECT 1 AS one")
    assert cursor.fetchone()["one"] == 1


# ---------------------------------------------------------------------------
# create_user  (validation + happy path)
# ---------------------------------------------------------------------------

def test_create_user_returns_id_and_persists(db):
    uid = _user(db)
    assert isinstance(uid, int)
    assert db.get_user(uid)["first"] == "Ada"


def test_create_user_requires_first_and_last(db):
    with pytest.raises(ValueError):
        db.create_user("", "Last", phone="336-1", play_thursdays=True)
    with pytest.raises(ValueError):
        db.create_user("First", "", phone="336-1", play_thursdays=True)


def test_create_user_rejects_multiple_preferences(db):
    with pytest.raises(ValueError):
        _user(db, prefer_email=True, prefer_text=True)


def test_create_user_requires_a_contact_method(db):
    # No email, no phone, no preference -> error.
    with pytest.raises(ValueError):
        db.create_user("Ada", "Lovelace", play_thursdays=True)


def test_create_user_requires_a_play_day(db):
    with pytest.raises(ValueError):
        db.create_user("Ada", "Lovelace", phone="336-1")


def test_create_user_accepts_single_preference(db):
    uid = _user(db, prefer_text=True)
    assert db.get_user(uid)["prefer_text"] == 1


# ---------------------------------------------------------------------------
# lookups
# ---------------------------------------------------------------------------

def test_get_user_by_name(db):
    _user(db)
    assert db.get_user_by_name("Ada", "Lovelace")["first"] == "Ada"
    assert db.get_user_by_name("Nobody", "Here") is None


def test_get_user_by_phone(db):
    _user(db, phone="336-555-1234")
    assert db.get_user_by_phone("336-555-1234")["last"] == "Lovelace"
    assert db.get_user_by_phone("000") is None


def test_get_user_missing_returns_none(db):
    assert db.get_user(9999) is None


def test_get_all_users_active_only_filters(db):
    _user(db, "Active", "One", active=True)
    _user(db, "Inactive", "Two", active=False)
    active = db.get_all_users(active_only=True)
    everyone = db.get_all_users(active_only=False)
    assert {u["first"] for u in active} == {"Active"}
    assert {u["first"] for u in everyone} == {"Active", "Inactive"}


def test_search_users_matches_name_and_phone(db):
    _user(db, "Ada", "Lovelace", phone="336-555-0001")
    _user(db, "Grace", "Hopper", phone="336-555-0002")
    assert [u["last"] for u in db.search_users("love")] == ["Lovelace"]
    assert [u["last"] for u in db.search_users("0002")] == ["Hopper"]


def test_search_users_blank_returns_all_active(db):
    _user(db, "Ada", "Lovelace")
    _user(db, "Grace", "Hopper")
    assert len(db.search_users("")) == 2


# ---------------------------------------------------------------------------
# update_user / delete_user
# ---------------------------------------------------------------------------

def test_update_user_changes_fields(db):
    uid = _user(db)
    assert db.update_user(uid, first="Augusta") is True
    assert db.get_user(uid)["first"] == "Augusta"


def test_update_user_returns_false_for_no_valid_fields(db):
    uid = _user(db)
    assert db.update_user(uid, nonsense="x") is False


def test_update_user_rejects_multiple_preferences(db):
    uid = _user(db)
    with pytest.raises(ValueError):
        db.update_user(uid, prefer_email=True, prefer_phone=True)


def test_update_user_missing_id_returns_false(db):
    assert db.update_user(9999, first="Ghost") is False


def test_delete_user(db):
    uid = _user(db)
    assert db.delete_user(uid) is True
    assert db.get_user(uid) is None
    assert db.delete_user(uid) is False   # already gone


# ---------------------------------------------------------------------------
# games
# ---------------------------------------------------------------------------

def test_get_or_create_month_thursdays_are_thursdays(db):
    result = db.get_or_create_month(10, 2026)
    assert result["thursdays"], "October 2026 should have Thursdays"
    # Every generated date must actually be a Thursday.
    import datetime
    for d in result["thursdays"]:
        dt = datetime.datetime.strptime(d, "%Y%m%d").date()
        assert dt.weekday() == 3
    for d in result["fridays"]:
        dt = datetime.datetime.strptime(d, "%Y%m%d").date()
        assert dt.weekday() == 4


def test_get_or_create_month_is_idempotent(db):
    first = db.get_or_create_month(10, 2026)
    second = db.get_or_create_month(10, 2026)
    assert first["thursdays"] == second["thursdays"]
    # No duplicate Games rows.
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) AS n FROM Games WHERE day_type='Thursday'")
    assert cursor.fetchone()["n"] == len(first["thursdays"])


def test_get_or_create_month_returns_compat_strings(db):
    result = db.get_or_create_month(10, 2026)
    assert result["thursdays_str"] == ",".join(result["thursdays"])


def test_get_game_id_and_info_by_date(db):
    result = db.get_or_create_month(10, 2026)
    date_str = result["thursdays"][0]
    gid = db.get_game_id_by_date(date_str)
    assert isinstance(gid, int)
    info = db.get_game_info_by_date(date_str)
    assert info["day_type"] == "Thursday"
    assert db.get_game_id_by_date("19000101") is None


# ---------------------------------------------------------------------------
# attendance
# ---------------------------------------------------------------------------

def test_get_or_create_attendance_defaults_then_returns_existing(db):
    uid = _user(db)
    gid = db.get_game_id_by_date(db.get_or_create_month(10, 2026)["thursdays"][0])
    assert db.get_or_create_attendance(uid, gid) == "Present"
    # Second call returns the stored value, not a new default.
    assert db.get_or_create_attendance(uid, gid, default_status="Absent") == "Present"


def test_update_attendance_creates_then_updates(db):
    uid = _user(db)
    gid = db.get_game_id_by_date(db.get_or_create_month(10, 2026)["thursdays"][0])
    aid = db.update_attendance(uid, gid, "Absent")
    assert isinstance(aid, int)
    assert db.get_attendance_status(uid, gid) == "Absent"
    # Update the same row.
    db.update_attendance(uid, gid, "Present")
    assert db.get_attendance_status(uid, gid) == "Present"


def test_update_attendance_rejects_bad_status(db):
    uid = _user(db)
    gid = db.get_game_id_by_date(db.get_or_create_month(10, 2026)["thursdays"][0])
    with pytest.raises(ValueError):
        db.update_attendance(uid, gid, "Maybe")


def test_get_attendance_status_missing_returns_none(db):
    uid = _user(db)
    gid = db.get_game_id_by_date(db.get_or_create_month(10, 2026)["thursdays"][0])
    assert db.get_attendance_status(uid, gid) is None


def test_attendance_unique_constraint(db):
    """One attendance row per (user, game) — the schema enforces it."""
    import sqlite3
    uid = _user(db)
    gid = db.get_game_id_by_date(db.get_or_create_month(10, 2026)["thursdays"][0])
    db.update_attendance(uid, gid, "Present")
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute(
            "INSERT INTO Attendance (user_id, game_id, status) VALUES (?, ?, ?)",
            (uid, gid, "Absent"),
        )


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------

def test_close_is_idempotent(tmp_path):
    database = Database(db_path=str(tmp_path / "t.db"))
    database.connect()
    database.close()
    database.close()          # must not raise
    assert database.conn is None
