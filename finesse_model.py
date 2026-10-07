"""
Bayesian model for estimating the probability that a finesse for the King works.

Scenario:
- Dealer holds: 10-J in the suit
- Board (dummy) holds: A-Q in the suit
- We are finessing the Queen, which works if the King is with LHO
- Opponent to the LEFT (LHO) opened the bidding (in a DIFFERENT suit)
- Dealer has 13 HCP
- Dealer's partner (dummy) has 6+ HCP
- We hold all honors in our suit except the King

Two sources of evidence:
  1. HCP evidence: If LHO has the King (+3 HCP), they're more likely to
     reach the 12 HCP opening threshold. We observed LHO opened.
     → Pushes P(King with LHO) UP

  2. Card distribution (vacant places): LHO has 5+ cards in their opening
     suit, leaving fewer slots for our suit. RHO has all 13 slots open.
     → Pushes P(King with LHO) DOWN

The model combines both, starting from a 50-50 prior.
"""

import pymc as pm
import numpy as np
import arviz as az
import matplotlib.pyplot as plt

np.random.seed(42)

# ---- Constants ----
TOTAL_HCP = 40
DEALER_HCP = 13
PARTNER_MIN_HCP = 6
KING_HCP = 3
OPEN_THRESHOLD = 12
RHO_TOTAL_CARDS = 13  # RHO has 13 cards, all "vacant" (unknown distribution)


def opening_probability(hcp, steepness=2.0):
    """Sigmoid mapping HCP to probability of opening, centered at 12 HCP."""
    return pm.math.sigmoid((hcp - OPEN_THRESHOLD) * steepness)


with pm.Model() as bridge_model:
    # ================================================================
    # LATENT VARIABLE: King's location (prior = 50-50)
    # ================================================================
    king_with_lho = pm.Bernoulli("king_with_lho", p=0.5)

    # ================================================================
    # HCP EVIDENCE (pushes P(King with LHO) UP)
    # ================================================================

    # Partner HCP (at least 6, as given)
    partner_hcp = pm.TruncatedNormal(
        "partner_hcp", mu=9, sigma=3, lower=PARTNER_MIN_HCP, upper=18
    )

    # Non-King opponent HCP (total minus dealer, partner, and King's 3 HCP)
    opp_non_king_hcp = pm.Deterministic(
        "opp_non_king_hcp", TOTAL_HCP - DEALER_HCP - partner_hcp - KING_HCP
    )

    # LHO's share of non-King HCP (prior: roughly 50-50)
    lho_hcp_share = pm.Beta("lho_hcp_share", alpha=3, beta=3)
    lho_non_king_hcp = pm.Deterministic(
        "lho_non_king_hcp", opp_non_king_hcp * lho_hcp_share
    )

    # LHO's total HCP = non-King HCP + 3 if King is with LHO
    lho_hcp = pm.Deterministic(
        "lho_hcp", lho_non_king_hcp + KING_HCP * king_with_lho
    )

    # Evidence: LHO opened (observed = True)
    p_open = pm.Deterministic("p_open", opening_probability(lho_hcp))
    lho_opens = pm.Bernoulli("lho_opens", p=p_open, observed=1)

    # ================================================================
    # CARD DISTRIBUTION EVIDENCE (pushes P(King with LHO) DOWN)
    # ================================================================

    # LHO's opening suit length (5+ for a major suit opening)
    lho_open_len = pm.TruncatedNormal(
        "lho_open_len", mu=5.5, sigma=0.7, lower=5, upper=8
    )

    # LHO's vacant places = cards NOT in the opening suit
    lho_vacant = pm.Deterministic("lho_vacant", 13 - lho_open_len)

    # Card-based probability King is with LHO (vacant places principle)
    # LHO has `lho_vacant` slots for our suit; RHO has 13 slots
    p_king_card = pm.Deterministic(
        "p_king_card", lho_vacant / (lho_vacant + RHO_TOTAL_CARDS)
    )

    # Soft evidence: vacant places act as a "prior" on King's location
    # log P(King with LHO | card dist) ∝ king_with_lho * log(p_king_card)
    #                                      + (1 - king_with_lho) * log(1 - p_king_card)
    pm.Potential(
        "card_evidence",
        king_with_lho * pm.math.log(p_king_card)
        + (1 - king_with_lho) * pm.math.log(1 - p_king_card),
    )

    # ================================================================
    # FOR REPORTING
    # ================================================================
    opp_total_hcp = pm.Deterministic(
        "opp_total_hcp", TOTAL_HCP - DEALER_HCP - partner_hcp
    )
    rho_hcp = pm.Deterministic("rho_hcp", opp_total_hcp - lho_hcp)

    # ================================================================
    # SAMPLE
    # PyMC auto-assigns Metropolis to discrete (king_with_lho),
    # NUTS to continuous variables.
    # ================================================================
    trace = pm.sample(
        2000, tune=1000, chains=4, target_accept=0.9, random_seed=42
    )


