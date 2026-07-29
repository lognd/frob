"""`frob.perf._effect_summaries` (T-0922): the shared substrate module's own
unit-level guarantees -- `Unknown`'s identity-only equality, and
`EffectGraph.summary` degrading an ambiguous/unresolvable callee to an
explicit `Unknown` member rather than a silently empty set.

# frob:ticket T-0922
"""

from __future__ import annotations

from pathlib import Path

from frob.lang import parse_file
from frob.perf._effect_summaries import UNKNOWN_KIND, EffectGraph, Unknown


def _write(root: Path, name: str, src: str) -> Path:
    """Write `src` to `root/name`, returning the path -- shared test setup."""
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src)
    return path


class TestUnknownIdentityEquality:
    """`Unknown` never compares equal to anything but itself, by design
    (module docstring/class docstring): this is what lets an `Unknown`
    occurrence widen visibility without ever manufacturing a false
    duplicate-detection match."""

    def test_two_unknowns_with_the_same_reason_text_are_not_equal(self) -> None:
        """Even identical `reason` strings never make two `Unknown`
        instances compare equal -- equality is plain object identity."""
        first = Unknown("unresolvable callee 'run'")
        second = Unknown("unresolvable callee 'run'")
        assert first != second
        assert first == first  # noqa: PLR0124 -- deliberately asserting identity
        assert len({first, second}) == 2

    def test_unknown_repr_carries_its_reason_for_diagnostics(self) -> None:
        """`repr(Unknown(...))` surfaces the reason string for humans
        reading a diagnostic dump, even though it plays no role in
        equality."""
        assert "no local definition" in repr(Unknown("no local definition"))


class TestEffectGraphSummaryUnknownDegradation:
    """T-0922 acceptance (c): `EffectGraph.summary` must degrade an
    unresolvable binding to an explicit, visible `Unknown` member --
    never to silent omission."""

    def test_ambiguous_cross_file_callee_yields_an_explicit_unknown_member(
        self, tmp_path: Path
    ) -> None:
        """Two DIFFERENT top-level functions in two DIFFERENT files both
        named `run` -- calling `run(...)` from a third, unrelated file
        cannot be scoped to either (no same-file candidate, and more than
        one cross-file candidate) -- `resolve_scoped` returns `[]`, and
        `summary()` must record that as an explicit `Unknown`, not
        nothing."""
        _write(tmp_path, "a.py", "def run(x):\n    return x\n")
        _write(tmp_path, "b.py", "def run(x):\n    return x + 1\n")
        src = "def caller(x):\n    return run(x)\n"
        path = _write(tmp_path, "caller.py", src)
        files = [
            parse_file(tmp_path / "a.py").danger_ok,
            parse_file(tmp_path / "b.py").danger_ok,
            parse_file(path).danger_ok,
        ]
        graph = EffectGraph(files)

        summary = graph.summary(f"{path}::caller")
        assert any(kind == UNKNOWN_KIND for kind, _arg in summary)
        unknown_members = [arg for kind, arg in summary if kind == UNKNOWN_KIND]
        assert all(isinstance(arg, Unknown) for arg in unknown_members)

    def test_fully_resolvable_call_path_has_no_unknown_member(
        self, tmp_path: Path
    ) -> None:
        """The ordinary, fully-resolvable case (a single, unambiguous
        same-file callee reached transitively) never contributes a
        spurious `Unknown` -- Unknown is additive-only, not a default
        noise floor."""
        src = (
            "import subprocess\n\n\n"
            "def leaf(root):\n"
            "    return subprocess.run(['git', 'status'], cwd=root)\n\n\n"
            "def caller(root):\n"
            "    return leaf(root)\n"
        )
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok
        graph = EffectGraph([parsed])

        summary = graph.summary(f"{path}::caller")
        assert not any(kind == UNKNOWN_KIND for kind, _arg in summary)
        assert ("spawn", "(['git', 'status'], cwd=root)") in summary


