"""
Simulation-based Bayesian model for the finesse problem.

Instead of modeling HCP and card distributions analytically, we:
  1. Simulate random bridge deals (vectorized, fast)
  2. Filter deals matching our constraints:
     - Dealer has ~13 HCP (12-14), holds J-10 of our suit (hearts)
     - Dummy has 6+ HCP, holds A-Q of hearts
     - LHO has 12+ HCP (opened the bidding)
     - LHO has a 5+ card suit (NOT hearts) with 2+ honors
  3. For each matching deal, record whether the King of hearts is with LHO
  4. Feed these observations into a PyMC Beta-Bernoulli model
  5. Show the posterior converging as more deals accumulate
"""

import numpy as np
import pymc as pm
import arviz as az
import matplotlib.pyplot as plt

np.random.seed(42)

# ================================================================
# CARD ENCODING
# card_id = suit * 13 + rank
# Suits: 0=S, 1=H (our suit), 2=D, 3=C
# Ranks: 0=2, 1=3, ..., 7=9, 8=10, 9=J, 10=Q, 11=K, 12=A
# ================================================================

# Known cards (fixed in place)
J_HEARTS = 1 * 13 + 9    # 22
T_HEARTS = 1 * 13 + 8    # 21
A_HEARTS = 1 * 13 + 12   # 25
Q_HEARTS = 1 * 13 + 10    # 23
K_HEARTS = 1 * 13 + 11    # 24  <- the card we're tracking

known_dealer = np.array([J_HEARTS, T_HEARTS])  # J♥, 10♥
known_dummy = np.array([A_HEARTS, Q_HEARTS])   # A♥, Q♥

# HCP table: A=4, K=3, Q=2, J=1
HCP = np.zeros(52)
for c in range(52):
    r = c % 13
    if r == 12: HCP[c] = 4
    elif r == 11: HCP[c] = 3
    elif r == 10: HCP[c] = 2
    elif r == 9:  HCP[c] = 1

known_dealer_hcp = HCP[known_dealer].sum()  # 1.0 (J)
known_dummy_hcp = HCP[known_dummy].sum()    # 6.0 (A+Q)

# Remaining 48 cards (everything except J♥, 10♥, A♥, Q♥)
remaining = np.array([c for c in range(52) if c not in [21, 22, 23, 25]])

# ================================================================
# VECTORIZED DEAL SIMULATOR
# ================================================================

def simulate_batch(batch_size, rng):
    """
    Simulate batch_size deals and return:
      - king_with_lho: boolean array (True if K♥ is in LHO's hand)
      - mask: boolean array (True if deal meets all constraints)
    """
    # Fast vectorized shuffle: generate random sort keys
    sort_keys = rng.random((batch_size, 48))
    order = np.argsort(sort_keys, axis=1)
    deals = np.take_along_axis(
        np.broadcast_to(remaining, (batch_size, 48)), order, axis=1
    )

    # Deal: 11 to dealer, 11 to dummy, 13 to LHO, 13 to RHO
    dealer_rest = deals[:, :11]
    dummy_rest  = deals[:, 11:22]
    lho         = deals[:, 22:35]
    rho         = deals[:, 35:48]

    # --- HCP ---
    dealer_hcp = known_dealer_hcp + HCP[dealer_rest].sum(axis=1)
    dummy_hcp  = known_dummy_hcp  + HCP[dummy_rest].sum(axis=1)
    lho_hcp    = HCP[lho].sum(axis=1)

    # --- Constraints ---
    mask = (dealer_hcp >= 12) & (dealer_hcp <= 14)    # Dealer ~13 HCP
    mask &= (dummy_hcp >= 6)                          # Partner 6+ HCP
    mask &= (lho_hcp >= 12)                           # LHO opened (12+ HCP)

    # LHO has 5+ in a non-heart suit (S/D/C) with 2+ honors (A,K,Q,J)
    lho_suits = lho // 13          # (batch, 13) suit indices
    lho_ranks = lho % 13           # (batch, 13) rank indices
    is_honor = lho_ranks >= 9      # J=9, Q=10, K=11, A=12

    can_open = np.zeros(batch_size, dtype=bool)
    for suit in [0, 2, 3]:         # Spades, Diamonds, Clubs (not Hearts)
        in_suit = lho_suits == suit
        suit_len = in_suit.sum(axis=1)
        suit_honors = (in_suit & is_honor).sum(axis=1)
        can_open |= (suit_len >= 5) & (suit_honors >= 2)

    mask &= can_open

    # --- King location ---
    king_with_lho = (lho == K_HEARTS).any(axis=1)

    return king_with_lho, mask, lho_hcp, lho_suits


# ================================================================
# RUN SIMULATION
# ================================================================

rng = np.random.default_rng(42)

all_results = []
total_sim = 0
total_match = 0
target = 20000

# Track convergence at intervals
convergence_points = []  # (n_matches, p_estimate)

print("Simulating bridge deals...")
print(f"{'Simulated':>12} {'Matched':>8} {'Rate':>7} {'P(K with LHO)':>14}")

