"""
Probability distribution of Total Points in a 4-hand Bridge game.

HCP (High Card Points):
    Ace   = 4 points
    King  = 3 points
    Queen = 2 points
    Jack  = 1 point
    2-10  = 0 points

Distribution points:
    Void      (0 cards in suit) = 4 points
    Singleton (1 card in suit)  = 3 points
    Doubleton (2 cards in suit) = 2 points
    Length    (5+ cards in suit) = +1 per card beyond 4
                                  (5-card suit = +1, 6-card suit = +2, etc.)

Total Points = HCP + Distribution Points

Deck: 52 cards, 4 suits × 13 cards (A K Q J 10 9 8 7 6 5 4 3 2).
Each hand is dealt 13 cards.
"""

import math
import random
from collections import Counter


HAND_SIZE = 13
DECK_SIZE = 52
SPOTS_PER_SUIT = 9   # cards 2-10
HONOURS_PER_SUIT = 4  # A, K, Q, J


def comb(n: int, k: int) -> int:
    """Binomial coefficient C(n, k)."""
    if k < 0 or k > n:
        return 0
    return math.comb(n, k)


def dist_points(suit_length: int) -> int:
    """Distribution points for a single suit."""
    if suit_length == 0:
        return 4   # void
    if suit_length == 1:
        return 3   # singleton
    if suit_length == 2:
        return 2   # doubleton
    if suit_length >= 5:
        return suit_length - 4  # length points
    return 0


# ---------------------------------------------------------------------------
# Precompute per-suit HCP possibilities
# ---------------------------------------------------------------------------
# All 16 subsets of {Ace(4), King(3), Queen(2), Jack(1)}.
# Each entry: (number_of_honours, hcp_value)
HONOUR_SUBSETS: list[tuple[int, int]] = []
for _a in (0, 1):
    for _k in (0, 1):
        for _q in (0, 1):
            for _j in (0, 1):
                HONOUR_SUBSETS.append(
                    (_a + _k + _q + _j, 4 * _a + 3 * _k + 2 * _q + 1 * _j)
                )


def suit_hcp_distribution(suit_length: int) -> dict[int, int]:
    """
    For a suit with `suit_length` cards dealt from it, return a mapping
    hcp_value -> number_of_ways to achieve that HCP.

    Each suit contains 4 honour cards and 9 spot cards (13 total).
    """
    hcp_ways: dict[int, int] = {}
    for num_h, hcp in HONOUR_SUBSETS:
        spots_needed = suit_length - num_h
        if spots_needed < 0 or spots_needed > SPOTS_PER_SUIT:
            continue
        ways = comb(SPOTS_PER_SUIT, spots_needed)
        hcp_ways[hcp] = hcp_ways.get(hcp, 0) + ways
    return hcp_ways


def convolve(d1: dict[int, int], d2: dict[int, int]) -> dict[int, int]:
    """Convolve two integer-valued distributions (sum of random variables)."""
    result: dict[int, int] = {}
    for v1, w1 in d1.items():
        for v2, w2 in d2.items():
            key = v1 + v2
            result[key] = result.get(key, 0) + w1 * w2
    return result


# ---------------------------------------------------------------------------
# Exact combinatorial calculation
# ---------------------------------------------------------------------------
def compute_exact_distributions() -> tuple[dict[int, float], dict[int, float]]:
    """
    Compute exact probability distributions for a 13-card bridge hand:
      1. HCP only
      2. Total points (HCP + distribution points)

    Method: enumerate every ordered suit-length distribution (s1,s2,s3,s4)
    with s1+s2+s3+s4 = 13.  For each, convolve the four per-suit HCP
    distributions and accumulate counts keyed by HCP and by total points.
    """
    total_hands = comb(DECK_SIZE, HAND_SIZE)

    # Cache per-suit HCP distributions by suit length
    suit_hcp = {length: suit_hcp_distribution(length) for length in range(HAND_SIZE + 1)}

    hcp_counts: dict[int, int] = {}
    tp_counts: dict[int, int] = {}

    # Enumerate all ordered 4-tuples (s1,s2,s3,s4) summing to 13
    for s1 in range(HAND_SIZE + 1):
        for s2 in range(HAND_SIZE + 1 - s1):
            for s3 in range(HAND_SIZE + 1 - s1 - s2):
                s4 = HAND_SIZE - s1 - s2 - s3

                dp = (dist_points(s1) + dist_points(s2)
                      + dist_points(s3) + dist_points(s4))

                # Convolve 4 per-suit HCP distributions
                combined = suit_hcp[s1]
                combined = convolve(combined, suit_hcp[s2])
                combined = convolve(combined, suit_hcp[s3])
                combined = convolve(combined, suit_hcp[s4])

                for hcp, ways in combined.items():
                    hcp_counts[hcp] = hcp_counts.get(hcp, 0) + ways
                    total = hcp + dp
                    tp_counts[total] = tp_counts.get(total, 0) + ways

    hcp_probs = {k: v / total_hands for k, v in sorted(hcp_counts.items())}
    tp_probs = {k: v / total_hands for k, v in sorted(tp_counts.items())}
    return hcp_probs, tp_probs


