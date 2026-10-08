#!/usr/bin/env python3
"""Send an SMS to bridge players based on the Thursday signup sheet.

Reads the Thursday signup spreadsheet (ODS), picks a game-day column, and
texts every player whose mark matches the chosen audience. In this sheet
``x`` means "not attending" (declined) and ``✔`` means "attending".

By default the audience is the players marked ``✔`` (attending) -- a
"see you there" style message. Pass ``--audience declined`` to instead text
the players marked ``x`` (e.g. a "confirming you won't be there" note).

Sending goes through the paired phone's cellular line via KDE Connect
(``kdeconnect-cli``), reusing the ``KDEConnect`` helper from the shared
``phone-mcp`` repo (``~/Home/Projects/phone-mcp``).

Day selection:
  By default the script picks the smallest day-of-month in the header that
  is >= today, i.e. the next upcoming game. Run on the 6th, 7th, or 8th and
  it selects the 8th. Use --day to force a specific column.

Always-call (do not text):
  Some players prefer a phone call over SMS. Two signals mark them:
    1. An "Always call X" note in the sheet's Last column (e.g.
       "Trudy | Always call Smith"). These rows are detected automatically.
    2. The ALWAYS_CALL set of real names (default: Milrie Lentz, Trudy
       Smith), matched case-insensitively against "First Last".
  --always-call NAMES adds extra names to the built-in set;
  --always-call-replace treats the given names as the complete set.
  These players are excluded from the SMS and listed separately under
  "call these instead". Use --include-always-call to text them anyway.

Send log / resending:
  A CSV send log keys on the message hash, so re-running the same message
  skips phones already texted. Use --force to ignore the log for a run and
  re-send to everyone selected.

Safety:
  A phone-link check runs first by default: it reports the KDE Connect
  device and battery. Without a message the run stops there (link check
  only). With a message, dry-run continues to print the recipient list even
  if the link is down; execute mode aborts if the phone is unreachable.
  Pass --check-phone no to skip the check and proceed.

  Dry-run by default (prints recipients without sending). Use --execute to
  actually send. A CSV send log keys on the message hash so re-runs skip
  phones already texted. Phone numbers are normalized to E.164 and
  deduplicated, so a household sharing one number gets a single text.

kdeconnect-cli is fire-and-forget: "sent" means KDE Connect accepted the
message, not that the carrier delivered it.

Usage examples:
    # Check the phone link only (also the default when you omit the flag)
    python send_bridge_sms.py --check-phone yes

    # Dry-run: who would be texted for the next game
    python send_bridge_sms.py --check-phone no \
        --message "Hi {first}, confirming you won't be at bridge on Oct 8. - Bren"

    # Force a specific day column and send
    python send_bridge_sms.py --check-phone no --day 15 \
        --message "Hi {first}, confirming you won't be at bridge on Oct 15. - Bren" --execute

    # Send to everyone, including the always-call players
    python send_bridge_sms.py --check-phone no \
        --message "..." --include-always-call --execute
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import os
import random
import re
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE_DEFAULT = SCRIPT_DIR / "bridge_sms_log.csv"

# Signup sheets are named "Bridge Signup Thursday <Month>.ods". The script
# discovers the file for the current month unless --file is given.
ODS_GLOB = "Bridge Signup Thursday *.ods"
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def discover_sheet(script_dir: Path) -> Path:
    """Find this month's signup sheet, erroring if ambiguous or missing."""
    month = MONTH_NAMES[datetime.date.today().month - 1]
    pattern = f"Bridge Signup Thursday {month}*.ods"
    matches = sorted(script_dir.glob(pattern))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        available = sorted(f.name for f in script_dir.glob(ODS_GLOB))
        raise SystemExit(
            f"No signup sheet found for {month} (looked for {pattern!r}). "
            f"Use --file to specify one. Available: {available}"
        )
    raise SystemExit(
        f"Multiple signup sheets match {month}: "
        f"{[m.name for m in matches]}. Use --file to pick one."
    )

# Players who prefer a phone call over SMS. Matched case-insensitively
# against "First Last". Edit here or override with --always-call.
ALWAYS_CALL: set[str] = {"Milrie Lentz", "Trudy Smith"}

