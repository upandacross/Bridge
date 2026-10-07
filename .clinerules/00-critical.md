# CRITICAL RULES — MUST FOLLOW

review `.cursorrules` for CodeGraph integration rules.

## 1. Use `uv` for All Dependency Management

**ALWAYS use `uv`, never `pip`.**

```bash
uv add package-name   # ✅ CORRECT
pip install package-name  # ❌ BREAKS LOCKFILE
```

**Why**: `pip` doesn't maintain `uv.lock` integrity. The project uses `uv` with a workspace member `bridge`.

## 2. SQLite Database — Single File, WAL Mode

The database is `bridge.db` (SQLite). The `Database` class in `database.py` handles all connections with `check_same_thread=False` (required for DearPyGui callbacks) and `PRAGMA journal_mode=WAL`.

- **Never** create separate SQLite databases for tests — use the existing `bridge.db` or `/tmp/` test databases
- **Never** hardcode the database path — pass it via `db_path` parameter
- **Always** use `sqlite3.Row` row factory (set in `Database.connect()`)

## 3. DearPyGui Threading Model

DearPyGui callbacks run on the UI thread. The database connection uses `check_same_thread=False` to allow cross-thread access, but:

- ✅ Short DB queries from callbacks are fine
- ✅ Use WAL mode (already enabled) for better concurrency
- ❌ Do NOT spawn background threads for DB writes without proper synchronization
- ❌ Do NOT create multiple `Database` instances — share the app's `db` instance

## 4. No Commits Without Testing

**MANDATORY**: All changes must be tested before committing.

- UI changes → Launch the DearPyGui app and verify the affected screen
- Database changes → Run `test/test_attendance_schema.py`
- Probability scripts → Run the script and check output
- Python changes → `uv run pyright <file.py>` clean (see §10 and gotcha #13)
- **All changes** → Present results for user review before committing

## 5. Card Encoding Convention

Bridge simulation scripts use a consistent card encoding:

```
card_id = suit * 13 + rank
Suits: 0=S, 1=H, 2=D, 3=C
Ranks: 0=2, 1=3, ..., 7=9, 8=10, 9=J, 10=Q, 11=K, 12=A
```

HCP values: A=4, K=3, Q=2, J=1 (all others=0)

**Always use this encoding** in new simulation scripts. Do not invent alternative encodings.

## 6. The 10 Is an Honor

In bridge convention (and this project), the **10 is counted as an honor** alongside A, K, Q, J. When checking for "honors in a suit," use `rank >= 8` (i.e., 10, J, Q, K, A), **not** `rank >= 9`.

**Why**: The user corrected this — the 10 is an honor in bridge bidding.

## 7. King Location Filtering in Simulations

When simulating finesse probabilities, **always filter to deals where the target card (e.g., King) is with an opponent** (LHO or RHO), not with the dealer or dummy. In a real bridge game, you see your hand and dummy's hand — if the card is there, there's no finesse question.

**Why**: The first simulation (`finesse_sim.py`) failed to do this and reported 32.6% instead of the correct ~70%.

## 8. Context Window Conservation

For verbose output scripts (simulations generating millions of deals), redirect output to files and read summaries:

```bash
python3 script.py > output.txt 2>&1; echo "EXIT: $?"
```

Then read `output.txt` — do not let large simulation logs consume context.

## 9. Pace of Work — Pause at Natural Points

Work in small, reviewable steps. Pause for acknowledgment before proceeding to the next phase.

- After diagnosing a problem and BEFORE making changes: state the root cause and planned fix, then pause
- After each logical group of edits: summarize what happened, then pause
- When output requires user review (simulation results, plots): STOP after presenting it

## 10. Annotate Everything

**MANDATORY**: Annotate every function you write or touch — parameter and return types. Prefer a `TypedDict`/dataclass over a bare `dict` for structured returns.

- Validate with `uv run pyright <file.py>` (a clean run on the touched file is the bar) — **not** `py_compile`, which only checks syntax
- Unannotated returns widen under type inference and produce **false positives in every caller**; the fix belongs in the library, never a `# type: ignore` at each call site
- When tightening a shared function's return type, re-check **all** its consumers, not just the file you edited

See gotcha #13 in `03-gotchas.md` for the full failure mode and worked example.

## When Rules Conflict

1. Data integrity rules take priority over performance
2. User-specified conventions (e.g., 10 as honor) take priority over defaults
3. Ask the user for clarification