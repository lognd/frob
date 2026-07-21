"""Run-scoped memoization for the heavy PURE analyses (T-0423, generalizing
the T-0414 parse-cache pattern beyond `frob.lang`).

Root cause this closes: the T-0418 arch double-run was one instance of a
recurring class -- the same expensive PURE computation (`build_graph`,
`analyze_project`, ...) gets called independently by more than one `frob
check` stage in the same invocation, and nothing made re-running it free.
Rather than hunt down and hand-fix each duplicate call site (brittle,
whack-a-mole, and the T-0418 fix itself proved this: `_arch_violations_
from_suggestions` was written to dedupe one such case and never wired), a
single `@memoize_per_run` decorator on each heavy function makes the SECOND
call within one `frob check` invocation a cache hit instead of a
recompute, no matter which stage calls it or in what order.

Explicit run scope, NOT an ambient always-on cache: memoization only
engages between a `run_memo_scope()` enter and its matching exit (entered
once, in `frob.check._run_check_with_skips`, alongside the sibling
`frob.lang.reset_parse_cache` call). Outside an active scope -- e.g. a
caller invoking `build_graph`/`analyze_project` directly, never through
`frob check` (the CLI runners in `frob.app.*`, or a test that calls one of
these functions twice in a row to exercise real incremental-rebuild
behavior across an on-disk content change) -- the decorated functions are a
transparent passthrough with no caching at all, so such callers see
exactly the same fresh-recompute-every-time behavior they always have.
This is the correctness boundary the ticket's "never a process-global that
survives across runs and goes stale" mandate demands: a plain always-on
args-keyed memo (no content hash) would silently return a stale result to
any caller who legitimately re-invokes one of these functions after
mutating the target tree outside of a `frob check` run; scoping engagement
to `run_memo_scope()` confines that risk to exactly the one caller
(`frob.check`) that already establishes, per invocation, that the target
tree is a stable snapshot for the run's duration.

Thread-safety: `frob.check._run_tasks_concurrently` runs gate stages in a
`ThreadPoolExecutor` spawned from within an active scope -- the "is a scope
active" flag and the cache itself are process-global (not thread-local) so
worker threads see the same active scope their parent entered, guarded by
one lock exactly like `frob.lang`'s `_parse_cache`.
"""

from __future__ import annotations

import functools
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])

_memo_lock = threading.Lock()
_memo_cache: dict[tuple[Any, ...], Any] = {}
_memo_hits = 0
_memo_misses = 0
_scope_depth = 0


# frob:invariant terminates reason="_freeze only recurses into a value's own dict/list/set/tuple elements, each a strictly smaller sub-structure of a finite, non-self-referential call-argument tree (paths/primitives/plain containers)" measure="total element count across nested dict/list/set/tuple containers strictly decreases with each recursive call"  # noqa: E501
def _freeze(value: Any) -> Any:  # noqa: ANN401
    """A hashable stand-in for `value`, recursing into dict/list/set/tuple.

    Call arguments to the memoized analyses are paths, primitives, and
    plain containers of them -- this covers those shapes without pulling
    in a general-purpose deep-freeze library for a handful of call sites.
    An unhashable/unsupported leaf (e.g. an arbitrary object) is returned
    as-is and will raise `TypeError` from the outer `dict` lookup, the same
    failure a caller would get from using it as a dict key directly --
    never silently miscompared.
    """
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    if isinstance(value, (list, set, frozenset)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_freeze(v) for v in value)
    return value


# frob:doc docs/commands/check.md#run-scoped-memoization
# frob:tests tests/unit/test_memo.py::test_run_memo_scope_deactivates_on_exit
# frob:tests tests/unit/test_memo.py::test_run_memo_scope_nests_without_truncating_outer
# frob:ticket T-0423
@contextmanager
def run_memo_scope() -> Iterator[None]:
    """Activate `memoize_per_run` caching for the duration of the `with`
    block; a fresh, empty cache and zeroed hit/miss counters on entry,
    fully cleared on exit.

    Nestable (depth-counted): only the outermost enter clears the cache and
    only the outermost exit clears it again, so a nested caller (a helper
    that happens to open its own scope inside an already-active one) never
    truncates the outer scope's in-progress memo. `frob.check._run_check_
    with_skips` opens exactly one top-level scope per `frob check`
    invocation.
    """
    global _scope_depth, _memo_hits, _memo_misses
    with _memo_lock:
        _scope_depth += 1
        entering_outermost = _scope_depth == 1
        if entering_outermost:
            _memo_cache.clear()
            _memo_hits = 0
            _memo_misses = 0
    try:
        yield
    finally:
        with _memo_lock:
            _scope_depth -= 1
            if _scope_depth == 0:
                _memo_cache.clear()


