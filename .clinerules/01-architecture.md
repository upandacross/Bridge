# Architecture Patterns

This document describes the key architectural patterns used in the Bridge project.

## Project Overview

The Bridge project has two distinct components:

1. **Attendance Tracker** — A DearPyGui desktop application for tracking bridge player attendance, managing schedules, and generating PDF reports
2. **Bridge Probability Simulations** — Python scripts (PyMC, Monte Carlo) for computing bridge card probabilities (finesse, contract levels, HCP distributions, trump splits)

## Database Schema (SQLite)

### Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `User` | Player information and preferences | `id`, `first`, `last`, `phone`, `active`, `play_thursdays`, `play_fridays`, `prefer_email/phone/text`, `all_month`, `select_days`, `will_come`, `will_leave` |
| `Month_Year_Thursday_Friday` | Game schedule per month | `id`, `MM`, `YYYY`, `thursdays` (array), `fridays` (array) |
| `Attendance` | Links users to game dates | `MYTF_id` (FK), `user_id` (FK), `thursdays` (bool array), `fridays` (bool array) |
| `sql_reports` | Saved SQL report scripts | `id`, `name`, `description`, `script_path`, `created_at`, `updated_at` |

### Key Relationships

```
User (1) ──────── (N) Attendance (N) ──────── (1) Month_Year_Thursday_Friday
```

- A user has one attendance record per month
- `first_last_phone_idx` enforces unique user (first + last + phone)
- Preference flags (`prefer_email`, `prefer_phone`, `prefer_text`) are mutually exclusive
- `all_month` and `select_days` are mutually exclusive

### Database Class

`database.py` contains the `Database` class — the single data access layer:

- All CRUD operations go through `Database` methods
- `check_same_thread=False` for DearPyGui compatibility
- WAL mode for concurrent reads
- Tables auto-created on `connect()` via `_create_tables()`

**Never bypass the `Database` class** with raw `sqlite3` connections. Always use the app's shared `db` instance.

## Attendance Tracker Architecture

### Tiered Structure

| Tier | Purpose | Files |
|------|---------|-------|
| Tier 1 | Database access | `database.py` |
| Tier 2 | UI components | `sql_reports.py` (SQLReportsManager) |
| Tier 3 | PDF generation | `generate_player_cards.py`, WeasyPrint |
| Tier 4 | Player card computation | `compute_player_card.py` |
| Tier 5 | Main application | `main()` in `database.py` (DearPyGui entry point) |

### Key Classes

- **`Database`** (`database.py`) — SQLite manager, all CRUD operations
- **`SQLReportsManager`** (`sql_reports.py`) — UI and CRUD for saved SQL reports
- **`PlayerCardGenerator`** (`generate_player_cards.py`) — Random table assignments with varied pairings
- **`PlayerCardComputer`** (`compute_player_card.py`) — Single player card from HTML template

## Probability Simulation Architecture

### Simulation Scripts

| Script | Purpose | Method |
|--------|---------|--------|
| `finesse_model.py` | Analytical finesse probability | PyMC (Bayesian MCMC) |
| `finesse_sim.py` | Finesse simulation (deprecated — has bug) | Monte Carlo |
| `finesse_compare.py` | Corrected finesse comparison | Monte Carlo + PyMC |
| `contract_probs.py` | Contract level probabilities | Monte Carlo (1M deals) |
| `trump_split.py` | Trump split distribution | Hypergeometric |
| `split.py` | Trump split (simple version) | Combinatorics |
| `hcp_distribution.py` | HCP and Total Points distribution | Exact combinatorial |
| `hcp_plots.py` | HCP/TP distribution plots | matplotlib |

### PyMC Model Pattern

Analytical models use this structure:

```python
with pm.Model() as model:
    # Prior (e.g., Beta for probabilities)
    p = pm.Beta("p", alpha=1, beta=1)

    # Likelihood (observed evidence)
    pm.Bernoulli("obs", p=p, observed=data)

    # Sample
    trace = pm.sample(2000, tune=1000, chains=4, random_seed=42)
```

### Monte Carlo Simulation Pattern

Deal simulations use vectorized numpy for speed:

```python
# Vectorized shuffle (fast — no Python loop)
sort_keys = rng.random((batch_size, 48))
order = np.argsort(sort_keys, axis=1)
deals = np.take_along_axis(remaining_deck, order, axis=1)

# Check constraints with boolean masks
mask = (hcp >= 12) & (hcp <= 14) & ...
```

**Always use vectorized operations** — Python loops over 100k+ deals are too slow.

## PDF Generation

- WeasyPrint is used for PDF generation (player cards, attendance reports)
- HTML templates are parsed by `compute_player_card.py`
- Output files: `player_cards3.pdf`, `player_cards4.pdf`, `player_cards5.pdf` (numbered by table count)

## Dependencies

| Package | Purpose |
|---------|---------|
| `dearpygui` | Desktop GUI framework |
| `pymc` | Bayesian statistical modeling (MCMC) |
| `weasyprint` | PDF generation from HTML |
| `mcp` | Model Context Protocol (code graph integration) |
| `numpy` | Vectorized simulation (implicit via pymc) |
| `matplotlib` | Plot generation (implicit) |
| `arviz` | PyMC posterior analysis (implicit via pymc) |

## CodeGraph Integration

The project has a `.codegraph.db` SQLite database for code structure indexing. See `.cursorrules` for CodeGraph usage details. Run `embed_code --files all` at the start of a new session.