# ---------------------------------------------------------------------------
# Monte Carlo simulation
# ---------------------------------------------------------------------------
def simulate_distributions(num_deals: int = 1_000_000,
                           ) -> tuple[dict[int, float], dict[int, float]]:
    """
    Simulate random deals and record HCP and Total Points distributions.
    """
    # Build a deck: list of (suit, hcp_value)
    deck: list[tuple[int, int]] = []
    for suit in range(4):
        deck.append((suit, 4))  # Ace
        deck.append((suit, 3))  # King
        deck.append((suit, 2))  # Queen
        deck.append((suit, 1))  # Jack
        for _ in range(SPOTS_PER_SUIT):
            deck.append((suit, 0))

    hcp_counter: Counter[int] = Counter()
    tp_counter: Counter[int] = Counter()

    for _ in range(num_deals):
        hand = random.sample(deck, HAND_SIZE)

        hcp = sum(v for _, v in hand)

        suit_lengths = [0, 0, 0, 0]
        for s, _ in hand:
            suit_lengths[s] += 1

        dp = sum(dist_points(l) for l in suit_lengths)

        hcp_counter[hcp] += 1
        tp_counter[hcp + dp] += 1

    hcp_probs = {k: v / num_deals for k, v in sorted(hcp_counter.items())}
    tp_probs = {k: v / num_deals for k, v in sorted(tp_counter.items())}
    return hcp_probs, tp_probs


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------
def mean_of(dist: dict[int, float]) -> float:
    return sum(k * p for k, p in dist.items())


def std_of(dist: dict[int, float]) -> float:
    mu = mean_of(dist)
    var = sum(k ** 2 * p for k, p in dist.items()) - mu ** 2
    return var ** 0.5


def range_prob(dist: dict[int, float], lo: int, hi: int) -> float:
    return sum(dist.get(k, 0.0) for k in range(lo, hi + 1))


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
def print_table(title: str,
                exact: dict[int, float],
                simulated: dict[int, float]) -> None:
    """Print a single distribution table."""
    all_keys = sorted(set(exact) | set(simulated))

    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)
    print()
    print(f"  {'Pts':>4}  {'Exact Prob':>12}  {'Simulated':>12}"
          f"  {'Exact %':>9}  {'Cumul %':>9}")
    print(f"  {'---':>4}  {'----------':>12}  {'---------':>12}"
          f"  {'-------':>9}  {'-------':>9}")

    cumulative = 0.0
    for pts in all_keys:
        prob = exact.get(pts, 0.0)
        if prob < 1e-12 and simulated.get(pts, 0.0) == 0.0:
            continue
        cumulative += prob
        sim = simulated.get(pts, 0.0)
        print(f"  {pts:>4}  {prob:>12.8f}  {sim:>12.8f}"
              f"  {prob * 100:>8.4f}%  {cumulative * 100:>8.4f}%")

    print()
    print(f"  Sum of exact probabilities: {sum(exact.values()):.10f}")


def print_stats(label: str, dist: dict[int, float]) -> None:
    mu = mean_of(dist)
    sd = std_of(dist)
    print(f"  {label}")
    print(f"    Mean:   {mu:.4f}")
    print(f"    StdDev: {sd:.4f}")


def print_ranges(title: str, dist: dict[int, float],
                 ranges: list[tuple[str, int, int]]) -> None:
    print()
    print(f"  {title}")
    print("  " + "-" * 50)
    for label, lo, hi in ranges:
        p = range_prob(dist, lo, hi)
        print(f"  {label:40s}  {p * 100:8.4f}%")


def main() -> None:
    print("\nComputing exact distributions (HCP and Total Points)...")
    exact_hcp, exact_tp = compute_exact_distributions()

    print("Running Monte Carlo simulation (1,000,000 deals)...")
    sim_hcp, sim_tp = simulate_distributions(1_000_000)

    # ---- HCP table ----
    print_table("HCP Distribution (High Card Points only)", exact_hcp, sim_hcp)
    print()
    print_stats("HCP Statistics", exact_hcp)

    # ---- Total Points table ----
    print_table(
        "Total Points Distribution (HCP + Distribution Points)\n"
        "    Void=4  Singleton=3  Doubleton=2  Length(5+)=cards-4",
        exact_tp, sim_tp,
    )
    print()
    print_stats("Total Points Statistics", exact_tp)

    # ---- Useful bridge ranges (Total Points) ----
    print_ranges(
        "Opening Ranges (Total Points)",
        exact_tp,
        [
            ("0-5   (pass)",                  0,  5),
            ("6-9   (respond, no open)",       6,  9),
            ("10-11 (marginal open)",         10, 11),
            ("12-14 (open / weak NT)",        12, 14),
            ("15-17 (strong NT)",             15, 17),
            ("18-19 (strong hand)",           18, 19),
            ("20-21 (2NT / strong 2)",        20, 21),
            ("22+   (game force)",            22, 50),
        ],
    )

    # ---- Partnership combined (approximate convolution) ----
    combined: dict[int, float] = {}
    for h1, p1 in exact_tp.items():
        for h2, p2 in exact_tp.items():
            t = h1 + h2
            combined[t] = combined.get(t, 0.0) + p1 * p2

    print_ranges(
        "Partnership Combined Total Points (independence approx.)",
        combined,
        [
            ("20-22 (possible part score)",      20, 22),
            ("23-25 (game invite)",              23, 25),
            ("26-28 (game likely)",              26, 28),
            ("29-32 (slam invite)",              29, 32),
            ("33-36 (small slam)",               33, 36),
            ("37-40 (grand slam)",               37, 40),
        ],
    )
    print()


if __name__ == "__main__":
    main()
