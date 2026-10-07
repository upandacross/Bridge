"""
Compare two finesse scenarios with simulation:

Scenario A (original): Dealer has J-10, Dummy has A-Q
  - Finesse LHO: lead J-10 from dealer toward A-Q on board
  - Works if King is with LHO

Scenario B (swapped): Dealer has A-Q, Dummy has J-10
  - Finesse RHO: lead J-10 from board toward A-Q in dealer
  - Works if King is with RHO

In both cases: LHO opened (12+ HCP, 5+ suit with 2 honors, not hearts)
              Dealer ~13 HCP, Partner 6+ HCP
              King must be with an OPPONENT (not dealer or dummy)

Bug fix from previous version: filter to only deals where the King
is with LHO or RHO (we would see it in our hand or dummy's hand).
"""

import numpy as np
import pymc as pm
import arviz as az
import matplotlib.pyplot as plt

rng = np.random.default_rng(42)

# ================================================================
# CARD ENCODING (same as before)
# ================================================================
J_HEARTS = 1 * 13 + 9   # 22
T_HEARTS = 1 * 13 + 8   # 21
A_HEARTS = 1 * 13 + 12   # 25
Q_HEARTS = 1 * 13 + 10   # 23
K_HEARTS = 1 * 13 + 11   # 24

HCP = np.zeros(52)
for c in range(52):
    r = c % 13
    if r == 12: HCP[c] = 4
    elif r == 11: HCP[c] = 3
    elif r == 10: HCP[c] = 2
    elif r == 9:  HCP[c] = 1

remaining = np.array([c for c in range(52) if c not in [21, 22, 23, 25]])


def simulate_scenario(known_dealer_cards, known_dummy_cards, batch_size=50000):
    """
    Simulate deals for a given card arrangement.
    Returns king locations for matching deals where King is with an opponent.
    """
    kd_hcp = HCP[np.array(known_dealer_cards)].sum()
    kn_hcp = HCP[np.array(known_dummy_cards)].sum()

    all_results = []  # 1 = King with LHO, 0 = King with RHO
    total_sim = 0
    total_match = 0
    target = 20000

    while total_match < target:
        # Vectorized shuffle
        sort_keys = rng.random((batch_size, 48))
        order = np.argsort(sort_keys, axis=1)
        deals = np.take_along_axis(
            np.broadcast_to(remaining, (batch_size, 48)), order, axis=1
        )

        dealer_rest = deals[:, :11]
        dummy_rest  = deals[:, 11:22]
        lho         = deals[:, 22:35]
        rho         = deals[:, 35:48]

        # HCP
        dealer_hcp = kd_hcp + HCP[dealer_rest].sum(axis=1)
        dummy_hcp  = kn_hcp + HCP[dummy_rest].sum(axis=1)
        lho_hcp    = HCP[lho].sum(axis=1)

        # Constraints
        mask = (dealer_hcp >= 12) & (dealer_hcp <= 14)
        mask &= (dummy_hcp >= 6)
        mask &= (lho_hcp >= 12)

        # LHO has 5+ in non-heart suit with 2+ honors
        lho_suits = lho // 13
        lho_ranks = lho % 13
        is_honor = lho_ranks >= 8  # 10, J, Q, K, A (10 is an honor in bridge)

        can_open = np.zeros(batch_size, dtype=bool)
        for suit in [0, 2, 3]:
            in_suit = lho_suits == suit
            suit_len = in_suit.sum(axis=1)
            suit_honors = (in_suit & is_honor).sum(axis=1)
            can_open |= (suit_len >= 5) & (suit_honors >= 2)
        mask &= can_open

        # King location: must be with an opponent (LHO or RHO)
        king_in_lho = (lho == K_HEARTS).any(axis=1)
        king_in_rho = (rho == K_HEARTS).any(axis=1)
        king_in_dealer = (dealer_rest == K_HEARTS).any(axis=1)
        king_in_dummy = (dummy_rest == K_HEARTS).any(axis=1)
        king_with_opp = king_in_lho | king_in_rho  # not with dealer or dummy

        # Filter: constraints met AND king is with an opponent
        valid = mask & king_with_opp
        # 1 = LHO, 0 = RHO
        results = king_in_lho[valid].astype(int)

        all_results.extend(results.tolist())
        total_match += valid.sum()
        total_sim += batch_size

    return np.array(all_results), total_sim, total_match


# ================================================================
# SCENARIO A: Dealer has J-10, Dummy has A-Q (finesse LHO)
# ================================================================
rng = np.random.default_rng(42)
print("=" * 60)
print("Scenario A: Dealer=J-10, Dummy=A-Q (finesse LHO)")
print("=" * 60)
results_a, sim_a, match_a = simulate_scenario(
    known_dealer_cards=[J_HEARTS, T_HEARTS],
    known_dummy_cards=[A_HEARTS, Q_HEARTS],
)
p_a = np.mean(results_a)
n_a = len(results_a)
ci_a = 1.96 * np.sqrt(p_a * (1 - p_a) / n_a)
print(f"Matching deals: {n_a:,} (from {sim_a:,} simulated)")
print(f"P(King with LHO) = {p_a:.4f}")
print(f"95% CI: [{p_a - ci_a:.4f}, {p_a + ci_a:.4f}]")
print(f"→ Finesse LHO works {p_a:.1%} of the time")

