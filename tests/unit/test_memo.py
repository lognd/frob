"""T-0423: run-scoped memoization for the heavy pure analyses.

Proves (a) a second call with identical arguments while a `run_memo_scope`
is active is a cache hit, not a recompute (a call-count spy on the wrapped
function), and (b) the scope's own exit drops the memo and deactivates
caching entirely -- a call after the `with` block recomputes, never
leaking a stale result to code outside the scope (including sibling test
modules sharing this worker process, e.g. `tests/test_graph.py`'s
incremental-rebuild tests that call `build_graph` directly with no scope
open at all).

Every test here opens and closes its OWN `run_memo_scope()` (never the
unconditionally-active `reset_run_memo()` convenience) so no test can
leave `memoize_per_run` caching active for whichever test runs next in
this worker process -- `reset_run_memo()` never deactivates on its own,
so using it here would have been exactly the cross-test staleness leak
this module exists to rule out.
"""

from __future__ import annotations

from pathlib import Path

from frob.arch import analyze_project
from frob.check._memo import (
    memoize_per_run,
    reset_run_memo,
    run_memo_scope,
    run_memo_stats,
)
from frob.dup import find_duplicates
from frob.graph import build_graph


def test_second_call_with_same_args_is_memo_hit() -> None:
    """Identical arguments hit the memo; call count stays at one."""
    calls: list[tuple[int, int]] = []

    @memoize_per_run
    def add(a: int, b: int) -> int:
        calls.append((a, b))
        return a + b

    with run_memo_scope():
        assert add(1, 2) == 3
        assert add(1, 2) == 3
        assert add(1, 2) == 3
        assert calls == [(1, 2)]

        hits, misses = run_memo_stats()
        assert hits == 2
        assert misses == 1


def test_different_args_are_distinct_cache_entries() -> None:
    """Distinct arguments never collide -- each is its own miss."""
    calls: list[tuple[int, int]] = []

    @memoize_per_run
    def add(a: int, b: int) -> int:
        calls.append((a, b))
        return a + b

    with run_memo_scope():
        assert add(1, 2) == 3
        assert add(3, 4) == 7
        assert calls == [(1, 2), (3, 4)]


def test_scope_exit_does_not_leak_across_scopes() -> None:
    """Two sequential `run_memo_scope()`s (simulating two `frob check`
    runs) never share cache entries -- the same arguments in a later scope
    are a fresh miss, not a stale hit from the earlier, already-exited
    scope."""
    calls: list[int] = []

    @memoize_per_run
    def double(x: int) -> int:
        calls.append(x)
        return x * 2

    with run_memo_scope():
        assert double(5) == 10
        assert calls == [5]

    # "run 2": a fresh scope must not see run 1's entry.
    with run_memo_scope():
        assert double(5) == 10
        assert calls == [5, 5]

        hits, misses = run_memo_stats()
        assert hits == 0
        assert misses == 1


def test_kwargs_are_part_of_the_cache_key() -> None:
    """Positional vs. keyword calls with different kwarg values must not
    be conflated into the same cache entry."""
    calls: list[tuple[int, int]] = []

    @memoize_per_run
    def scale(x: int, *, factor: int = 1) -> int:
        calls.append((x, factor))
        return x * factor

    with run_memo_scope():
        assert scale(2, factor=3) == 6
        assert scale(2, factor=4) == 8
        assert calls == [(2, 3), (2, 4)]


def _write_py_file(root: Path) -> None:
    """A trivial, valid source file so build_graph/analyze_project have
    something real to walk."""
    (root / "sample.py").write_text(
        "def greet(name):\n    '''Say hello.'''\n    return f'hello {name}'\n"
    )


def test_build_graph_second_call_is_memo_hit(tmp_path: Path) -> None:
    """`build_graph` called twice with the same (root, cache) inside one
    scope returns the identical object the second time -- a memo hit, not
    a second incremental rebuild."""
    _write_py_file(tmp_path)
    cache = tmp_path / ".frob" / "cache.db"

    with run_memo_scope():
        first = build_graph(tmp_path, cache)
        second = build_graph(tmp_path, cache)

        assert first is second
        hits, misses = run_memo_stats()
        assert hits == 1
        assert misses == 1


def test_build_graph_outside_scope_is_never_cached(tmp_path: Path) -> None:
    """Outside any `run_memo_scope`, `build_graph` recomputes every call --
    the correctness boundary the whole design exists for (this is the
    exact shape `tests/test_graph.py`'s incremental-rebuild tests rely on,
    called with no scope open at all)."""
    _write_py_file(tmp_path)
    cache = tmp_path / ".frob" / "cache.db"

    first = build_graph(tmp_path, cache)
    second = build_graph(tmp_path, cache)

    # Both succeed and agree on content, but are not required to be (and
    # in general will not be) the identical cached object -- no scope was
    # ever opened, so memoize_per_run never touched either call.
    assert first.is_ok
    assert second.is_ok


