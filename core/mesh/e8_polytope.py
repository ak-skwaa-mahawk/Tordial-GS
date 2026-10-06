"""E8 Gosset Polytope (4_21) Root Generator.

Generates the 240 canonical roots of the E8 Lie algebra:
1. 112 vectors: permutations of (+-1, +-1, 0, 0, 0, 0, 0, 0)
2. 128 vectors: (+-1/2, +-1/2, ..., +-1/2) with an even number of minus signs.
"""

from itertools import combinations, product

def generate_e8_roots() -> list[tuple[float, ...]]:
    roots = set()

    # 1. Type D8: (+-1, +-1, 0, 0, 0, 0, 0, 0)
    for pos in combinations(range(8), 2):
        for s1, s2 in product([-1.0, 1.0], repeat=2):
            vec = [0.0] * 8
            vec[pos[0]] = s1
            vec[pos[1]] = s2
            roots.add(tuple(vec))

    # 2. Type Spinor: (+-0.5, ..., +-0.5) with even sum of negative signs
    for signs in product([-0.5, 0.5], repeat=8):
        negative_count = sum(1 for s in signs if s < 0)
        if negative_count % 2 == 0:
            roots.add(signs)

    sorted_roots = sorted(list(roots))
    assert len(sorted_roots) == 240, f"Expected 240 roots, got {len(sorted_roots)}"
    return sorted_roots

def get_root_vector(index: int) -> tuple[float, ...]:
    """Retrieve 0-indexed root vector (0 <= index < 240)."""
    if not 0 <= index < 240:
        raise ValueError(f"Root index {index} out of bounds (0-239).")
    roots = generate_e8_roots()
    return roots[index]

if __name__ == "__main__":
    roots = generate_e8_roots()
    print(f"[+] Successfully generated {len(roots)} E8 lattice roots.")
    print(f"[*] Sample Root #0:   {roots[0]}")
    print(f"[*] Sample Root #12:  {roots[12]}")
    print(f"[*] Sample Root #48:  {roots[48]}")
    print(f"[*] Sample Root #120: {roots[120]}")
