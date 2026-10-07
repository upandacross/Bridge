import math

def comb(n, k):
    if k < 0 or k > n:
        return 0
    return math.comb(n, k)

remaining_trumps = 5
non_trumps = 21
total_ways = comb(26, 13)

print("Trump Split Distribution (5 trumps with opponents)")
print("=" * 55)
print(f"{'Split':>8} {'Probability':>14} {'Percent':>10}")
print("-" * 55)

cumulative = 0.0
for left in range(6):
    right = 5 - left
    non_needed = 13 - left
    if non_needed < 0 or non_needed > non_trumps:
        continue
    ways = comb(remaining_trumps, left) * comb(non_trumps, non_needed)
    prob = ways / total_ways
    cumulative += prob
    print(f"{left}-{right:>3} {prob:>14.10f} {prob*100:>9.4f}%")

print("-" * 55)
print(f"{'Total':>8} {cumulative:>14.10f} {cumulative*100:>9.4f}%")

p32 = 2 * comb(5, 3) * comb(21, 10) / total_ways
p41 = 2 * comb(5, 4) * comb(21, 9) / total_ways
p50 = 2 * comb(5, 5) * comb(21, 8) / total_ways

print()
print("Summary:")
print(f"  3-2 split: {p32*100:.2f}%")
print(f"  4-1 split: {p41*100:.2f}%")
print(f"  5-0 split: {p50*100:.2f}%")