# KDE Connect helper lives in the shared phone-mcp clone at ~/Home/Projects.
# Override with the PHONE_MCP_DIR environment variable if it moves.
PHONE_MCP_DIR = Path(os.environ.get(
    "PHONE_MCP_DIR", Path.home() / "Home/Projects/phone-mcp"))
sys.path.insert(0, str(PHONE_MCP_DIR))
from kdeconnect import KDEConnect  # noqa: E402

# ODS XML namespaces.
_NS_TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
_NS_TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"

# Marks in a day column. "x" means declined, "✔" means attending.
MARK_DECLINED = {"x", "X"}
MARK_ATTENDING = {"✔"}
# Audience -> the set of marks that select a recipient.
AUDIENCE_MARKS = {
    "declined": MARK_DECLINED,
    "attending": MARK_ATTENDING,
}


# ---------------------------------------------------------------------------
# Spreadsheet parsing
# ---------------------------------------------------------------------------

def _cell_text(cell: ET.Element) -> str:
    """Extract the visible text of a table cell."""
    parts = ["".join(p.itertext()) for p in cell.iter(_NS_TEXT + "p")]
    return " ".join(p for p in parts if p).strip()


def _row_cells(row: ET.Element) -> list[str]:
    """Expand a table-row into a list of cell strings, honoring repeats."""
    out: list[str] = []
    for cell in row.iter(_NS_TABLE + "table-cell"):
        repeat = int(cell.get(_NS_TABLE + "number-columns-repeated", "1"))
        text = _cell_text(cell)
        out.extend([text] * min(repeat, 64))
    while out and out[-1] == "":
        out.pop()
    return out


def read_sheet(ods_path: Path) -> list[list[str]]:
    """Return the first non-empty sheet of an ODS as a list of rows."""
    if not ods_path.exists():
        raise SystemExit(f"Spreadsheet not found: {ods_path}")
    with zipfile.ZipFile(ods_path) as zf:
        root = ET.fromstring(zf.read("content.xml"))

    for table in root.iter(_NS_TABLE + "table"):
        rows = [_row_cells(r) for r in table.iter(_NS_TABLE + "table-row")]
        rows = [r for r in rows if r]
        if rows:
            return rows
    raise SystemExit(f"No data found in {ods_path}")


def find_header(rows: list[list[str]]) -> int:
    """Find the header row: the one whose first cell is 'number'.

    Handles the October layout (header at row 0) and the September layout
    (title block above the header).
    """
    for i, row in enumerate(rows):
        if row and row[0].strip().lower() == "number":
            return i
    raise SystemExit(
        "Could not find a header row (expected first cell to be 'number')."
    )


def month_from_filename(ods_path: Path) -> tuple[int, int]:
    """Return (year, month) for a sheet named 'Bridge Signup Thursday <Month>.ods'.

    Only the month comes from the filename; the year is chosen as the
    occurrence nearest today so a December sheet opened in early January
    still anchors to the previous December.
    """
    name = ods_path.name
    month_num = None
    for i, m in enumerate(MONTH_NAMES, start=1):
        if m.lower() in name.lower():
            month_num = i
            break
    if month_num is None:
        raise SystemExit(
            f"Could not determine the month from filename {name!r}. "
            f"Rename it to include a month, e.g. "
            f"'Bridge Signup Thursday November.ods'."
        )

    today = datetime.date.today()
    year = today.year
    # Anchor to the occurrence of this month nearest to today:
    # a month "ahead" by more than ~6 months is really the previous year's.
    month_delta = month_num - today.month
    if month_delta > 6:
        year -= 1
    elif month_delta < -6:
        year += 1
    return year, month_num


def parse_day_columns(header: list[str]) -> dict[int, int]:
    """Map day-of-month -> column index for the numeric header cells."""
    days: dict[int, int] = {}
    for idx, cell in enumerate(header):
        m = re.fullmatch(r"\s*(\d{1,2})\s*", cell)
        if m:
            days[int(m.group(1))] = idx
    return days


