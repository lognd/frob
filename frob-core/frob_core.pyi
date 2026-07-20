"""Typed surface of the frob-core clone-detection kernels
(docs/modules/dup.md#frob-core-kernels-the-pyo3-exported-surface).

frob:describes frob-core/src/lib.rs
"""

def r3_canonical_hash(tokens: list[str]) -> str: ...
def winnow_fingerprints(tokens: list[str], k: int, w: int) -> list[int]: ...
def candidate_pairs(
    fingerprint_sets: list[list[int]], min_shared: int
) -> list[tuple[int, int]]: ...
def tree_edit_similarity(
    a: list[int], b: list[int]
) -> tuple[float, list[tuple[int, int]]]: ...
def apted_similarity(
    labels_a: list[str],
    parents_a: list[int],
    labels_b: list[str],
    parents_b: list[int],
) -> float: ...
def anti_unify(
    labels_a: list[str],
    parents_a: list[int],
    labels_b: list[str],
    parents_b: list[int],
) -> tuple[
    bool, list[str], list[int], list[tuple[int, int]], list[tuple[int, int]]
]: ...
def wl_hash(
    adjacency: list[tuple[int, int]], labels: list[str], iterations: int
) -> int: ...
def exact_regions(
    documents: list[list[str]],
    min_len: int,
    max_run_size: int = 200,
) -> tuple[list[tuple[int, int, int, int, int]], bool]: ...
