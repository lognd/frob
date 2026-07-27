"""Thin shim over the `frob_core` native `resolve_call_edges` kernel
(docs/modules/graph.md#rust-core, T-0930).

Mirrors `frob.dup._core`'s `core_available()`-gated pattern: a PyO3 call
never crosses this boundary as an exception the rest of `frob.graph` has
to know about, and a missing/unbuilt extension is a plain `None` return
-- `frob.graph.callgraph._resolve_edges` falls back to its own pure-Python
loop (`_resolve_edges_python`, kept byte-identical) whenever this returns
`None`, never a silent behavior change.
"""
# frob:ticket T-0930

from __future__ import annotations

from functools import lru_cache

from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/modules/graph.md#rust-core
INSTALL_HINT = (
    "install with: uv pip install ./frob-core  (or: maturin develop, from frob-core/)"
)


# frob:doc docs/modules/graph.md#rust-core
# frob:waive TEST005 reason="core_available is the same 66.7%-branch-cover shape as \
# frob.dup._core's twin (T-0160 debt), not a new gap this ticket introduces"
@lru_cache(maxsize=1)
def core_available() -> bool:
    """Whether the compiled `frob_core` extension is importable, cached once."""
    try:
        import frob_core  # noqa: F401
    except ImportError:
        _log.warning(
            "frob_core not importable; callgraph edge resolution stays "
            "pure-python (dead_symbols/build_call_graph/build_reference_graph "
            "all pay the slower path). %s",
            INSTALL_HINT,
        )
        return False
    return True


# frob:doc docs/modules/graph.md#rust-core
# frob:tests \
# tests/test_graph.py::TestResolveCallEdgesNative.test_native_matches_python_fallback_o\
# n_a_real_package  # noqa: E501
def resolve_call_edges_native(
    callers: list[str],
    names_per_caller: list[list[str]],
    exempt_per_caller: list[list[str]],
    by_name: dict[str, list[tuple[str, str, bool]]],
    mark_unresolved: bool,
    unresolved_sentinel: str,
) -> dict[str, tuple[str, ...]] | None:
    """Call `frob_core.resolve_call_edges` and reshape its ordered
    `(caller, callees)` pair list back into the dict
    `frob.graph.callgraph._resolve_edges` returns -- preserves the same
    caller-iteration insertion order the pure-Python loop produces.
    Returns `None` (never raises) when `frob_core` is unavailable, the
    signal `_resolve_edges` uses to fall back to its own pure-Python loop.
    """
    if not core_available():
        return None
    import frob_core

    pairs = frob_core.resolve_call_edges(
        callers,
        names_per_caller,
        exempt_per_caller,
        by_name,
        mark_unresolved,
        unresolved_sentinel,
    )
    return {caller: tuple(callees) for caller, callees in pairs}


# T-0930 DISCLOSURE: `frob_core` also exports `called_names`,
# `ordered_called_names`, `referenced_names`, and `unresolved_exempt_names`
# (frob-core/src/lib.rs) -- native ports of `frob.graph.callgraph`'s
# per-symbol token-scan helpers, prototyped during this same investigation.
# Deliberately NOT wired here: measured end-to-end SLOWER than the
# pure-Python loops they would replace (0.242s vs 0.135s median
# dead_symbols in-scope thread_time over this repo's own `src/frob/gates`
# package) because each is called once PER SYMBOL -- thousands of small
# calls, where per-call PyO3 marshaling overhead outweighs the loop-speed
# win a Rust implementation gives on larger batches (contrast
# `resolve_call_edges` above: 46 large, batched calls, a genuine win).
# Kept in `frob_core` (tested, documented) as a parked kernel for a future
# caller that batches across a whole package/file rather than one symbol
# at a time -- see `frob.graph.callgraph._ordered_called_names`'s
# docstring for the full disposition.
