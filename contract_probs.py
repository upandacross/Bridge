"""
Simulate bridge deals to compute the probability of a partnership having
enough HCP for each contract level: part-score, NT game, major game,
minor game, small slam, grand slam.

Output: PNG table + histogram of partnership HCP distribution.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.gridspec as gridspec

rng = np.random.default_rng(42)

# ================================================================
# HCP TABLE: A=4, K=3, Q=2, J=1
# ================================================================
hcp_table = np.zeros(52)
for c in range(52):
    rank = c % 13
    if rank == 12: hcp_table[c] = 4   # A
    elif rank == 11: hcp_table[c] = 3 # K
    elif rank == 10: hcp_table[c] = 2 # Q
    elif rank == 9:  hcp_table[c] = 1 # J

# ================================================================
# SIMULATE DEALS (vectorized, 1 million)
# ================================================================
batch_size = 100_000
n_batches = 10
all_hcp = []

print("Simulating 1,000,000 bridge deals...")
for b in range(n_batches):
    sort_keys = rng.random((batch_size, 52))
    deals = np.argsort(sort_keys, axis=1)

    # Partnership: hand 0 (13 cards) + hand 2 (13 cards)
    h1 = hcp_table[deals[:, :13]].sum(axis=1)
    h2 = hcp_table[deals[:, 26:39]].sum(axis=1)
    all_hcp.extend((h1 + h2).tolist())
    print(f"  Batch {b+1}/{n_batches} done")

total_hcp = np.array(all_hcp)
n = len(total_hcp)

# ================================================================
# CONTRACT LEVELS
# ================================================================
contracts = [
    # (name,           tricks, min_hcp, max_hcp)
    ("Part-score",       "0–8",   0, 24),
    ("NT Game (3NT)",     "9",    25, 25),
    ("Major Game (4♥/4♠)","10",   26, 28),
    ("Minor Game (5♣/5♦)","11",   29, 32),
    ("Small Slam (6x)",   "12",   33, 36),
    ("Grand Slam (7x)",   "13",   37, 40),
]

# Compute probabilities
rows = []
for name, tricks, lo, hi in contracts:
    p_cumulative = np.mean(total_hcp >= lo)  # P(HCP >= threshold)
    p_range = np.mean((total_hcp >= lo) & (total_hcp <= hi))  # P(in this range)
    rows.append((name, tricks, lo, hi, p_cumulative, p_range))

# Print results
print(f"\n{'='*65}")
print(f"Partnership HCP Distribution (n={n:,})")
print(f"{'='*65}")
print(f"{'Contract':<22} {'Tricks':>7} {'HCP':>8} {'P(≥HCP)':>10} {'P(range)':>10}")
print(f"{'-'*65}")
for name, tricks, lo, hi, p_cum, p_range in rows:
    hcp_str = f"{lo}" if lo == hi else f"{lo}–{hi}"
    print(f"{name:<22} {tricks:>7} {hcp_str:>8} {p_cum:>10.2%} {p_range:>10.2%}")
print(f"{'-'*65}")
print(f"Mean HCP: {np.mean(total_hcp):.2f}")
print(f"Std:      {np.std(total_hcp):.2f}")
print(f"Median:   {np.median(total_hcp):.0f}")

# ================================================================
# FIGURE: Table + Histogram
# ================================================================
fig = plt.figure(figsize=(14, 9))
gs = gridspec.GridSpec(2, 1, height_ratios=[1.2, 1], hspace=0.15)

# --- TABLE (top) ---
ax_table = fig.add_subplot(gs[0])
ax_table.axis('off')
ax_table.set_title("Bridge Contract Probabilities by Partnership HCP",
                     fontsize=16, fontweight='bold', pad=15)

col_labels = ["Contract Level", "Tricks", "HCP Range", "P(HCP ≥ min)",
              "P(in range)", "Odds (≥ min)"]

table_data = []
for name, tricks, lo, hi, p_cum, p_range in rows:
    hcp_str = f"{lo}" if lo == hi else f"{lo}–{hi}"
    if p_cum > 0:
        odds = f"1 : {1/p_cum - 1:.1f}" if p_cum < 1 else "—"
    else:
        odds = "—"
    table_data.append([name, tricks, hcp_str, f"{p_cum:.2%}", f"{p_range:.2%}", odds])

# Colors for each contract level
colors = ['#E8F5E9', '#E3F2FD', '#FFF3E0', '#FFF9C4', '#FCE4EC', '#F3E5F5']

table = ax_table.table(
    cellText=table_data,
    colLabels=col_labels,
    cellLoc='center',
    loc='center',
    colWidths=[0.22, 0.10, 0.12, 0.14, 0.14, 0.14],
)
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1, 2.0)

# Style header
for j in range(len(col_labels)):
    cell = table[0, j]
    cell.set_facecolor('#37474F')
    cell.set_text_props(color='white', fontweight='bold', fontsize=11)

# Style rows
for i in range(len(table_data)):
    for j in range(len(col_labels)):
        cell = table[i + 1, j]
        cell.set_facecolor(colors[i])
        if j == 0:
            cell.set_text_props(fontweight='bold')
        if j in (3, 4):
            cell.set_text_props(fontsize=10)

# --- HISTOGRAM (bottom) ---
ax_hist = fig.add_subplot(gs[1])

# Compute histogram
values, bin_edges = np.histogram(total_hcp, bins=range(0, 42), density=True)
bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

# Color bars by contract level
bar_colors = []
for hcp_val in bin_centers:
    if hcp_val < 25:
        bar_colors.append('#81C784')  # green - part-score
    elif hcp_val < 26:
        bar_colors.append('#64B5F6')  # blue - NT game
    elif hcp_val < 29:
        bar_colors.append('#FFB74D')  # orange - major game
    elif hcp_val < 33:
        bar_colors.append('#FFF176')  # yellow - minor game
    elif hcp_val < 37:
        bar_colors.append('#F48FB1')  # pink - small slam
    else:
        bar_colors.append('#CE93D8')  # purple - grand slam

ax_hist.bar(bin_centers, values, width=0.8, color=bar_colors, edgecolor='white', linewidth=0.3)

# Vertical lines at thresholds
thresholds = [
    (25, "3NT", '#1976D2'),
    (26, "4M", '#F57C00'),
    (29, "5m", '#FBC02D'),
    (33, "6x", '#C2185B'),
    (37, "7x", '#7B1FA2'),
]
for hcp_val, label, color in thresholds:
    ax_hist.axvline(hcp_val, color=color, linestyle='--', alpha=0.8, linewidth=1.5)
    y_pos = max(values) * 0.95
    ax_hist.text(hcp_val + 0.3, y_pos, label, fontsize=9, color=color,
                fontweight='bold', va='top')

# Cumulative line on secondary axis
ax_cum = ax_hist.twinx()
cumulative = np.cumsum(values) * (bin_centers[1] - bin_centers[0])
ax_cum.plot(bin_centers, cumulative, 'k-', linewidth=1.5, alpha=0.5, label='CDF')
ax_cum.set_ylabel('Cumulative Probability', fontsize=10)
ax_cum.set_ylim(0, 1.05)
ax_cum.set_yticks([0, 0.25, 0.5, 0.75, 1.0])

ax_hist.set_xlabel('Partnership HCP', fontsize=11)
ax_hist.set_ylabel('Probability', fontsize=11)
ax_hist.set_title('Partnership HCP Distribution (1,000,000 simulated deals)',
                   fontsize=12, fontweight='bold')
ax_hist.set_xlim(-0.5, 41)
ax_hist.set_xticks(range(0, 41, 2))
ax_hist.grid(axis='y', alpha=0.3)

# Legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#81C784', label='Part-score (<25)'),
    Patch(facecolor='#64B5F6', label='NT Game (25)'),
    Patch(facecolor='#FFB74D', label='Major Game (26–28)'),
    Patch(facecolor='#FFF176', label='Minor Game (29–32)'),
    Patch(facecolor='#F48FB1', label='Small Slam (33–36)'),
    Patch(facecolor='#CE93D8', label='Grand Slam (37+)'),
]
ax_hist.legend(handles=legend_elements, loc='upper right', fontsize=8, ncol=2)

plt.savefig("contract_probabilities.png", dpi=150, bbox_inches='tight')
print(f"\nPlot saved to: contract_probabilities.png")