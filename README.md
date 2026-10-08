# Bridge Attendance Tracker

A Python application to track bridge players' intentions to participate in bridge games on Thursdays or Fridays of any given month.

## Database Schema

### Month_Year_Thursday_Friday
Stores the schedule for each month:
- `id` - Unique primary key
- `MM` - Month (numeric)
- `YYYY` - Year (numeric)
- `thursdays` - Array of Thursday dates in YYYYMM format
- `fridays` - Array of Friday dates in YYYYMM format

### User
Stores player information and preferences:
- `active` - Boolean, required
- `play_thursdays` - Boolean, required
- `play_fridays` - Boolean, required
- `first` - String, required (first name)
- `last` - String, required (last name)
- `email` - String, required if `prefer_email` is true
- `phone` - String, required and unique
- `first_last_phone_idx` to enforce unique
- `prefer_email` - Boolean, if true, other preference flags are false
- `prefer_phone` - Boolean, if true, other preference flags are false
- `prefer_text` - Boolean, if true, other preference flags are false
- `all_month` - Boolean, true if player attends all month (select_days is false)
- `select_days` - Boolean, true if player selects specific days (all_month is false)
- `will_come` - Boolean
- `will_leave` - Boolean

### Attendance
Tracks actual attendance:
- `MYTF_id` - Foreign key referencing Month_Year_Thursday_Friday table
- `user_id` - Foreign key referencing User table
- `thursdays` - Array of booleans, one for each Thursday in the linked record (if user plays_thursdays is true)
- `fridays` - Array of booleans, one for each Friday in the linked record (if user plays_fridays is true)

## Frontend - DearPyGui

A graphical interface built with DearPyGui providing:

- **CRUD operations** for managing users - trap duplicate user and display 'User exists' message
- **Attendance display/PDF export** showing player attendance by YYYYMM in a data table
  - Number of tables calculated as `mod(sum(attending players, 4))` for each Thursday and Friday
  - **edit attendance records** by first, last, phone for specific YYYYMMDD
- **Filtering** attendance records by YYYYMM and play day (Thursday or Friday)
- **Display & Edit attendance boolean array** for user YYYYMM.
Example:

|User|YYYYMM|Day|1st|2nd|3rd|4th|
|----------|:--------:|:------------:|:-----:|:-----:|:-----:|:-----:|
|B Letson|202602|Thursday|2/06|2/13|2/20|2/27|
||||x|x|x|x|
|B Letson|202602|Friday|2/07|2/14|2/21|2/28|
||||||x|x|

- **Quick attendance updates** for users via phone number or name
  - Prompts to create user record if name or phone not found
- **Automatic schedule management**
  - Triggers to add/delete Month_Year_Thursday_Friday records with associated attendance records
  - **Attendance Reports** by YYYYMM
  - **All User Reports** by active or inactive, by thursdays or fridays or both
  - **Quit** to exit application

## SMS Signup Reminders (`send_bridge_sms.py`)

Texts bridge players selected from the Thursday signup spreadsheet (ODS)
via a phone paired over KDE Connect. By default it texts the players marked
**attending** for the chosen day; `--audience declined` selects the players
marked **not attending** instead.

### Mark convention (important)

The signup spreadsheet's day columns use:

- `x`  = **not attending** (declined)
- `✔`  = **attending**

The default audience is the `✔` (attending) rows — e.g. a "see you there"
note. Pass `--audience declined` to target the `x` rows instead (a
"confirming you won't be there" note). Either way the marks are the
**opposite** of the attendance-table example above, where `x` marks a
player who is attending.

### How it works

1. Reads the ODS directly (no `odfpy` needed — it parses `content.xml`).
   The file is auto-discovered for the current month
   (`Bridge Signup Thursday <Month>.ods`); pass `--file PATH` to override,
   or when none/several match (both cases error rather than guess).
2. Finds the header row by locating the `number` cell, so both the current
   layout (header on row 0) and older files with a title block above the
   header are supported.
3. Selects the day column. Header days are anchored to the **sheet's
   month** (taken from the filename) so the comparison is between real
   dates, not bare day numbers. The default is the earliest game date
   `>= today`:
   - Run on the 6th, 7th, or 8th, it picks the 8th (running *on* a game day
     targets that day).
   - A November sheet run on Oct 30 picks Nov 5 (the game may be in the
     next month).
   - A sheet from a month *before* the current month is rejected as stale
     ("Pass --file to select the correct sheet").
   - A sheet for the *next* month may be used early, e.g. a January sheet
     opened in late December.
   Use `--day DD` to force a specific column.
4. Collects rows whose mark matches the audience (`✔` attending by
default, or `x` with `--audience declined`), normalizes phones to E.164,
and deduplicates by phone so a shared household number gets one text.

### Always-call players (do not text)

Some players prefer a call. Two signals mark them, and both are honored:

- An **`Always call X` note** in the sheet's `Last` column (e.g.
  `Trudy | Always call Smith`). Detected automatically; the note is
  stripped so the name displays cleanly.
- The **`ALWAYS_CALL`** set of real names at the top of the script
  (default: Milrie Lentz, Trudy Smith), matched case-insensitively against
  `First Last`. `--always-call "First Last" ...` **adds** extra names to
  that set; `--always-call-replace` treats the given names as the complete
  set instead.

These players are skipped and listed separately under *call these
instead*. Use `--include-always-call` to text them anyway.

### Resending (`--force`)

The send log keys on the message hash, so re-running the **same** message
skips phones already texted. `--force` ignores the log for a run and
re-sends to everyone selected — e.g. to resend an identical broadcast.

### Phone link check

By default the script checks the desktop<->phone KDE Connect link and
prints the device and battery. This is a link check only — it does **not**
confirm cellular service or carrier delivery.

The check no longer forces an exit when a message is given:

- **Dry-run** prints the link status and then continues to the recipient
  list, whether or not the phone is reachable.
- **Execute** (`--execute`) aborts before sending if the phone is not
  reachable.
- With **no `--message`**, the run stops right after the check (a pure
  link check).

Pass `--check-phone no` to skip the check entirely and proceed.

### Delivery caveat

`kdeconnect-cli` is fire-and-forget: "SENT" means KDE Connect handed the
message to the phone, not that the carrier delivered it. Out-of-service or
no-signal numbers are not detectable from the return code.

### Usage

```bash
# Check the phone link only (also the default when the flag is omitted)
python send_bridge_sms.py --check-phone yes

# Dry-run: who would be texted for the next game
python send_bridge_sms.py --check-phone no \
    --message "Hi {first}, confirming you won't be at bridge on Oct 8. - Bren"

# Send
python send_bridge_sms.py --check-phone no \
    --message "Hi {first}, confirming you won't be at bridge on Oct 8. - Bren" --execute
```

`--file` selects the signup sheet; without it, the script uses the current
month's file and errors if none or several match. `{first}` is replaced per
recipient if present; otherwise the message is sent verbatim. A CSV send log (`bridge_sms_log.csv`) keyed on the message
hash makes re-runs skip phones already texted. `--help` lists all options.