def pick_day(days: dict[int, int], override: int | None,
             year: int, month: int) -> int:
    """Return the day-of-month to use, erroring if it is not a column.

    Header days are anchored to the sheet's (year, month) so the comparison
    is between real dates, not bare day numbers. This handles games near a
    month boundary, e.g. a November sheet run on Oct 30 correctly selects
    Nov 5.
    """
    if override is not None:
        if override not in days:
            raise SystemExit(
                f"--day {override} is not a column. "
                f"Available days: {sorted(days)}"
            )
        return override

    today = datetime.date.today()
    sheet_start = datetime.date(year, month, 1)
    # Error if the sheet is a stale month (before the current month).
    if (year, month) < (today.year, today.month):
        raise SystemExit(
            f"Sheet is for {MONTH_NAMES[month - 1]} {year}, which is before "
            f"the current month ({MONTH_NAMES[today.month - 1]} {today.year}). "
            f"Pass --file to select the correct sheet."
        )

    dated = sorted((datetime.date(year, month, d), d) for d in days)
    upcoming = [d for dt, d in dated if dt >= today]
    if not upcoming:
        raise SystemExit(
            f"No game day on or after today ({today.isoformat()}). "
            f"Available days: {sorted(days)}. Use --day to force one."
        )
    return upcoming[0]


# ---------------------------------------------------------------------------
# Recipients
# ---------------------------------------------------------------------------

def parse_always_call_note(name: str) -> tuple[str, bool]:
    """Split an "Always call X" note out of a name.

    The signup sheet sometimes stores a contact note in the Last column,
    e.g. "Trudy | Always call Smith". Returns (clean_name, flagged) where
    clean_name drops the note ("Trudy Smith") and flagged is True when the
    note was present. The note means: do not text, phone instead.
    """
    m = re.search(r"always\s+call\s+(.*)$", name, flags=re.IGNORECASE)
    if not m:
        return name, False
    clean = (name[:m.start()] + m.group(1)).strip()
    return re.sub(r"\s+", " ", clean), True

