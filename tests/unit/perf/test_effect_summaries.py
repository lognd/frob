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
