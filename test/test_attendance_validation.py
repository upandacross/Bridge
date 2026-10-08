"""Tests for the attendance schema validation.

Two layers:

- **Unit tests** for ``validate_attendance_record`` — a pure function, fast,
  no database. Run by default.
- **Integration tests** (marked ``integration``) for ``run_validation`` — they
  read the real ``bridge.db`` and assert on the returned structure. Deselected
  by default; run with ``uv run pytest -m integration``.

The standalone script ``test_attendance_schema.py`` (which also writes
``attendance_validation.csv``) remains the manual / n8n entry point and is left
untouched.

Run:   uv run pytest test/test_attendance_validation.py            # unit only
       uv run pytest -m integration test/test_attendance_validation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "test"))

from test_attendance_schema import run_validation, validate_attendance_record  # noqa: E402


# ---------------------------------------------------------------------------
# Unit tests: validate_attendance_record
# ---------------------------------------------------------------------------

def _record(**overrides) -> dict:
    """A valid record, with any field overridable per test."""
    base = {
        "Name": "Lentz, Milrie",
        "Phone": "336-765-1902",
        "Email": "",
        "Preference": "phone",
        "Date": "20261015",
        "Day Type": "Thursday",
        "Attendance": "Present",
    }
    base.update(overrides)
    return base


def test_valid_record_has_no_errors():
    assert validate_attendance_record(_record(), "20261015") == []


@pytest.mark.parametrize("preference", ["email", "text", "phone", "none", "PHONE", "Email"])
def test_all_valid_preferences_accepted(preference):
    assert validate_attendance_record(_record(Preference=preference), "20261015") == []


@pytest.mark.parametrize("day_type", ["Thursday", "Friday"])
def test_all_valid_day_types_accepted(day_type):
    assert validate_attendance_record(_record(**{"Day Type": day_type}), "20261015") == []


@pytest.mark.parametrize("attendance", ["Present", "Absent", "Unknown", "present", "ABSENT"])
def test_all_valid_attendance_values_accepted(attendance):
    assert validate_attendance_record(_record(Attendance=attendance), "20261015") == []


def test_empty_name_is_flagged():
    errors = validate_attendance_record(_record(Name="   "), "20261015")
    assert any("Name is empty" in e for e in errors)


def test_invalid_preference_is_flagged():
    errors = validate_attendance_record(_record(Preference="carrier-pigeon"), "20261015")
    assert any("Invalid preference" in e for e in errors)


def test_invalid_day_type_is_flagged():
    errors = validate_attendance_record(_record(**{"Day Type": "Monday"}), "20261015")
    assert any("Invalid day type" in e for e in errors)


def test_invalid_attendance_is_flagged():
    errors = validate_attendance_record(_record(Attendance="Maybe"), "20261015")
    assert any("Invalid attendance" in e for e in errors)


@pytest.mark.parametrize("bad_date", ["2026-10-15", "2026101", "202610155", "abcdefgh", ""])
def test_malformed_date_is_flagged(bad_date):
    errors = validate_attendance_record(_record(), bad_date)
    assert any("Invalid date format" in e for e in errors)


def test_multiple_errors_accumulate():
    errors = validate_attendance_record(
        _record(Name="", Preference="bogus", **{"Day Type": "Monday"}), "bad")
    # Empty name, bad preference, bad day type, bad date -> at least 4.
    assert len(errors) >= 4


# ---------------------------------------------------------------------------
# Integration tests: run_validation against the real bridge.db
# ---------------------------------------------------------------------------

pytestmark_integration = pytest.mark.integration


@pytest.mark.integration
def test_run_validation_reports_structure():
    result = run_validation()
    assert set(result) >= {"start_time", "db_path", "validations", "errors", "summary"}
    assert isinstance(result["validations"], list)
    assert isinstance(result["summary"], dict)


@pytest.mark.integration
def test_run_validation_finds_database():
    result = run_validation()
    # bridge.db must exist in the project root; a missing file is recorded
    # in errors rather than raised.
    assert not any("Database file not found" in e for e in result["errors"])


@pytest.mark.integration
def test_run_validation_game_counts_are_consistent():
    result = run_validation()
    summary = result["summary"]
    assert summary["valid_games"] + summary["invalid_games"] == summary["total_games"]
    assert summary["total_games"] == len(result["validations"])


@pytest.mark.integration
def test_run_validation_all_games_valid():
    """The committed data should validate cleanly."""
    result = run_validation()
    assert result["summary"]["total_errors"] == 0, result["errors"][:5]
    assert result["summary"]["invalid_games"] == 0
