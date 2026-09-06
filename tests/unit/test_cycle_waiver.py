"""T-2584 regression: CYCLE001 findings from `frob check --only cycle`
(`frob.check._python._run_cycle`) used to go straight into their
`ToolResult` with zero calls into `frob.gates._waive` -- a documented
`# frob:waive CYCLE001 reason="..."` comment was silently inert, no matter
how deliberate the repo-owner decision behind it (T-2364's own "declare
this coupling and move on" case had no landable form). This suite is the
ticket's own mandatory positive/negative control: a planted cycle reports
unwaived, a matching waiver in its representative file suppresses it, and
an unrelated file's waiver does not.
"""

from __future__ import annotations

import ntpath
from pathlib import Path, PureWindowsPath

from frob.check._python import _run_cycle


def _write(path: Path, text: str) -> None:
    """Write `text` to `path`, creating parent directories -- fixture helper."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _make_cyclic_fixture(root: Path, *, waiver_in: str | None) -> None:
    """A minimal `src/`-layout project with a planted `pkg.a` <-> `pkg.b`
    cycle. If `waiver_in` names a file ("a.py"/"b.py"/"c.py"), a `# frob:
    waive CYCLE001` comment is prepended to that file only."""
    _write(
        root / "pyproject.toml",
        '[project]\nname = "pkg"\n\n'
        '[tool.setuptools]\npackages = { find = { where = ["src"] } }\n',
    )
    _write(root / "src" / "pkg" / "__init__.py", "")
    waiver_line = '# frob:waive CYCLE001 reason="test waiver"\n'
    a_body = "import pkg.b\n"
    b_body = "import pkg.a\n"
    if waiver_in == "a.py":
        a_body = waiver_line + a_body
    elif waiver_in == "b.py":
        b_body = waiver_line + b_body
    _write(root / "src" / "pkg" / "a.py", a_body)
    _write(root / "src" / "pkg" / "b.py", b_body)
    if waiver_in == "c.py":
        _write(root / "src" / "pkg" / "c.py", waiver_line + "x = 1\n")


class TestCycleWaiverPipeline:
    """`_run_cycle`'s CYCLE001 diagnostics now route through the same
    `_apply_waivers`/`_match_waiver` spine every other gate's `Violation`
    stream uses (T-2584)."""

    # frob:ticket T-2584
    # frob:tests tests/unit/test_cycle_waiver.py::TestCycleWaiverPipeline.test_unwaived_cycle_reports  # noqa: E501
    def test_unwaived_cycle_reports(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/_python.py::_run_cycle kind="unit"
        _make_cyclic_fixture(tmp_path, waiver_in=None)
        result = _run_cycle(tmp_path)
        assert len(result.diagnostics) == 1, (
            f"expected exactly one unwaived CYCLE001 finding; got {result.diagnostics}"
        )
        assert result.diagnostics[0].code == "CYCLE001"

    # frob:ticket T-2584
    # frob:tests tests/unit/test_cycle_waiver.py::TestCycleWaiverPipeline.test_matching_waiver_suppresses_the_cycle  # noqa: E501
    def test_matching_waiver_suppresses_the_cycle(self, tmp_path: Path) -> None:
        """A `frob:waive CYCLE001` in the cycle's own representative file
        (the lower-sorted of the two nodes -- `_cycle_representative_file`)
        suppresses the finding entirely. This is the exact repro T-2584
        recorded by hand: adding the comment used to change NOTHING,
        byte-for-byte identical diagnostic text before and after."""
        # frob:tests src/frob/check/_python.py::_run_cycle kind="unit"
        # frob:tests src/frob/check/_python.py::_cycle_apply_waivers kind="unit"
        _make_cyclic_fixture(tmp_path, waiver_in="a.py")  # min("a.py","b.py")=a.py
        result = _run_cycle(tmp_path)
        assert result.diagnostics == [], (
            f"a matching frob:waive CYCLE001 must suppress the cycle; got "
            f"{result.diagnostics}"
        )

    # frob:ticket T-2584
    # frob:tests tests/unit/test_cycle_waiver.py::TestCycleWaiverPipeline.test_unrelated_files_waiver_does_not_suppress  # noqa: E501
    def test_unrelated_files_waiver_does_not_suppress(self, tmp_path: Path) -> None:
        """Negative control: a `frob:waive CYCLE001` in a THIRD file that
        is not part of the cycle must not suppress an unrelated cycle --
        the match is per representative-file, not rule-wide."""
        # frob:tests src/frob/check/_python.py::_cycle_apply_waivers kind="unit"
        _make_cyclic_fixture(tmp_path, waiver_in="c.py")
        result = _run_cycle(tmp_path)
        assert len(result.diagnostics) == 1, (
            f"an unrelated file's waiver must not suppress this cycle; got "
            f"{result.diagnostics}"
        )

    # frob:ticket T-2584
    # frob:tests tests/unit/test_cycle_waiver.py::TestCycleWaiverPipeline.test_missing_reason_is_not_silently_honored  # noqa: E501
    def test_missing_reason_is_not_silently_honored(self, tmp_path: Path) -> None:
        """A waiver comment with no `reason=` must not suppress anything --
        `_apply_waivers`'s WAIVE001 requirement is inherited unchanged by
        going through the real pipeline, not bypassed."""
        # frob:tests src/frob/check/_python.py::_cycle_apply_waivers kind="unit"
        _write(
            tmp_path / "pyproject.toml",
            '[project]\nname = "pkg"\n\n'
            '[tool.setuptools]\npackages = { find = { where = ["src"] } }\n',
        )
        _write(tmp_path / "src" / "pkg" / "__init__.py", "")
        _write(
            tmp_path / "src" / "pkg" / "a.py",
            "# frob:waive CYCLE001\nimport pkg.b\n",
        )
        _write(tmp_path / "src" / "pkg" / "b.py", "import pkg.a\n")
        result = _run_cycle(tmp_path)
        assert len(result.diagnostics) == 1, (
            "a frob:waive with no reason= must not suppress a CYCLE001 "
            f"finding; got {result.diagnostics}"
        )


# frob:ticket T-4056
def test_windows_shaped_relative_path_str_disagrees_with_as_posix() -> None:
    """T-4056 mechanism proof: on win32, `str(Path.relative_to(...))` and
    `Path.relative_to(...).as_posix()` are DIFFERENT strings for any
    multi-component path -- this is what made every `_build_import_graph`
    node id (built with the bare, pre-fix `str()`) permanently unequal to
    every edge target `resolve_local_import` returns (`as_posix()`,
    always), so Tarjan saw only graph singletons and CYCLE001 silently
    reported "no cycles" on a real, unwaived cycle.

    This assertion is a PROVEN claim, not a platform simulation of the
    kind that misled T-3947/T-3948: `PureWindowsPath.__str__` and
    `.as_posix()` are pure Python string methods with no OS dispatch
    (unlike `fnmatch`'s `os.path.normcase`, which genuinely behaves
    differently per-platform) -- `ntpath` is used directly, for the same
    reason, to keep the claim in terms of the real Windows path flavour
    rather than a `Path` object whose separator is actually `/` on this
    (posix) test-running machine. What this test does NOT prove is that
    `_build_import_graph`'s real behavior on a real Windows CI runner
    matches this reasoning end to end -- that still needs a real Windows
    run (T-3936)."""
    windows_rel = PureWindowsPath("pkg", "a.py")
    assert str(windows_rel) == "pkg\\a.py"
    assert windows_rel.as_posix() == "pkg/a.py"
    assert str(windows_rel) != windows_rel.as_posix()
    # ntpath (the real win32 path module) agrees with PureWindowsPath here
    # -- there is no separate os-dispatch step being skipped.
    assert ntpath.join("pkg", "a.py") == "pkg\\a.py"
