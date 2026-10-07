# Development Workflows

This document describes the development workflows for the Bridge project.

## Session Start

At the start of each session:

1. Load `.clinerules/00-critical.md` through `03-gotchas.md`
2. Check `TODO/SESSION_HANDOFF.md` for session state
3. If working with code, run `embed_code --files all` to refresh the code graph
4. Load `context_sets/best_practices.md` if working on the attendance tracker

## Running the Attendance Tracker

```bash
cd Bridge && uv run python database.py
```

This launches the DearPyGui desktop application with the main menu:
- CRUD operations for users
- Attendance display/edit by YYYYMM
- PDF export
- Player card generation
- SQL report management

## Running Probability Simulations

### Analytical Models (PyMC)

```bash
cd Bridge && python3 finesse_model.py > output.txt 2>&1
```

Takes ~2 seconds per model. Redirect to file to conserve context.

### Monte Carlo Simulations

```bash
cd Bridge && python3 finesse_compare.py > output_compare.txt 2>&1
cd Bridge && python3 contract_probs.py > output_probs.txt 2>&1
```

These simulate 1-4 million deals and take 10-60 seconds. **Always redirect output to files.**

### Quick Probability Scripts

```bash
cd Bridge && python3 trump_split.py      # Trump split distribution
cd Bridge && python3 hcp_distribution.py  # HCP/Total Points distribution
cd Bridge && python3 hcp_plots.py         # Generate HCP/TP plots
```

## Testing

### Schema Tests

```bash
cd Bridge && python3 test/test_attendance_schema.py
```

Tests verify the SQLite schema is correct and attendance data integrity holds.

### Validation Data

`test/attendance_validation.csv` contains known-good attendance data for validation.

### Testing New Simulations

For new probability scripts:
1. Run the script with a small number of simulations first (e.g., 1000 deals)
2. Verify the output makes sense (e.g., HCP mean should be ~10 per hand, ~20 per partnership)
3. Scale up to full simulation (100k+ deals)
4. Check convergence (running proportion should stabilize)

## PDF Generation

### Player Cards

```bash
cd Bridge && uv run python generate_player_cards.py
```

Generates PDF player cards with random table assignments. Output: `player_cards{N}.pdf`.

### Attendance Reports

Generated from within the DearPyGui application (WeasyPrint).

## File Reading Best Practices

Prefer ranged reads over full-file reads:

```bash
sed -n 'START,ENDp' FILE     # Range
sed -n 'N,$p' FILE           # From line N to end
grep -nE '^#|^##' FILE       # Find section headers
```

For large files (`database.py` is 1000+ lines), use `grep -n` first to find the target region, then read just that section.

## Dependency Management

```bash
uv add <package-name>     # Add a dependency
uv remove <package-name>  # Remove a dependency
uv sync                   # Install all dependencies from lockfile
uv run python script.py   # Run a script with project dependencies
```

**Never use `pip install`** — it breaks the `uv.lock` file.

## Git Workflow

1. Make changes
2. Test (run relevant scripts or launch the app)
3. Present results to user for review
4. Commit after user approval
5. Post-commit hook updates `.codegraph.db`