# ================================================================
# SCENARIO B: Dealer has A-Q, Dummy has J-10 (finesse RHO)
# ================================================================
rng = np.random.default_rng(42)
print(f"\n{'=' * 60}")
print("Scenario B: Dealer=A-Q, Dummy=J-10 (finesse RHO)")
print("=" * 60)
results_b, sim_b, match_b = simulate_scenario(
    known_dealer_cards=[A_HEARTS, Q_HEARTS],
    known_dummy_cards=[J_HEARTS, T_HEARTS],
)
# In scenario B, finesse works if King is with RHO
# results_b: 1 = King with LHO, 0 = King with RHO
# So P(finesse works) = P(King with RHO) = 1 - mean(results_b)
p_b = 1.0 - np.mean(results_b)
n_b = len(results_b)
ci_b = 1.96 * np.sqrt(p_b * (1 - p_b) / n_b)
print(f"Matching deals: {n_b:,} (from {sim_b:,} simulated)")
print(f"P(King with RHO) = {p_b:.4f}")
print(f"95% CI: [{p_b - ci_b:.4f}, {p_b + ci_b:.4f}]")
print(f"→ Finesse RHO works {p_b:.1%} of the time")

# ================================================================
# COMPARISON
# ================================================================
print(f"\n{'=' * 60}")
print("COMPARISON")
print(f"{'=' * 60}")
print(f"  Scenario A (finesse LHO, lead from dealer):  {p_a:.1%}  [{'GOOD' if p_a > 0.5 else 'BAD'}]")
print(f"  Scenario B (finesse RHO, lead from board):    {p_b:.1%}  [{'GOOD' if p_b > 0.5 else 'BAD'}]")
print(f"  Difference:                                  {p_b - p_a:+.1%}")
print()
if p_b > 0.5 and p_a < 0.5:
    print("  ✓ YES — swapping J-10 to the board flips the finesse from")
    print("    unfavorable to favorable. Leading from the board and")
    print("    finessing RHO is the correct play.")
elif p_b > p_a:
    print(f"  → Scenario B is better by {p_b - p_a:.1%} points")
else:
    print(f"  → Scenario A is better by {p_a - p_b:.1%} points")

# ================================================================
# PyMC MODEL for both scenarios
# ================================================================
print(f"\n{'=' * 60}")
print("PyMC Posterior Distributions")
print(f"{'=' * 60}")

# Scenario A: P(King with LHO)
with pm.Model() as model_a:
    p_a_pymc = pm.Beta("p_king_lho", alpha=1, beta=1)
    pm.Bernoulli("obs", p=p_a_pymc, observed=results_a)
    trace_a = pm.sample(2000, tune=1000, chains=4, random_seed=42)

# Scenario B: P(King with RHO) = 1 - P(King with LHO)
with pm.Model() as model_b:
    p_b_pymc = pm.Beta("p_king_rho", alpha=1, beta=1)
    pm.Bernoulli("obs", p=p_b_pymc, observed=1 - results_b)
    trace_b = pm.sample(2000, tune=1000, chains=4, random_seed=42)

p_a_samples = trace_a.posterior["p_king_lho"].values.flatten()
p_b_samples = trace_b.posterior["p_king_rho"].values.flatten()

hdi_a = az.hdi(p_a_samples, hdi_prob=0.94)
hdi_b = az.hdi(p_b_samples, hdi_prob=0.94)

print(f"\n  Scenario A (finesse LHO):")
print(f"    Posterior mean: {np.mean(p_a_samples):.1%}")
print(f"    94% HDI: [{float(np.ravel(hdi_a)[0]):.1%}, {float(np.ravel(hdi_a)[1]):.1%}]")
print(f"\n  Scenario B (finesse RHO):")
print(f"    Posterior mean: {np.mean(p_b_samples):.1%}")
print(f"    94% HDI: [{float(np.ravel(hdi_b)[0]):.1%}, {float(np.ravel(hdi_b)[1]):.1%}]")

# ================================================================
# PLOT
# ================================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# Scenario A posterior
az.plot_posterior(trace_a, var_names=["p_king_lho"], ax=axes[0])
axes[0].axvline(0.5, color='red', linestyle='--', alpha=0.7, label='50% (break-even)')
axes[0].set_title("Scenario A: P(finesse LHO works)\n(Dealer=J-10, Board=A-Q)")
axes[0].legend(fontsize=8)

# Scenario B posterior
az.plot_posterior(trace_b, var_names=["p_king_rho"], ax=axes[1])
axes[1].axvline(0.5, color='red', linestyle='--', alpha=0.7, label='50% (break-even)')
axes[1].set_title("Scenario B: P(finesse RHO works)\n(Dealer=A-Q, Board=J-10)")
axes[1].legend(fontsize=8)

# Comparison bar chart
labels = ['Scenario A\n(finesse LHO)', 'Scenario B\n(finesse RHO)']
means = [np.mean(p_a_samples), np.mean(p_b_samples)]
errors = [
    [np.mean(p_a_samples) - float(np.ravel(hdi_a)[0]), float(np.ravel(hdi_a)[1]) - np.mean(p_a_samples)],
    [np.mean(p_b_samples) - float(np.ravel(hdi_b)[0]), float(np.ravel(hdi_b)[1]) - np.mean(p_b_samples)],
]
errors = np.array(errors).T
colors = ['red' if m < 0.5 else 'green' for m in means]
axes[2].bar(labels, means, yerr=errors, color=colors, alpha=0.7, capsize=10)
axes[2].axhline(0.5, color='black', linestyle='--', alpha=0.5, label='50% (break-even)')
axes[2].set_ylabel("Probability finesse works")
axes[2].set_title("Finesse Comparison")
axes[2].legend(fontsize=8)
axes[2].set_ylim(0, 1)
for i, m in enumerate(means):
    axes[2].text(i, m + 0.02, f'{m:.1%}', ha='center', fontweight='bold')

plt.tight_layout()
plt.savefig("finesse_comparison.png", dpi=150)
print(f"\nPlot saved to: finesse_comparison.png")