# frob:doc \
# docs/modules/perf.md#duplicate-identical-subprocess-spawn-detector-perf012-t-0919
# frob:tests \
# tests/unit/perf/test_effect_summaries.py::TestSplatArgumentDegradesToUnknown.test_spl\
# at_argument_nested_in_a_literal_yields_an_unknown_member
# frob:tests \
# tests/unit/perf/test_effect_summaries.py::TestSplatArgumentDegradesToUnknown.test_pla\
# in_named_parameter_forward_is_not_treated_as_a_splat
# frob:ticket T-1018
class TestSplatArgumentDegradesToUnknown:
    """T-1018: a direct-effect call whose argument list contains a
    `*args`/`**kwargs` splat -- even nested inside a literal collection
    argument, the real `["git", *args]` shape -- degrades to an explicit
    `Unknown` rather than a comparable literal arg-text occurrence, since
    the splat's real content is caller-dependent and cannot be compared
    by static text at the wrapper's own definition site."""

    def test_splat_argument_nested_in_a_literal_yields_an_unknown_member(
        self, tmp_path: Path
    ) -> None:
        """`_git(*args, cwd): subprocess.run(["git", *args], cwd=cwd)` --
        the splat sits one level below `argument_list`, inside the `list`
        literal, not as a direct top-level call argument; the summary must
        still surface an explicit `Unknown`, not a concrete arg-text
        occurrence that would wrongly compare equal across every caller."""
        src = (
            "import subprocess\n\n\n"
            "def _git(*args, cwd):\n"
            "    return subprocess.run(['git', *args], cwd=cwd)\n\n\n"
            "def caller(root):\n"
            "    return _git('status', cwd=root)\n"
        )
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok
        graph = EffectGraph([parsed])

        summary = graph.summary(f"{path}::caller")
        assert any(kind == UNKNOWN_KIND for kind, _arg in summary)
        assert not any(kind == "spawn" for kind, _arg in summary)

    def test_plain_named_parameter_forward_is_not_treated_as_a_splat(
        self, tmp_path: Path
    ) -> None:
        """A plain named-parameter forward (`ticket_id` used directly, no
        `*`/`**`) is NOT a splat -- the T-0919 true-positive shape must
        keep surfacing a concrete, comparable arg-text occurrence."""
        src = (
            "import subprocess\n\n\n"
            "def check_gates(root, ticket_id):\n"
            "    return subprocess.run(\n"
            "        ['frob', 'check', '--ticket', ticket_id], cwd=root\n"
            "    )\n\n\n"
            "def caller(root, ticket_id):\n"
            "    return check_gates(root, ticket_id)\n"
        )
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok
        graph = EffectGraph([parsed])

        summary = graph.summary(f"{path}::caller")
        assert not any(kind == UNKNOWN_KIND for kind, _arg in summary)
        assert any(kind == "spawn" for kind, _arg in summary)


# frob:doc \
# docs/modules/perf.md#shared-interprocedural-effect-summary-substrate-effectgraph-t-09\
# 22
# frob:tests \
# tests/unit/perf/test_effect_summaries.py::TestMemoizedCalleeDetection.test_lru_cache_\
# decorated_symbol_is_memoized
# frob:tests \
# tests/unit/perf/test_effect_summaries.py::TestMemoizedCalleeDetection.test_undecorate\
# d_symbol_is_not_memoized
# frob:tests \
# tests/unit/perf/test_effect_summaries.py::TestMemoizedCalleeDetection.test_bare_cache\
# _named_parameter_is_not_mistaken_for_a_decorator
# frob:ticket T-1053
class TestMemoizedCalleeDetection:
    """T-1053 lru_cache-blindness fix: `EffectGraph.is_memoized`/
    `callee_is_memoized` must recognize an actual `@lru_cache`/`@cache`
    decorator, never a bare-name coincidence like a parameter called
    `cache`."""

    def test_lru_cache_decorated_symbol_is_memoized(self, tmp_path: Path) -> None:
        """A `@lru_cache`-decorated function is memoized by both
        `is_memoized` (by symref) and `callee_is_memoized` (by short
        name)."""
        src = (
            "from functools import lru_cache\n\n\n"
            "@lru_cache\n"
            "def run_argv(argv):\n"
            "    return len(argv)\n"
        )
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok
        graph = EffectGraph([parsed])

        assert graph.is_memoized(f"{path}::run_argv")
        assert graph.callee_is_memoized("run_argv")

    def test_undecorated_symbol_is_not_memoized(self, tmp_path: Path) -> None:
        """A plain, undecorated function is never memoized."""
        src = "def run_argv(argv):\n    return len(argv)\n"
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok
        graph = EffectGraph([parsed])

        assert not graph.is_memoized(f"{path}::run_argv")
        assert not graph.callee_is_memoized("run_argv")

    def test_bare_cache_named_parameter_is_not_mistaken_for_a_decorator(
        self, tmp_path: Path
    ) -> None:
        """A parameter literally named `cache` (no `@` decorator marker
        before it) must not be mistaken for `@cache` memoization -- the
        same bare-name-coincidence discipline this ticket's other two
        fixes apply."""
        src = "def run_argv(argv, cache):\n    return len(argv) + len(cache)\n"
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok
        graph = EffectGraph([parsed])

        assert not graph.is_memoized(f"{path}::run_argv")
        assert not graph.callee_is_memoized("run_argv")

    def test_functools_dotted_lru_cache_decorator_is_memoized(
        self, tmp_path: Path
    ) -> None:
        """The common real spelling `@functools.lru_cache(maxsize=32)`
        (`import functools`, not `from functools import lru_cache`) is
        recognized too, not just the bare `@lru_cache` form -- the exact
        spelling `frob.gates.__init__._ledger_states_at_base` uses (the
        real specimen behind one of the waivers this ticket retires)."""
        src = (
            "import functools\n\n\n"
            "@functools.lru_cache(maxsize=32)\n"
            "def run_argv(argv):\n"
            "    return len(argv)\n"
        )
        path = _write(tmp_path, "mod.py", src)
        parsed = parse_file(path).danger_ok
        graph = EffectGraph([parsed])

        assert graph.is_memoized(f"{path}::run_argv")
        assert graph.callee_is_memoized("run_argv")
