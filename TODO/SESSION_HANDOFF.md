# Session Handoff — Bridge Project

## 1. Summary

Built Bayesian models (PyMC) and Monte Carlo simulations to answer two bridge probability questions: (1) whether a finesse for the King works when LHO has opened, and (2) the probability of a partnership having enough HCP for each contract level (game, slam). Key finding: when LHO opens a 5-card suit that is not yours, the finesse **through LHO** is strongly favored (~70%) while finessing **around LHO** (through RHO) is strongly disfavored (~34%). Contract probability table: P(any game)≈17.5%, P(small slam)≈0.35%, P(grand slam)≈0.01%.

Additional work this session: SMS reminder script (`send_bridge_sms.py`) — now sends to **attendees by default** (`--audience attending|declined`), with `--force` to bypass the send log and additive `--always-call`; player-card generator now defaults to `player_cards<N>.pdf`; project `.clinerules` memory added; pyright wired in as the type-check (gotcha #13); `phone-mcp` relocated to a shared clone with a `PHONE_MCP_DIR` override; first pytest unit tests for the SMS logic added.

## 2. Files Changed

| Path | What changed | Category | Status |
|------|-------------|----------|--------|
| `.clinerules/00-critical.md` | Critical rules for the Bridge project | config | committed |
| `.clinerules/01-architecture.md` | Architecture patterns (SQLite, DearPyGui, PyMC, simulations) | config | committed |
| `.clinerules/02-workflows.md` | Development workflows (running scripts, testing, PDF gen) | config | committed |
| `.clinerules/03-gotchas.md` | 13 learned gotchas from this session | config | committed |
| `pyproject.toml` | Added `pymc>=5.28.5` (later `pytest>=9.1.1`) dependency | config | committed |
| `uv.lock` | Lockfile updates for pymc/pytest | config | committed |
| `generate_player_cards.py` | Default PDF filename `player_cards<N>.pdf`; CSV/HTML now opt-in | code | committed |
| `README.md` | Documented `send_bridge_sms.py` (mark convention, discovery, always-call) | docs | committed |
| `test/test_sms_logic.py` | Unit tests for `send_bridge_sms` pure logic (36 tests) | tests | committed (this session) |
| `send_bridge_sms.py` | SMS to signup sheet; audience selectable (`--audience`, default **attending**), `--force` bypasses send log, additive `--always-call`; resolves `phone-mcp` via `PHONE_MCP_DIR` | code | committed |
| `finesse_model.py` | Analytical PyMC models: HCP-only (74.4%) and HCP+vacant places (69.4%) | code | committed |
| `finesse_sim.py` | First simulation approach — **had a bug** (didn't filter King to be with an opponent). Superseded by `finesse_compare.py`. | code | committed |
| `finesse_compare.py` | **Corrected** simulation comparing two finesse scenarios. Key file. | code | committed |
| `contract_probs.py` | Simulates 1M deals, partnership HCP distribution, table + histogram | code | committed |
| `hcp_distribution.py`, `hcp_plots.py` | HCP / Total Points distribution + plots | code | committed |
| `split.py`, `trump_split.py` | Trump split distributions | code | committed |
| `main.py`, `test_pair_intersection.py` | Removed (unused entry point / stale test script) | code | committed |
| `test/` (renamed from `test_dir/`) | Directory renamed on disk; `test_attendance_schema.py` tracked at new path | code | committed (this commit) |
| `.clinerules/00-critical.md`, `.clinerules/02-workflows.md` | Path refs updated `test_dir/` → `test/` | config | committed (this commit) |
| `.gitignore` | Added `*.png`, `*.txt`, `node_modules/`, `Bridge Base Online_files/` | config | committed |
| `test/test_sms_logic.py` | Unit tests for `send_bridge_sms` pure logic (36 tests) | tests | committed |
| `test/test_attendance_validation.py` | Unit + integration tests for attendance validation | tests | committed |
| `test/test_database.py` | CRUD tests for `database.py` (temp-file DBs) | tests | committed |
| `test/test_player_cards.py` | Invariant tests for `PlayerCardGenerator` | tests | committed (this session) |
| `pytest.ini` | Registers `integration` marker; deselects it by default | config | committed (this session) |
| `TODO/SESSION_HANDOFF.md` | This handoff document | config | committed (this commit) |

### Not committed (working artifacts — intentionally left out)

Generated outputs (`output*.txt`, `trump_split_result.txt`) and plots (`*.png`) are now gitignored; the October signup `.ods` sheets and `bridge.db` are tracked. Nothing is intentionally left uncommitted in this repo.

## 3. Root Causes & Diagnoses

1. **Analytical HCP model overestimated finesse probability** (74.4% vs simulated 69.6%). The HCP-proportionality heuristic (P(King with LHO) = LHO_HCP / opp_total_HCP) is an approximation that overestimates because HCP is spread across many cards/suits.

2. **Critical bug in first simulation** (`finesse_sim.py`): Reported 32.6% because it included deals where the King was dealt to the dealer or dummy. Fix: filter to only deals where King is with LHO or RHO. Corrected result: ~69.6%.

3. **Vacant places effect is real but secondary**: LHO having 5+ in opening suit means ~7 vacant slots vs RHO's 13. HCP effect dominates, pushing combined probability to ~70%.

4. **10 as honor**: Including the 10 (rank 8) as an honor shifted results ~1pp.

5. **Test directory was renamed on disk but never committed**: `test_dir/` (git-tracked) was renamed to `test/` outside git, leaving stale `test_dir/` entries plus an untracked `test/`. Resolved by staging the rename explicitly (`git add test/test_attendance_schema.py && git add -u test_dir/`) so git records a rename, not delete+add. Note `.clinerules` docs originally referenced the correct historical name; the paths are now updated to `test/`.

6. **CodeGraph post-commit hook had a stale error marker** (`~/.local/state/prc/<hash>/code_graph_error`): a transient `sqlite3.OperationalError: unable to open database file`. Running `rebuild_code_graph.py` directly succeeded and self-cleared the marker — the failure was not a permissions/FS issue.

## 4. Pending Steps

**Ready to run (rerunnable):**
- `cd Bridge && python3 finesse_compare.py`
- `cd Bridge && python3 contract_probs.py`
- `cd Bridge && python3 finesse_model.py`
- `cd Bridge && python3 test/test_attendance_schema.py` (schema test)
- `cd Bridge && ./send_bridge_sms.py --file <sheet.ods> --day DD --message "..."` (dry-run; add `--execute` to send)

**Blocked on user decision:**
- Minor suit opening (3+ cards, asking for 4-card major) — user said "keep it simple for now."
- Sensitivity analysis: dealer HCP 12 vs 14, second bidding round, 6-card opening suit.
- Rewrite `context_sets/best_practices.md` (currently contains Precinct project content — see gotcha #10).
- Whether to commit the signup ODS sheets (`Bridge Signup Friday October.ods`, the modified `Bridge Signup Thursday October.ods`, and `Bridge Signup Thursday October Backup.ods`) — currently left untracked/unstaged.

## 5. Open Decisions

1. Model a minor-suit opening as a separate scenario?
2. Rewrite `context_sets/best_practices.md` for the Bridge project?
3. RESOLVED: `node_modules/` gitignored + untracked; `*.png`/`*.txt`/`Bridge Base Online_files/` ignored. `bridge.db` and `*.ods` deliberately kept tracked/visible per user preference.
4. RESOLVED: `test/test_attendance_schema.py` docstring `test_dir` reference fixed.
5. Should `--audience` default stay `attending`? It reverses the script's original declined-oriented purpose — anything relying on the old default now targets the opposite group.
6. Any further bridge probability questions to model (restricted choice, etc.)?

## 6. Validation Status

| Component | Status |
|-----------|--------|
| `finesse_model.py` — PyMC convergence | ✅ r_hat=1.0, no divergences (previous session) |
| `finesse_compare.py` — Simulation | ✅ 20k+ matching deals, tight 95% CIs (previous session) |
| `contract_probs.py` — Simulation | ✅ 1M deals, stable convergence (previous session) |
| Schema test (`test/test_attendance_schema.py`) | ✅ run this session (34/34 games valid, 442 records, 0 errors) |
| `send_bridge_sms.py` — flag changes | ✅ dry-run verified (audience/force/always-call); `pyright` clean; **not** executed against real recipients by the agent |
| SMS logic unit tests (`test/test_sms_logic.py`) | ✅ `uv run pytest` — 36 passed; `pyright` clean |
| Attendance validation tests (`test/test_attendance_validation.py`) | ✅ 20 unit passed; 4 integration passed (`-m integration`); `pyright` clean |
| Database CRUD tests (`test/test_database.py`) | ✅ 29 passed (temp-file DBs); `pyright` clean |
| Player card tests (`test/test_player_cards.py`) | ✅ 12 passed (seeded; invariants held over 300 seeds); `pyright` clean |
| CodeGraph rebuild | ✅ re-enabled this session (stale error marker cleared) |
| Git commits | ✅ Executed this session (multiple phased groups — see `git log`) |

## 7. Resume Here

**Load `.clinerules/00-critical.md` through `03-gotchas.md` first.**

**SMS script quick reference** (`send_bridge_sms.py`): default audience is `attending` (`✔`); `--audience declined` targets `x`; `--always-call NAMES` adds to the built-in {Milrie Lentz, Trudy Smith}; `--force` ignores the send log; dry-run is the default (add `--execute` to send). The ODS sheets are live data — recipient counts shift as the sheet is edited.

**Tests:** run `cd Bridge && uv run pytest` — 101 unit tests (SMS logic + attendance schema rules + database CRUD + player cards). Integration tests hit the real `bridge.db`: `uv run pytest -m integration` (4 tests). The older `test/test_attendance_schema.py` is a standalone script (`python3 test/test_attendance_schema.py`), not collected by pytest. All test files use temp-file DBs where a DB is needed — never `bridge.db`, per `.clinerules`.

**Bridge probability work:** re-read `finesse_compare.py` (the key corrected simulation) and `output_compare.txt` (results). The highest-leverage next step is the minor-suit opening scenario or HCP sensitivity analysis in `finesse_compare.py`.

## 8. Shared dependency: phone-mcp

`send_bridge_sms.py` imports `KDEConnect` from a shared clone of the
third-party **phone-mcp** repo (upstream `github.com/wexi/phone-mcp`, by a
developer "Enoch"). It was moved out of `precinct/phone-mcp` to avoid one
consumer owning it:

- **Now at:** `~/Home/Projects/phone-mcp` (override with `PHONE_MCP_DIR`).
- **Consumers:** `Bridge/send_bridge_sms.py` and
  `precinct/app_administration/send_release_announcement.py` both resolve it
  via the same env-overridable path.
- **pyright:** `Bridge/pyproject.toml` `[tool.pyright] extraPaths` points at it.
- **Local-only commits:** phone-mcp has 2 unpushed typing commits
  (`f8c70f2`, `e8bea65`) — not pushed upstream (no write access to `wexi`).