# ================================================================
# RESULTS
# ================================================================
print("=" * 60)
print("Bayesian Finesse Model — HCP + Vacant Places")
print("=" * 60)

summary = az.summary(trace, var_names=[
    "king_with_lho", "partner_hcp", "opp_total_hcp", "opp_non_king_hcp",
    "lho_non_king_hcp", "lho_hcp", "rho_hcp",
    "lho_hcp_share", "lho_open_len", "lho_vacant",
    "p_open", "p_king_card",
])
print(summary)

# Key results
king_samples = trace.posterior["king_with_lho"].values.flatten()
p_card_samples = trace.posterior["p_king_card"].values.flatten()
lho_hcp_samples = trace.posterior["lho_hcp"].values.flatten()

mean_prob = np.mean(king_samples)
mean_card = np.mean(p_card_samples)
mean_lho_hcp = np.mean(lho_hcp_samples)

hdi = az.hdi(king_samples, hdi_prob=0.94)
hdi_lower = float(np.ravel(hdi)[0])
hdi_upper = float(np.ravel(hdi)[1])

print(f"\n{'─' * 60}")
print(f"COMBINED RESULT (HCP + Vacant Places)")
print(f"{'─' * 60}")
print(f"P(finesse works | LHO opened + vacant places) = {mean_prob:.1%}")
print(f"94% HDI: [{hdi_lower:.1%}, {hdi_upper:.1%}]")
print(f"\nFor comparison:")
print(f"  Prior (no evidence):              50.0%")
print(f"  HCP-only model (previous):        74.4%")
print(f"  Card-based (vacant places alone):  {mean_card:.1%}")
print(f"  Combined (this model):             {mean_prob:.1%}")
print(f"\nLHO mean HCP: {mean_lho_hcp:.1f}")
print(f"{'─' * 60}")

# ================================================================
# PLOTS
# ================================================================
fig, axes = plt.subplots(2, 2, figsize=(12, 9))

# 1. Posterior of king_with_lho (main result)
az.plot_posterior(trace, var_names=["king_with_lho"], ax=axes[0, 0])
axes[0, 0].set_title("P(Finesse Works) — Combined Evidence")
axes[0, 0].axvline(0.5, color="gray", linestyle="--", alpha=0.7, label="Prior (50%)")
axes[0, 0].axvline(0.744, color="orange", linestyle="--", alpha=0.7, label="HCP-only (74.4%)")
axes[0, 0].axvline(mean_prob, color="red", linestyle="-", alpha=0.7, label=f"Combined ({mean_prob:.1%})")
axes[0, 0].legend(fontsize=8)

# 2. Card-based probability (vacant places)
az.plot_posterior(trace, var_names=["p_king_card"], ax=axes[0, 1])
axes[0, 1].set_title("Card-Based P(King with LHO)\n(Vacant Places — pulls DOWN)")
axes[0, 1].axvline(0.5, color="gray", linestyle="--", alpha=0.7, label="Prior (50%)")
axes[0, 1].legend(fontsize=8)

# 3. LHO HCP posterior
az.plot_posterior(trace, var_names=["lho_hcp"], ax=axes[1, 0])
axes[1, 0].set_title("LHO HCP (King adds 3 if with LHO)")
axes[1, 0].axvline(OPEN_THRESHOLD, color="red", linestyle="--", alpha=0.7, label="Open threshold (12)")
axes[1, 0].legend(fontsize=8)

# 4. LHO opening suit length
az.plot_posterior(trace, var_names=["lho_open_len"], ax=axes[1, 1])
axes[1, 1].set_title("LHO Opening Suit Length\n(More length → fewer vacant places)")

plt.tight_layout()
plt.savefig("finesse_combined.png", dpi=150)
print(f"\nPlot saved to: finesse_combined.png")