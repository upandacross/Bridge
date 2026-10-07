"""
Probability distribution of how remaining trumps split between opponents.

Given:
  - Partnership holds 8 trumps (between their 26 cards)
  - 5 trumps remain in the opponents' 26 cards
  - 21 non-trump cards also in opponents' hands (26 total non-trumps - 5 held by partnership)

Each opponent holds 13 of the 26 opponent cards.
We compute P(k trump cards with LHO, 5-k with RHO) for k = 0, 1, 2, 3, 4, 5.

This is a hypergeometric distribution:
  P(k) = C(5, k) × C(21, 13-k) / C(26, 13)
"""

import math
from collections import defaultdict


def comb(n: int, k: int) -> int:
    """Binomial coefficient C(n, k)."""
    if k < 0 or k > n:
        return 0
    return math.comb(n, k)


def trump_split_distribution(remaining_trumps: int = 5,
                              opponent_cards: int = 26,
                              cards_per_opponent: int = 13) -> dict[tuple[int, int], float]:
    """
    Compute the probability distribution of trump splits.

    Args:
        remaining_trumps: Number of trumps in opponents' hands (5 when partnership has 8)
        opponent_cards: Total cards held by both opponents (26)
        cards_per_opponent: Cards held by each opponent (13)

    Returns:
        Dict mapping (left_trumps, right_trumps) -> probability
    """
    non_trumps = opponent_cards - remaining_trumps  # 21 when 5 trumps remain

    total_ways = comb(opponent_cards, cards_per_opponent)

    dist: dict[tuple[int, int], float] = {}

    for left_trumps in range(remaining_trumps + 1):
        right_trumps = remaining_trumps - left_trumps

        # Left opponent needs (cards_per_opponent - left_trumps) non-trumps
        non_trumps_needed = cards_per_opponent - left_trumps
        if non_trumps_needed < 0 or non_trumps_needed > non_trumps:
            continue

        ways = comb(remaining_trumps, left_trumps) * comb(non_trumps, non_trumps_needed)
        prob = ways / total_ways
        dist[(left_trumps, right_trumps)] = prob

    return dist


def print_distribution(dist: dict[tuple[int, int], float],
                       partnership_trumps: int = 8) -> None:
    """Print a formatted table of the trump split distribution."""

    remaining = 13 - partnership_trumps + 13 - partnership_trumps
    # Actually: partnership has 26 cards with 8 trumps, so opponents have 26 cards with 5 trumps

    print("=" * 70)
    print(f"  Trump Split Distribution (Partnership has {partnership_trumps} trumps)")
    print(f"  Remaining {13 * 4 - 26 - (13 - partnership_trumps * 2)} trumps in opponents' 26 cards")
    print("=" * 70)
    print()

    # Group by split type (0-5, 1-4, 2-3, etc.)
    split_probs: dict[str, float] = defaultdict(float)

    print(f"  {'Split':>10}  {'Exact Prob':>14}  {'Percent':>10}  {'Cumul %':>10}")
    print(f"  {'------':>10}  {'----------':>14}  {'-------':>10}  {'-------':>10}")

    cumulative = 0.0
    for (left, right), prob in sorted(dist.items()):
        split_label = f"{left}-{right}"
        cumulative += prob
        pct = prob * 100
        cum_pct = cumulative * 100
        split_probs[split_label] = prob
        print(f"  {split_label:>10}  {prob:>14.10f}  {pct:>9.4f}%  {cum_pct:>9.4f}%")

    print()
    print(f"  Sum of probabilities: {sum(dist.values()):.10f}")
    print()

    # Summary: group symmetric splits
    print("  Summary by Split Type")
    print("  " + "-" * 50)

    # 3-2 includes both 3-2 and 2-3
    prob_3_2 = dist.get((3, 2), 0) + dist.get((2, 3), 0)
    prob_4_1 = dist.get((4, 1), 0) + dist.get((1, 4), 0)
    prob_5_0 = dist.get((5, 0), 0) + dist.get((0, 5), 0)

    print(f"  {'3-2 split':>20s}  {prob_3_2:>12.10f}  ({prob_3_2 * 100:6.2f}%)")
    print(f"  {'4-1 split':>20s}  {prob_4_1:>12.10f}  ({prob_4_1 * 100:6.2f}%)")
    print(f"  {'5-0 split':>20s}  {prob_5_0:>12.10f}  ({prob_5_0 * 100:6.2f}%)")
    print()

    # Common bridge heuristics
    print("  Bridge Heuristics / Rules of Thumb")
    print("  " + "-" * 50)
    print(f"  'Five trumps out: expect 3-2'    Actual: {prob_3_2 * 100:.1f}%")
    print(f"  '4-1 or worse break':            Actual: {(prob_4_1 + prob_5_0) * 100:.1f}%")
    print(f"  'No worse than 4-1':             Actual: {(prob_3_2 + prob_4_1) * 100:.1f}%")
    print()

    return split_probs


def print_general_table() -> None:
    """Print a general table for various partnership trump holdings."""
    print("=" * 70)
    print("  Trump Split Probabilities for Various Partnership Holdings")
    print("=" * 70)
    print()

    print(f"  {'Partnership':>12}  {'Remaining':>10}  {'3-2 or':>10}  {'4-1 or':>10}  {'5-0':>10}")
    print(f"  {'Trumps':>12}  {'Trumps':>10}  {'better':>10}  {'worse':>10}  {'split':>10}")
    print(f"  {'------------':>12}  {'----------':>10}  {'----------':>10}  {'----------':>10}  {'----------':>10}")

    for partnership_trumps in range(7, 14):
        remaining = 13 * 2 - partnership_trumps  # trumps remaining with opponents

        # Compute distribution
        dist = trump_split_distribution(remaining)

        # Calculate probabilities for "X-Y or better" splits
        # For remaining trumps r, we want probability of splits that are "reasonable"
        if remaining == 5:
            prob_3_2_or_better = sum(dist.get((3, 2), 0), dist.get((2, 3), 0))
            prob_4_1_or_worse = sum(dist.get((4, 1), 0), dist.get((1, 4), 0),
                                    dist.get((5, 0), 0), dist.get((0, 5), 0))
            prob_5_0 = sum(dist.get((5, 0), 0), dist.get((0, 5), 0))
        elif remaining == 4:
            prob_3_2_or_better = sum(dist.get((3, 1), 0), dist.get((1, 3), 0),
                                     dist.get((2, 2), 0))
            prob_4_1_or_worse = sum(dist.get((4, 0), 0), dist.get((0, 4), 0))
            prob_5_0 = 0.0
        elif remaining == 3:
            prob_3_2_or_better = sum(dist.get((2, 1), 0), dist.get((1, 2), 0),
                                     dist.get((3, 0), 0), dist.get((0, 3), 0))
            prob_4_1_or_worse = 0.0
            prob_5_0 = 0.0
        else:
            # For other cases, just compute sum
            prob_3_2_or_better = sum(p for (_, _), p in dist.items())
            prob_4_1_or_worse = 0.0
            prob_5_0 = 0.0

        print(f"  {partnership_trumps:>11d}  {remaining:>10d}  {prob_3_2_or_better * 100:>9.2f}%  "
              f"{prob_4_1_or_worse * 100:>9.2f}%  {prob_5_0 * 100:>9.2f}%")

    print()


def main() -> None:
    print()

    # Main result: 8 trumps held, 5 remaining
    dist = trump_split_distribution(remaining_trumps=5)
    print_distribution(dist, partnership_trumps=8)

    # General table
    print_general_table()


if __name__ == "__main__":
    main()