def normalize_phone(phone: str) -> str | None:
    """Normalize a US phone number to E.164 (+1XXXXXXXXXX)."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return None


def collect_declined(rows: list[list[str]], header_idx: int,
                     day_col: int,
                     marks: set[str] = MARK_DECLINED) -> tuple[list[dict], list[dict]]:
    """Return (recipients, invalid-phone rows) with dedup applied.

    ``marks`` selects the audience: MARK_DECLINED (default) or MARK_ATTENDING.
    Recipients are deduplicated by normalized phone so a shared household
    number gets a single text.
    """
    recipients: list[dict] = []
    invalid: list[dict] = []
    seen: set[str] = set()

    for row in rows[header_idx + 1:]:
        if day_col >= len(row):
            continue
        mark = row[day_col].strip()
        if mark not in marks:
            continue
        phone_raw = row[0].strip() if row else ""
        if not phone_raw:
            continue  # skip aggregate / blank rows

        first = row[1].strip() if len(row) > 1 else ""
        last = row[2].strip() if len(row) > 2 else ""
        name = f"{first} {last}".strip() or "(unknown)"
        name, note_flag = parse_always_call_note(name)
        if note_flag:
            first = name.split(" ")[0] if name else first

        normalized = normalize_phone(phone_raw)
        if normalized is None:
            invalid.append({"name": name, "phone": phone_raw})
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        recipients.append({
            "name": name,
            "first": first or name,
            "last": last,
            "phone": phone_raw,
            "normalized": normalized,
            "call_only": note_flag,
        })
    return recipients, invalid


def is_always_call(name: str, always_call: set[str]) -> bool:
    """Case-insensitive membership test on 'First Last'."""
    key = " ".join(name.split()).lower()
    return key in {" ".join(a.split()).lower() for a in always_call}


# ---------------------------------------------------------------------------
# Send log (deduplication across runs)
# ---------------------------------------------------------------------------

def message_hash(message: str) -> str:
    return hashlib.md5(message.encode()).hexdigest()[:8]


def load_sent_log(log_path: Path, msg_hash: str) -> set[str]:
    sent: set[str] = set()
    if not log_path.exists():
        return sent
    with log_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("message_hash") == msg_hash and row.get("phone"):
                sent.add(row["phone"])
    return sent


def log_send(log_path: Path, msg_hash: str, recipient: dict, status: str) -> None:
    write_header = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if write_header:
            writer.writerow([
                "timestamp", "message_hash", "name", "phone", "status",
            ])
        writer.writerow([
            datetime.datetime.now().isoformat(timespec="seconds"),
            msg_hash,
            recipient["name"],
            recipient["normalized"],
            status,
        ])


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------

def render_message(template: str, recipient: dict) -> str:
    """Fill {first} if present; otherwise return the template verbatim."""
    return template.replace("{first}", recipient["first"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Text bridge players selected from the signup game day.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--message", default=None,
                        help="SMS text; {first} is replaced per recipient "
                             "(required unless --check-phone no is used)")
    parser.add_argument("--file", "--ods", dest="ods", type=Path, default=None,
                        help="Signup spreadsheet ODS. Defaults to the current "
                             "month's file (e.g. 'Bridge Signup Thursday "
                             "November.ods'); errors if none or several match. "
                             "(--ods is an accepted alias.)")
    parser.add_argument("--day", type=int, default=None,
                        help="Force a day-of-month column (default: next upcoming)")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="SMS per batch (default: 10)")
    parser.add_argument("--sleep-min", type=float, default=5,
                        help="Min seconds between batches (default: 5)")
    parser.add_argument("--sleep-max", type=float, default=7,
                        help="Max seconds between batches (default: 7)")
    parser.add_argument("--always-call", nargs="*", default=None,
                        help="Extra names to skip as always-call (adds to "
                             "the built-in set; use --always-call-replace to "
                             "override it entirely)")
    parser.add_argument("--always-call-replace", action="store_true",
                        help="Treat --always-call as the full set, replacing "
                             "the built-in defaults")
    parser.add_argument("--force", action="store_true",
                        help="Ignore the send log for this run and re-send to "
                             "everyone selected, even phones already texted "
                             "with this message")
    parser.add_argument("--include-always-call", action="store_true",
                        help="Send to always-call players too")
    parser.add_argument("--audience", choices=["declined", "attending"],
                        default="attending",
                        help="Who to text: players marked '✔' (attending, "
                             "default) or 'x' (declined)")
    parser.add_argument("--log-file", type=Path, default=LOG_FILE_DEFAULT,
                        help=f"Send log CSV (default: {LOG_FILE_DEFAULT.name})")
    parser.add_argument("--execute", action="store_true",
                        help="Actually send SMS. Without this flag the script "
                             "runs in dry-run mode (prints recipients, sends "
                             "nothing).")
    parser.add_argument("--check-phone", choices=["yes", "no"], default="yes",
                        help="Check KDE Connect phone link and exit before any "
                             "send. Runs by default; pass 'no' to skip "
                             "(default: yes)")
    args = parser.parse_args()

    if args.sleep_min > args.sleep_max:
        sys.exit("--sleep-min must be <= --sleep-max")

    # --- Phone link check (runs by default) ---
    if args.check_phone == "yes":
        kc = KDEConnect()
        status = kc.status()
        reachable = bool(status.get("reachable"))
        print(f"KDE Connect reachable: {reachable}")
        print(f"  device: {status.get('name', 'unknown')}")
        print(f"  battery: {status.get('battery', {}).get('charge', '?')}%")
        if err := status.get("error"):
            print(f"  error: {err}")
        print("Note: this confirms the desktop<->phone link, NOT cellular "
              "service or carrier delivery.")
        print()
        # Only the check was requested (no message) -> stop here.
        if not args.message:
            return
        # In execute mode the phone must be reachable; dry-run continues
        # regardless so the recipient list is still shown.
        if args.execute and not reachable:
            sys.exit(f"Phone not reachable via KDE Connect: "
                     f"{status.get('error', 'unknown')}")

    # Past the check: a message is required to build the send.
    if not args.message:
        sys.exit("--message is required (unless --check-phone yes is used)")

    if args.always_call is None:
        always_call = set(ALWAYS_CALL)
    elif args.always_call_replace:
        always_call = set(args.always_call)
    else:
        always_call = set(ALWAYS_CALL) | set(args.always_call)

    # --- Parse the sheet and select the day ---
    ods_path = args.ods or discover_sheet(SCRIPT_DIR)
    rows = read_sheet(ods_path)
    header_idx = find_header(rows)
    days = parse_day_columns(rows[header_idx])
    if not days:
        raise SystemExit("No day columns found in the header.")
    year, month = month_from_filename(ods_path)
    day = pick_day(days, args.day, year, month)
    day_col = days[day]

    recipients, invalid = collect_declined(
        rows, header_idx, day_col, AUDIENCE_MARKS[args.audience])

    # --- Split out always-call players ---
    def _call_only(r: dict) -> bool:
        return r.get("call_only", False) or is_always_call(r["name"], always_call)

    always_call_hits = [r for r in recipients if _call_only(r)]
    if not args.include_always_call:
        recipients = [r for r in recipients if not _call_only(r)]

    # --- Dedup against the send log ---
    msg_hash = message_hash(args.message)
    if args.force:
        sent_phones: set[str] = set()
    else:
        sent_phones = load_sent_log(args.log_file, msg_hash)
    already = [r for r in recipients if r["normalized"] in sent_phones]
    recipients = [r for r in recipients if r["normalized"] not in sent_phones]

    # --- Report the plan ---
    print(f"Spreadsheet: {ods_path}")
    print(f"Header row: {header_idx}, day column: {day} (col {day_col})")
    print(f"Message: {args.message!r}")
    print(f"Message hash: {msg_hash}")
    print(f"Log file: {args.log_file}")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY-RUN'}")
    print()
    print(f"Recipients ({len(recipients)}):")
    for r in recipients:
        print(f"  {r['name']:30s}  {r['normalized']}")
    if already:
        print(f"\nAlready texted (skipped from log): {len(already)}")
    if not args.include_always_call and always_call_hits:
        print(f"\nCall these instead ({len(always_call_hits)}):")
        for r in always_call_hits:
            print(f"  {r['name']:30s}  {r['phone']}")
    if invalid:
        print(f"\nInvalid phones (skipped): {len(invalid)}")
        for r in invalid:
            print(f"  {r['name']:30s}  {r['phone']}")

    print()
    if not recipients:
        print("No recipients to text. Nothing to do.")
        return
    if not args.execute:
        print("(dry-run - use --execute to send SMS)")
        return

    # --- Verify KDE Connect before sending ---
    kc = KDEConnect()
    status = kc.status()
    if not status.get("reachable"):
        sys.exit(f"Phone not reachable via KDE Connect: "
                 f"{status.get('error', 'unknown')}")
    print(f"Phone: {status.get('name', 'unknown')} "
          f"(battery: {status.get('battery', {}).get('charge', '?')}%)")
    print()

    # --- Send in batches ---
    total_batches = (len(recipients) + args.batch_size - 1) // args.batch_size
    sent_count = fail_count = 0

    for i in range(0, len(recipients), args.batch_size):
        batch = recipients[i:i + args.batch_size]
        batch_num = i // args.batch_size + 1
        print(f"--- Batch {batch_num}/{total_batches} ({len(batch)} recipients) ---")

        for r in batch:
            text = render_message(args.message, r)
            try:
                kc.send_sms(text, r["normalized"])
                print(f"  {r['name']:30s}  SENT to {r['normalized']}")
                sent_count += 1
                log_send(args.log_file, msg_hash, r, "sent")
            except Exception as e:  # noqa: BLE001
                print(f"  {r['name']:30s}  FAILED: {e}")
                fail_count += 1
                log_send(args.log_file, msg_hash, r, f"error: {e}")
            time.sleep(1)

        if batch_num < total_batches:
            sleep_time = random.uniform(args.sleep_min, args.sleep_max)
            print(f"  ... sleeping {sleep_time:.1f}s ...")
            time.sleep(sleep_time)

    print()
    print(f"Summary: {len(recipients)} recipients")
    print(f"  Sent:   {sent_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Log file: {args.log_file}")

    # --- Offer to drop the Wi-Fi hotspot ---
    try:
        response = input("\nDisconnect from Wi-Fi hotspot? (y/N): ").strip().lower()
        if response == "y":
            import subprocess
            result = subprocess.run(
                ["nmcli", "device", "disconnect", "wlp195s0"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                print("Disconnected from hotspot. KDE Connect pairing persists "
                      "for next time.")
            else:
                print(f"Could not disconnect: "
                      f"{result.stderr.strip() or result.stdout.strip()}")
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == "__main__":
    main()
