# Common Gotchas and Mistakes

This document lists common mistakes and how to avoid them. These are learned from actual debugging sessions.

## 1. King Location Filtering in Finesse Simulations

**Problem**: The first finesse simulation (`finesse_sim.py`) reported P(finesse works) = 32.6%, which was wrong.

**Root Cause**: The simulation included deals where the King was dealt to the dealer or dummy. In a real bridge game, you see your hand and dummy's hand — if the King is there, there's no finesse question. These deals were counted as "finesse doesn't work" (King not with LHO), inflating the failure rate.

**Fix**: Always filter to only deals where the King is with an opponent (LHO or RHO):

```python
king_with_opp = king_in_lho | king_in_rho
valid = mask & king_with_opp  # Only count deals where King is with an opponent
```

Corrected result: ~70% (not 32.6%).

## 2. The 10 Is an Honor

**Problem**: Initial simulation code used `rank >= 9` to identify honors (J, Q, K, A), excluding the 10.

**Root Cause**: HCP values only count A, K, Q, J. But in bridge bidding convention, the **10 is also an honor** for suit quality evaluation.

**Fix**: Use `rank >= 8` to include 10, J, Q, K, A:

```python
is_honor = lho_ranks >= 8  # 10, J, Q, K, A — 10 IS an honor in bridge
```

Impact: ~1 percentage point shift in the correct direction.

## 3. HCP Proportionality Is Approximate

**Problem**: The analytical model estimated P(King with LHO) = LHO_HCP / opp_total_HCP = 74.4%, but the simulation ground truth was 69.6%.

**Root Cause**: HCP proportionality assumes that the probability of holding a specific card is proportional to HCP share. In reality, HCP is spread across many cards and suits. Having 74% of opponent HCP doesn't mean a 74% chance of holding any specific card — the King's location is driven by card count (vacant places) and HCP jointly.

**Fix**: Use Monte Carlo simulation as the ground truth. The analytical HCP+Vacant Places model (69.4%) was closest to simulation (69.6%). The HCP-only model (74.4%) overestimates by ~5pp.

## 4. Non-Vectorized Simulation Loops

**Problem**: Simulating 1 million deals with a Python loop (`for i in range(100000): np.random.shuffle(...)`) is extremely slow.

**Fix**: Use vectorized numpy operations:

```python
# ✅ FAST — vectorized shuffle via argsort
sort_keys = rng.random((batch_size, 48))
order = np.argsort(sort_keys, axis=1)
deals = np.take_along_axis(deck, order, axis=1)

# ❌ SLOW — Python loop
for i in range(batch_size):
    np.random.shuffle(deals[i])
```

The vectorized approach is ~100x faster.

## 5. Simulation Output Flooding Context

**Problem**: Running `python3 finesse_compare.py` directly in the terminal floods the context with progress bars and MCMC sampling output.

**Fix**: Always redirect simulation output to files:

```bash
python3 script.py > output.txt 2>&1; echo "EXIT: $?"
```

Then read `output.txt` to get the results.

## 6. PyMC HDI on Binary Variables

**Problem**: The 94% HDI for a binary (0/1) variable like `king_with_lho` shows [0%, 100%], which is meaningless.

**Root Cause**: HDI is computed on the posterior samples, which are all 0s and 1s. The HDI of a bimodal distribution spans the full range.

**Fix**: For binary latent variables, use the **posterior mean** as the probability estimate. The HDI is meaningful only for continuous parameters (like `p_finesse` in a Beta-Bernoulli model).

## 7. PyMC arviz.hdi Return Type Changed

**Problem**: `az.hdi(samples)` returns an array in newer versions, not a dict with `'hdi_lower'`/`'hdi_upper'` keys.

**Fix**: Handle both cases:

```python
hdi = az.hdi(samples, hdi_prob=0.94)
if isinstance(hdi, dict):
    lo, hi = hdi['hdi_lower'], hdi['hdi_upper']
else:
    lo, hi = float(np.ravel(hdi)[0]), float(np.ravel(hdi)[1])
```

## 8. arviz plot_trace API

**Problem**: `az.plot_trace()` does not accept `ax=` or `axes=` keyword arguments, making it incompatible with subplot layouts.

**Fix**: Use `az.plot_posterior()` for subplots (it accepts `ax=`). For trace plots, let `az.plot_trace()` create its own figure.

## 9. DearPyGui + SQLite Threading

**Problem**: DearPyGui callbacks that access the database can fail if the SQLite connection isn't configured for cross-thread use.

**Fix**: The `Database` class already uses `check_same_thread=False` and WAL mode. Never create a second `Database` instance — always use the shared `app.db` instance.

## 10. context_sets/best_practices.md Contains Precinct Project Content

**Problem**: `context_sets/best_practices.md` currently contains content from the Precinct project (Flask, PostgreSQL, n8n, etc.) — none of which applies to the Bridge project.

**Status**: Needs to be rewritten for the Bridge project (DearPyGui, SQLite, PyMC, WeasyPrint).

## 11. Finesse Direction Matters — Through the Opener, Not Around

**Problem**: It's tempting to think that swapping which hand holds A-Q vs J-10 (and finessing the other opponent) gives a symmetric result.

**Root Cause**: The opening bid breaks the symmetry. LHO has ~13 HCP; RHO has ~5 HCP. The King is much more likely with the player who has more HCP (the opener). Finessing through LHO works ~70%; finessing around LHO (through RHO) works only ~34%.

**Fix**: Always finesse **through the opener**, not around them. This is a classic bridge principle, now quantified by simulation.