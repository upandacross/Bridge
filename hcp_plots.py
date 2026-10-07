"""
Generate PNG plots of HCP and Total Points probability distributions
for a 13-card Bridge hand.
"""

import matplotlib
matplotlib.use("Agg")  # non-interactive backend

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from hcp_distribution import compute_exact_distributions


def style_ax(ax, title, xlabel, ylabel):
    """Apply consistent styling to an axes."""
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=1))
    ax.grid(axis="y", alpha=0.3, linewidth=0.5)


def plot_single_distribution(dist: dict[int, float],
                             title: str,
                             colour: str,
                             filename: str,
                             mean: float,
                             std: float) -> None:
    """Bar chart of a single probability distribution."""
    keys = sorted(dist.keys())
    vals = [dist[k] for k in keys]

    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.bar(keys, vals, color=colour, edgecolor="white", linewidth=0.4)

    # Highlight the mode
    mode_idx = int(np.argmax(vals))
    bars[mode_idx].set_edgecolor("black")
    bars[mode_idx].set_linewidth(1.5)

    # Mean / std lines
    ax.axvline(mean, color="red", linestyle="--", linewidth=1.2, label=f"Mean = {mean:.2f}")
    ax.axvline(mean - std, color="orange", linestyle=":", linewidth=1, label=f"±1 SD = {std:.2f}")
    ax.axvline(mean + std, color="orange", linestyle=":", linewidth=1)

    style_ax(ax, title, "Points", "Probability")
    ax.legend(fontsize=9, loc="upper right")

    fig.tight_layout()
    fig.savefig(filename, dpi=180)
    plt.close(fig)
    print(f"  Saved {filename}")


def plot_cumulative(dist: dict[int, float],
                    title: str,
                    colour: str,
                    filename: str) -> None:
    """Cumulative distribution function plot."""
    keys = sorted(dist.keys())
    cum = np.cumsum([dist[k] for k in keys])

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.step(keys, cum, where="mid", color=colour, linewidth=2)
    ax.fill_between(keys, cum, step="mid", alpha=0.15, color=colour)

    # Reference lines at common thresholds
    for pct, label in [(0.25, "25%"), (0.50, "50%"), (0.75, "75%"), (0.90, "90%")]:
        ax.axhline(pct, color="grey", linestyle=":", linewidth=0.7, alpha=0.6)
        ax.text(keys[-1] + 0.5, pct, label, va="center", fontsize=8, color="grey")

    style_ax(ax, title, "Points", "Cumulative Probability")

    fig.tight_layout()
    fig.savefig(filename, dpi=180)
    plt.close(fig)
    print(f"  Saved {filename}")


def plot_comparison(hcp: dict[int, float],
                    tp: dict[int, float],
                    filename: str) -> None:
    """Overlay HCP and Total Points distributions for comparison."""
    all_keys = sorted(set(hcp) | set(tp))
    hcp_vals = [hcp.get(k, 0.0) for k in all_keys]
    tp_vals = [tp.get(k, 0.0) for k in all_keys]

    width = 0.4
    x = np.array(all_keys, dtype=float)

    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.bar(x - width / 2, hcp_vals, width, label="HCP Only", color="#4C72B0",
           edgecolor="white", linewidth=0.3, alpha=0.85)
    ax.bar(x + width / 2, tp_vals, width, label="Total Points (HCP + Dist)",
           color="#DD8452", edgecolor="white", linewidth=0.3, alpha=0.85)

    style_ax(ax, "HCP vs Total Points Distribution", "Points", "Probability")
    ax.legend(fontsize=10)

    fig.tight_layout()
    fig.savefig(filename, dpi=180)
    plt.close(fig)
    print(f"  Saved {filename}")


def plot_opening_ranges(dist: dict[int, float], filename: str) -> None:
    """Horizontal bar chart of opening-range probabilities (Total Points)."""
    ranges = [
        ("0–5\nPass",          0,  5, "#b0b0b0"),
        ("6–9\nRespond",       6,  9, "#7fbfff"),
        ("10–11\nMarginal",   10, 11, "#5fa0e0"),
        ("12–14\nOpen / 1NT", 12, 14, "#3080c0"),
        ("15–17\nStrong NT",  15, 17, "#1a6aab"),
        ("18–19\nStrong",     18, 19, "#0d4f8a"),
        ("20–21\n2NT / 2♣",   20, 21, "#08386b"),
        ("22+\nGame Force",   22, 50, "#042040"),
    ]

    labels = [r[0] for r in ranges]
    probs = [sum(dist.get(k, 0.0) for k in range(lo, hi + 1))
             for _, lo, hi, _ in ranges]
    colours = [r[3] for r in ranges]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(labels, probs, color=colours, edgecolor="white", linewidth=0.5)

    for bar, p in zip(bars, probs):
        ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height() / 2,
                f"{p * 100:.1f}%", va="center", fontsize=9)

    ax.set_title("Probability by Opening Range (Total Points)",
                 fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Probability", fontsize=11)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3, linewidth=0.5)

    fig.tight_layout()
    fig.savefig(filename, dpi=180)
    plt.close(fig)
    print(f"  Saved {filename}")


def main() -> None:
    print("Computing exact distributions...")
    hcp, tp = compute_exact_distributions()

    hcp_mean = sum(k * p for k, p in hcp.items())
    hcp_std = (sum(k**2 * p for k, p in hcp.items()) - hcp_mean**2) ** 0.5
    tp_mean = sum(k * p for k, p in tp.items())
    tp_std = (sum(k**2 * p for k, p in tp.items()) - tp_mean**2) ** 0.5

    print("Generating plots...")

    plot_single_distribution(
        hcp,
        "HCP Probability Distribution (13-card Bridge Hand)",
        "#4C72B0",
        "hcp_distribution.png",
        hcp_mean, hcp_std,
    )

    plot_single_distribution(
        tp,
        "Total Points Distribution  (HCP + Void=4 / Singleton=3 / Doubleton=2 / Length)",
        "#DD8452",
        "total_points_distribution.png",
        tp_mean, tp_std,
    )

    plot_cumulative(
        hcp,
        "HCP Cumulative Distribution",
        "#4C72B0",
        "hcp_cumulative.png",
    )

    plot_cumulative(
        tp,
        "Total Points Cumulative Distribution",
        "#DD8452",
        "total_points_cumulative.png",
    )

    plot_comparison(hcp, tp, "hcp_vs_total_points.png")

    plot_opening_ranges(tp, "opening_ranges.png")

    print("\nDone — 6 PNG files generated.")


if __name__ == "__main__":
    main()
