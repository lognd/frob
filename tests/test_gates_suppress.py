"""Tests for `frob.gates._suppress` (T-1340): the `SuppressionDialect`
registry and SUPPRESS001's evidence-driven correlation. Uses the REAL
`ty`/`mypy` binaries against small on-disk fixtures rather than mocking
their output -- the whole point of this gate is real, observed
diagnostics, and both tools are dev dependencies already required to run
this suite (T-1339's oracle mechanism)."""

# frob:waive OPAQUE001 reason="T-1038: the setattr(...) below is monkeypatch-style \
# test isolation (pytest fixtures reassigning a module attribute by a name the test \
# itself constructs) -- deliberate test infrastructure, not an evasion risk over \
# untrusted input"

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._models import Severity
from frob.gates._suppress import (
    SuppressionDialect,
    _line_suppressions,
    _relativize,
    suppress001_gate,
    suppression_dialects,
)
from frob.graph._models import GraphSnapshot

pytestmark = pytest.mark.timeout(90)

_SNAPSHOT = GraphSnapshot(root=".", symbols={}, edges=())


def _write(root: Path, rel: str, text: str) -> None:
    """Write `text` to `root/rel`, creating parent dirs as needed."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class TestSuppressionDialects:
    """`suppression_dialects` / `SuppressionDialect` registry shape."""

    def test_registers_ty_mypy_ruff(self) -> None:
        """The registry names exactly `ty`, `mypy`, `ruff` (T-1340's Phase
        1 mandate: python entries for all three)."""
        dialects = suppression_dialects()
        assert set(dialects) == {"ty", "mypy", "ruff"}
        for name, dialect in dialects.items():
            assert isinstance(dialect, SuppressionDialect)
            assert dialect.name == name

    def test_available_reflects_path_not_project_config(self) -> None:
        """`available` is a capability check (the tool resolves on
        `PATH`), never a "configured for this project" check -- T-1339's
        DESIGN AMENDMENT. `ty` and `mypy` are both dev dependencies of
        this very test run, so both must report available."""
        dialects = suppression_dialects()
        assert dialects["ty"].available is True
        assert dialects["mypy"].available is True


class TestLineSuppressions:
    """`_line_suppressions`: per-line suppression-comment extraction."""

    def test_bare_ty_ignore_covers_everything(self) -> None:
        """A bare `# ty: ignore` (no bracketed code) is recorded as `None`
        -- covers every rule code on the line, matching ty's own bare-
        ignore semantics."""
        dialects = suppression_dialects()
        present = _line_suppressions("x = y  # ty: ignore", dialects)
        assert present == {"ty": None}

    def test_coded_mypy_ignore_extracts_code_set(self) -> None:
        """A coded `# type: ignore[code]` extracts exactly that code into
        a one-element set."""
        dialects = suppression_dialects()
        present = _line_suppressions("x = y  # type: ignore[name-defined]", dialects)
        assert present == {"mypy": {"name-defined"}}

    def test_both_dialects_on_one_line(self) -> None:
        """A line stacking both dialects' comments extracts both,
        independently."""
        dialects = suppression_dialects()
        present = _line_suppressions(
            "x = y  # type: ignore[name-defined]  # ty: ignore[unresolved-reference]",
            dialects,
        )
        assert present == {
            "mypy": {"name-defined"},
            "ty": {"unresolved-reference"},
        }

    def test_no_suppression_present(self) -> None:
        """A line with no suppression comment at all extracts nothing."""
        dialects = suppression_dialects()
        assert _line_suppressions("x = y", dialects) == {}


class TestRelativize:
    """`_relativize`: normalising a checker-reported path to root-relative."""

    def test_absolute_path_under_root(self, tmp_path: Path) -> None:
        """An absolute path under `root` becomes a root-relative posix
        path."""
        target = tmp_path / "src" / "mod.py"
        assert _relativize(str(target), tmp_path) == "src/mod.py"

    def test_already_relative_path_passes_through(self, tmp_path: Path) -> None:
        """An already-relative path is returned unchanged (as posix)."""
        assert _relativize("src/mod.py", tmp_path) == "src/mod.py"

    def test_path_outside_root_is_none(self, tmp_path: Path) -> None:
        """A path resolving outside `root` entirely cannot be sited
        against a tracked source line -- `None`, not a wrong guess."""
        outside = tmp_path.parent / "elsewhere" / "mod.py"
        assert _relativize(str(outside), tmp_path) is None

    def test_none_file_is_none(self, tmp_path: Path) -> None:
        """A checker diagnostic with no file at all yields `None`."""
        assert _relativize(None, tmp_path) is None


# frob:ticket T-1635
class TestMypyOracleCacheDir:
    """T-1635 regression: `_mypy_diagnostics` must pin `--cache-dir`
    inside the caller's own root.

    Before this fix the oracle invocation inherited mypy's default
    `.mypy_cache` resolved against the PROCESS CWD, so every concurrent
    pytest-xdist worker shared one cache directory. A torn read then
    returned ZERO diagnostics for a file that genuinely had one -- the
    silent-under-report shape this drive kept hitting, here making the
    ty-vs-mypy oracle disagree at random and reddening SUPPRESS001 tests
    only under load."""

    def test_mypy_invocation_pins_cache_dir_under_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/_suppress.py::_mypy_diagnostics kind="unit"
        from frob.gates import _suppress

        captured: list[list[str]] = []

        from typani.result import Err

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN003, ANN202
            captured.append(list(argv))
            # Err short-circuits _mypy_diagnostics to [] -- this test is
            # about the ARGV it builds, not the diagnostics it parses.
            return Err("stubbed: argv captured")

        monkeypatch.setattr(_suppress, "guarded_subprocess_run", _fake_run)
        _suppress._mypy_diagnostics(tmp_path)

        assert captured, "mypy was never invoked"
        argv = captured[0]
        assert "--cache-dir" in argv, argv
        pinned = argv[argv.index("--cache-dir") + 1]
        assert pinned == str(tmp_path / ".mypy_cache"), pinned


class TestSuppress001Gate:
    """`suppress001_gate`: the full evidence-driven correlation, against
    the real `ty`/`mypy` oracles."""

    def test_mypy_suppressed_ty_unsuppressed_fires(self, tmp_path: Path) -> None:
        """Acceptance [0]: a line carrying ONLY a mypy `type: ignore` that
        `ty` still errors on fires SUPPRESS001, naming both dialects and
        ty's own reported rule code."""
        _write(
            tmp_path,
            "src/mod.py",
            "def uses_bad() -> None:\n"
            "    return undefined_name  # type: ignore[name-defined]\n",
        )
        violations = suppress001_gate(tmp_path, _SNAPSHOT)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule == "SUPPRESS001"
        assert v.severity == Severity.ERROR
        assert v.file == "src/mod.py"
        assert v.line == 2
        assert "mypy" in v.message
        assert "ty" in v.message
        assert "unresolved-reference" in v.message

    def test_ty_suppressed_mypy_unsuppressed_fires(self, tmp_path: Path) -> None:
        """Symmetric direction: a line carrying ONLY a `ty: ignore` that
        mypy still errors on fires SUPPRESS001 naming mypy's own code."""
        _write(
            tmp_path,
            "src/mod.py",
            "def uses_bad() -> None:\n"
            "    return undefined_name  # ty: ignore[unresolved-reference]\n",
        )
        violations = suppress001_gate(tmp_path, _SNAPSHOT)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule == "SUPPRESS001"
        assert v.file == "src/mod.py"
        assert v.line == 2
        assert "ty" in v.message
        assert "mypy" in v.message
        assert "name-defined" in v.message

    def test_both_dialects_present_reports_nothing(self, tmp_path: Path) -> None:
        """Acceptance [1]: a line already carrying BOTH dialects'
        suppressions reports nothing -- fully portable already."""
        _write(
            tmp_path,
            "src/mod.py",
            "def uses_bad() -> None:\n"
            "    return undefined_name  # type: ignore[name-defined]"
            "  # ty: ignore[unresolved-reference]\n",
        )
        violations = suppress001_gate(tmp_path, _SNAPSHOT)
        assert violations == ()

    def test_no_suppression_no_finding(self, tmp_path: Path) -> None:
        """A genuinely clean, unsuppressed line with no diagnostics at
        all from either oracle produces no SUPPRESS001 finding -- this
        gate only ever fires on a cross-dialect MISMATCH, never on a
        bare type error with no suppression comment at all (that is a
        different gate's problem, not this one's)."""
        _write(
            tmp_path,
            "src/mod.py",
            "def add(a: int, b: int) -> int:\n    return a + b\n",
        )
        violations = suppress001_gate(tmp_path, _SNAPSHOT)
        assert violations == ()

    def test_no_available_oracle_reports_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Reworded acceptance [2]: with NO oracle available for any
        dialect (a capability limit, not "unconfigured in this
        project"), the gate reports nothing rather than guessing --
        simulated here by monkeypatching the registry itself so both
        `ty` and `mypy` read as unavailable regardless of what is
        actually on this machine's `PATH`."""
        _write(
            tmp_path,
            "src/mod.py",
            "def uses_bad() -> None:\n"
            "    return undefined_name  # type: ignore[name-defined]\n",
        )

        def _no_oracles() -> dict[str, SuppressionDialect]:
            return {
                "ty": SuppressionDialect(
                    name="ty", pattern=r"#\s*ty:\s*ignore", available=False
                ),
                "mypy": SuppressionDialect(
                    name="mypy", pattern=r"#\s*type:\s*ignore", available=False
                ),
                "ruff": SuppressionDialect(
                    name="ruff", pattern=r"#\s*noqa", available=False
                ),
            }

        monkeypatch.setattr("frob.gates._suppress.suppression_dialects", _no_oracles)
        violations = suppress001_gate(tmp_path, _SNAPSHOT)
        assert violations == ()