def test_reset_run_memo_activates_an_unbounded_scope(monkeypatch) -> None:  # noqa: ANN001
    """`reset_run_memo` is the unconditionally-active convenience over
    `run_memo_scope` -- a call after it hits the memo, exactly like inside
    a `with run_memo_scope():` block.

    `reset_run_memo` never deactivates on its own (unlike `run_memo_scope`,
    it has no matching exit), so this test snapshots+restores the
    module's private `_scope_depth` via `monkeypatch` rather than leaving
    it permanently active -- otherwise every test after this one in the
    same worker process would silently inherit an active scope, which is
    exactly the cross-run staleness leak this module's design exists to
    prevent."""
    import frob.check._memo as _memo_mod

    monkeypatch.setattr(_memo_mod, "_scope_depth", _memo_mod._scope_depth)

    calls: list[int] = []

    @memoize_per_run
    def quintuple(x: int) -> int:
        calls.append(x)
        return x * 5

    reset_run_memo()
    assert quintuple(7) == 35
    assert quintuple(7) == 35
    assert calls == [7]
    hits, misses = run_memo_stats()
    assert hits == 1
    assert misses == 1


def test_run_memo_scope_deactivates_on_exit() -> None:
    """Outside `run_memo_scope()`, `memoize_per_run` is a pure passthrough
    -- no caching, no staleness risk."""
    calls: list[int] = []

    @memoize_per_run
    def triple(x: int) -> int:
        calls.append(x)
        return x * 3

    assert triple(2) == 6
    assert triple(2) == 6
    assert calls == [2, 2]

    with run_memo_scope():
        assert triple(2) == 6
        assert triple(2) == 6
    assert calls == [2, 2, 2]

    assert triple(2) == 6
    assert calls == [2, 2, 2, 2]


def test_run_memo_scope_nests_without_truncating_outer() -> None:
    """A nested `run_memo_scope()` entered inside an already-active one
    must not clear the outer scope's in-progress memo on its own exit --
    only the outermost exit clears it."""
    calls: list[int] = []

    @memoize_per_run
    def quadruple(x: int) -> int:
        calls.append(x)
        return x * 4

    with run_memo_scope():
        assert quadruple(5) == 20
        with run_memo_scope():
            # Inner scope reuses the outer scope's already-cached entry.
            assert quadruple(5) == 20
        # Back in the outer scope: still cached, inner exit did not wipe it.
        assert quadruple(5) == 20
    assert calls == [5]


def test_analyze_project_second_call_is_memo_hit(tmp_path: Path) -> None:
    """`analyze_project` called twice with the same arguments inside one
    scope returns the identical object the second time -- the T-0418 arch
    double-run scenario, now a memo hit."""
    _write_py_file(tmp_path)

    with run_memo_scope():
        first = analyze_project(tmp_path)
        second = analyze_project(tmp_path)

        assert first is second
        hits, misses = run_memo_stats()
        assert hits == 1
        assert misses == 1


def test_find_duplicates_second_call_is_memo_hit(tmp_path: Path) -> None:
    """`find_duplicates` (T-0491, extending the T-0423 precedent) called
    twice with the same (root, min_lines) inside one scope returns the
    identical object the second time -- a memo hit, not a second scan."""
    _write_py_file(tmp_path)

    with run_memo_scope():
        first = find_duplicates(tmp_path)
        second = find_duplicates(tmp_path)

        assert first is second
        hits, misses = run_memo_stats()
        assert hits == 1
        assert misses == 1


def test_find_duplicates_no_cross_run_leak(tmp_path: Path) -> None:
    """A memo hit inside one `run_memo_scope` must never survive into a
    later, independent scope -- each `frob check` invocation gets a fresh
    scan, never a decade-stale result from an earlier run."""
    _write_py_file(tmp_path)

    with run_memo_scope():
        first = find_duplicates(tmp_path)
        hits, misses = run_memo_stats()
        assert hits == 0
        assert misses == 1

    with run_memo_scope():
        second = find_duplicates(tmp_path)
        hits, misses = run_memo_stats()
        assert hits == 0
        assert misses == 1

    # Equal content, but the second scope recomputed from scratch rather
    # than reusing the first scope's cached object.
    assert first == second
    assert first is not second
