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

# T-1220: python-only tree-extraction kernel -- see
# docs/modules/lang.md#extraction-api. Returns (comment_spans,
# docstring_spans, identifiers, tokens); never raises (source that fails to
# parse yields four empty lists rather than a PyErr).
def extract_tree_python(
    source: bytes,
) -> tuple[
    list[tuple[int, int]],
    list[tuple[int, int]],
    list[tuple[str, int]],
    list[str],
]: ...

# T-1220: rust-only tree-extraction kernel companion to
# extract_tree_python -- see docs/modules/lang.md#extraction-api. Returns
# (comment_spans, identifiers, tokens); a 3-tuple, not the python kernel's
# 4-tuple, since rust has no python-style string-literal docstring facet.
# Never raises (source that fails to parse yields three empty lists rather
# than a PyErr).
def extract_tree_rust(
    source: bytes,
) -> tuple[
    list[tuple[int, int]],
    list[tuple[str, int]],
    list[str],
]: ...

# T-1220: cpp-only tree-extraction kernel companion to extract_tree_python/
# extract_tree_rust -- see docs/modules/lang.md#extraction-api. Returns
# (comment_spans, identifiers, tokens); a 3-tuple, no docstring facet (cpp
# has no python-style string-literal docstring convention). Never raises
# (source that fails to parse yields three empty lists rather than a
# PyErr).
def extract_tree_cpp(
    source: bytes,
) -> tuple[
    list[tuple[int, int]],
    list[tuple[str, int]],
    list[str],
]: ...

# T-1220: typescript-only tree-extraction kernel companion to the python/
# rust/cpp kernels -- see docs/modules/lang.md#extraction-api. Returns
# (comment_spans, identifiers, tokens); a 3-tuple, no docstring facet.
# Never raises (source that fails to parse yields three empty lists rather
# than a PyErr).
def extract_tree_typescript(
    source: bytes,
) -> tuple[
    list[tuple[int, int]],
    list[tuple[str, int]],
    list[str],
]: ...

# T-1221: rust capability-scan resolver for python source -- see
# docs/modules/vet.md#public-api. Returns (candidates, unresolved, spans):
# candidates is (resolved_dotted_target, start_byte, end_byte) for every
# call/attribute/subscript site this resolver could identify (mirrors
# frob.vet._capability_python._python_resolved_candidates, minus three
# disclosed registry-dependent deviations -- see
# frob-core/src/capability_python.rs's module docstring); unresolved is
# (start_byte, end_byte) for every call site that is a dynamic-dispatch
# shape (a subscript keyed by a non-literal expression) this resolver can
# SEE but cannot identify the callee for -- a loud, explicit "cannot
# resolve" outcome, never silently folded into "no capability"; spans is
# comment+docstring byte spans, matching
# frob.vet._capability_core._non_executable_byte_spans's contract. Never
# raises (a buffer tree-sitter cannot parse, or one that is not python,
# yields three empty lists rather than a PyErr).
def scan_python_capabilities(
    source: bytes,
) -> tuple[
    list[tuple[str, int, int]],
    list[tuple[int, int]],
    list[tuple[int, int]],
]: ...

# T-1222: rust arch python metrics single-pass walk -- extraction only, see
# docs/modules/arch.md#normalized-code-model. Returns one entry per python
# function (module-level, method, or nested, flattened) in source order:
# ((start_line, end_line), max_nesting_depth, cyclomatic, (branches, loops,
# calls, field_accesses, returns, raises, catches, subscripts)), matching
# frob.arch._python's _py_max_nesting/_py_cyclomatic/_py_collect_body_events
# output exactly EXCEPT NormalizedCall.declared_raises (never populated
# here -- a raw-text `# frob:callee-raises` comment convention layered on
# top of the tree walk, disclosed deviation, see
# frob-core/src/arch_python.rs's module docstring). Each event tuple:
# branches: (line, condition_text); loops: (line, kind); calls: (callee,
# line, args) where args is (index, keyword, ident) with exactly one of
# index/keyword set; field_accesses: (name, line, is_write); returns:
# (line, value_text); raises: (line, exception_type); catches: (line,
# exception_type); subscripts: line. Never raises (source that fails to
# parse, or is not python, yields an empty list rather than a PyErr).
def py_function_metrics(
    source: bytes,
) -> list[
    tuple[
        tuple[int, int],
        int,
        int,
        tuple[
            list[tuple[int, str]],
            list[tuple[int, str]],
            list[tuple[str, int, list[tuple[int | None, str | None, str | None]]]],
            list[tuple[str, int, bool]],
            list[tuple[int, str | None]],
            list[tuple[int, str | None]],
            list[tuple[int, str | None]],
            list[int],
        ],
    ]
]: ...