batch = 50000
while total_match < target:
    king_lho, mask, _, _ = simulate_batch(batch, rng)
    n_match = mask.sum()
    all_results.extend(king_lho[mask].tolist())
    total_match += n_match
    total_sim += batch

    p = np.mean(all_results)
    print(f"{total_sim:>12,} {total_match:>8,} {total_match/total_sim:>7.1%} {p:>14.4f}")
    convergence_points.append((total_match, p))

results = np.array(all_results)
n = len(results)
p_hat = np.mean(results)

print(f"\n{'=' * 60}")
print(f"SIMULATION COMPLETE")
print(f"{'=' * 60}")
print(f"Total deals simulated:  {total_sim:,}")
print(f"Matching deals found:    {n:,}")
print(f"Rejection rate:          {1 - n/total_sim:.1%}")
print(f"P(finesse works):        {p_hat:.4f}")
print(f"95% CI (freq):           [{p_hat - 1.96*np.sqrt(p_hat*(1-p_hat)/n):.4f}, "
      f"{p_hat + 1.96*np.sqrt(p_hat*(1-p_hat)/n):.4f}]")

# ================================================================
# PyMC MODEL: Feed simulated deals as evidence
# ================================================================

print(f"\n{'=' * 60}")
print(f"PyMC Model: Beta(1,1) prior + simulated observations")
print(f"{'=' * 60}")

with pm.Model() as sim_model:
    # Prior: uniform (50-50 compatible — Beta(1,1) is uniform on [0,1])
    p_finesse = pm.Beta("p_finesse", alpha=1, beta=1)

    # Likelihood: each matching deal is a Bernoulli observation
    pm.Bernoulli("obs", p=p_finesse, observed=results)

    trace = pm.sample(2000, tune=1000, chains=4, random_seed=42)

summary = az.summary(trace, var_names=["p_finesse"])
print(summary)

p_samples = trace.posterior["p_finesse"].values.flatten()
hdi = az.hdi(p_samples, hdi_prob=0.94)
hdi_lower = float(np.ravel(hdi)[0])
hdi_upper = float(np.ravel(hdi)[1])

print(f"\n{'─' * 60}")
print(f"RESULTS COMPARISON")
print(f"{'─' * 60}")
print(f"  Prior (no evidence):              50.0%")
print(f"  HCP-only model (PyMC):            74.4%")
print(f"  HCP + Vacant Places (PyMC):       69.4%")
print(f"  Simulation-based (this model):    {np.mean(p_samples):.1%}")
print(f"  Simulation 94% HDI:               [{hdi_lower:.1%}, {hdi_upper:.1%}]")
print(f"  Simulation 95% freq CI:          [{p_hat - 1.96*np.sqrt(p_hat*(1-p_hat)/n):.1%}, "
      f"{p_hat + 1.96*np.sqrt(p_hat*(1-p_hat)/n):.1%}]")
print(f"{'─' * 60}")

# ================================================================
# PLOTS
# ================================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# 1. Convergence plot
n_vals = [c[0] for c in convergence_points]
p_vals = [c[1] for c in convergence_points]
axes[0].plot(n_vals, p_vals, 'b-o', markersize=4)
axes[0].axhline(0.5, color='gray', linestyle='--', alpha=0.5, label='Prior (50%)')
axes[0].axhline(0.744, color='orange', linestyle='--', alpha=0.5, label='HCP-only (74.4%)')
axes[0].axhline(0.694, color='green', linestyle='--', alpha=0.5, label='HCP+VP (69.4%)')
axes[0].axhline(p_hat, color='red', linestyle='-', alpha=0.7, label=f'Simulation ({p_hat:.1%})')
axes[0].set_xlabel('Number of matching deals')
axes[0].set_ylabel('P(finesse works)')
axes[0].set_title('Posterior Convergence')
axes[0].legend(fontsize=8)
axes[0].grid(True, alpha=0.3)

# 2. Posterior distribution
az.plot_posterior(trace, var_names=["p_finesse"], ax=axes[1])
axes[1].set_title("Posterior: P(finesse works)")
axes[1].axvline(0.5, color='gray', linestyle='--', alpha=0.5, label='Prior (50%)')
axes[1].axvline(0.744, color='orange', linestyle='--', alpha=0.5, label='HCP-only')
axes[1].axvline(0.694, color='green', linestyle='--', alpha=0.5, label='HCP+VP')
axes[1].legend(fontsize=8)

# 3. Histogram of simulated results (running proportion)
running_p = np.cumsum(results) / np.arange(1, n + 1)
axes[2].plot(range(1, n + 1), running_p, 'b-', alpha=0.7, linewidth=0.5)
axes[2].axhline(p_hat, color='red', linestyle='-', alpha=0.7, label=f'Mean ({p_hat:.1%})')
axes[2].axhline(0.5, color='gray', linestyle='--', alpha=0.5, label='Prior (50%)')
axes[2].set_xlabel('Deal number')
axes[2].set_ylabel('Running P(K with LHO)')
axes[2].set_title('Running Proportion (King with LHO)')
axes[2].legend(fontsize=8)
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("finesse_simulation.png", dpi=150)
print(f"\nPlot saved to: finesse_simulation.png")