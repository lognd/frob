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

# T-0930: frob.graph.callgraph kernels -- see docs/modules/graph.md#rust-core.
def resolve_call_edges(
    callers: list[str],
    names_per_caller: list[list[str]],
    exempt_per_caller: list[list[str]],
    by_name: dict[str, list[tuple[str, str, bool]]],
    mark_unresolved: bool,
    unresolved_sentinel: str,
) -> list[tuple[str, list[str]]]: ...
def called_names(body_tokens: list[str], wrapper_markers: list[str]) -> list[str]: ...
def ordered_called_names(
    body_tokens: list[str], wrapper_markers: list[str]
) -> list[str]: ...
def referenced_names(sig_tokens: list[str], body_tokens: list[str]) -> list[str]: ...
def unresolved_exempt_names(body_tokens: list[str]) -> list[str]: ...

# T-0953: frob.arch._python's near-duplicate body-similarity clustering --
# see docs/modules/dup.md#rust-core.
def near_duplicate_indices(bodies: list[str], threshold: float) -> list[int]: ...