# frob:doc docs/commands/check.md#run-scoped-memoization
# frob:tests tests/unit/test_memo.py::test_reset_run_memo_activates_an_unbounded_scope
# frob:ticket T-0423
def reset_run_memo() -> None:
    """Enter a fresh top-level memo scope, clearing any prior one and its
    hit/miss counters.

    A thin convenience over `run_memo_scope()` for callers (and tests) that
    want an unconditionally-active, unbounded scope rather than a `with`
    block -- used by unit tests exercising `memoize_per_run` directly.
    Prefer `run_memo_scope()` for real call sites so the cache is
    guaranteed to deactivate again (never a caller invoking `build_graph`
    outside `frob check` and silently getting a decade-stale cache hit
    because a `frob check` run's scope was entered but never exited).
    """
    global _memo_hits, _memo_misses, _scope_depth
    with _memo_lock:
        _memo_cache.clear()
        _memo_hits = 0
        _memo_misses = 0
        _scope_depth = 1


# frob:doc docs/commands/check.md#run-scoped-memoization
# frob:tests tests/unit/test_memo.py::test_second_call_with_same_args_is_memo_hit
# frob:ticket T-0423
def run_memo_stats() -> tuple[int, int]:
    """(hits, misses) against every `@memoize_per_run`-wrapped call since
    the last `reset_run_memo`/`run_memo_scope` entry.

    The T-0423 anti-regression instrument: a test asserts a heavy analysis
    called twice with identical arguments in one run records exactly one
    miss and one hit, mirroring `frob.lang.parse_cache_stats`.
    """
    with _memo_lock:
        return _memo_hits, _memo_misses


# frob:doc docs/commands/check.md#run-scoped-memoization
# frob:tests tests/unit/test_memo.py::test_second_call_with_same_args_is_memo_hit
# frob:tests tests/unit/test_memo.py::test_build_graph_second_call_is_memo_hit
# frob:tests tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit
# frob:ticket T-0423
def memoize_per_run(func: _F) -> _F:
    """Wrap `func` so repeat calls with identical arguments, while a
    `run_memo_scope()` is active, reuse the first call's result instead of
    recomputing.

    Applied to the ~5 heavy PURE analyses (`build_graph`, `analyze_project`,
    ...) at their definition site rather than at each call site: every
    caller across every stage/gate benefits automatically whenever a scope
    is active, with no call-site edits and no risk of one stage's copy
    going stale relative to another's. Outside an active scope this is a
    pure passthrough -- no caching, no staleness risk, identical behavior
    to the undecorated function (see this module's docstring for why that
    boundary matters). Keyed on the decorated function's identity plus its
    frozen arguments (`_freeze`) -- a distinct function or distinct
    arguments always misses; identical function+arguments always hits,
    regardless of which stage or thread calls it. Must only wrap functions
    that are referentially transparent for the lifetime of one scope (no
    I/O result that can change mid-scope) -- `build_graph`/`analyze_project`
    qualify because a single `frob check` invocation treats the target
    tree as a stable snapshot.
    """

    @functools.wraps(func)
    def _wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        global _memo_hits, _memo_misses
        with _memo_lock:
            if _scope_depth == 0:
                active = False
            else:
                active = True
                key = (id(func), _freeze(args), _freeze(kwargs))
                if key in _memo_cache:
                    _memo_hits += 1
                    return _memo_cache[key]
                _memo_misses += 1
        if not active:
            return func(*args, **kwargs)
        result = func(*args, **kwargs)
        with _memo_lock:
            if _scope_depth > 0:
                _memo_cache[key] = result
        return result

    return _wrapper  # type: ignore[return-value]  # ty: ignore[invalid-return-type]
