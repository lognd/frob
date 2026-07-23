"""Regression coverage for T-0769: docstring prose counted as an observed
capability (the `_concurrency.py` fork/pool-hazard-documentation false
positive) -- both the set-level `frob.vet._capability.scan_file_capabilities`
raw-text scanner and the line-level `frob.strata._effects` observation used
by THREAT004/`check_capability_conformance` (strata's SYS100 selfconform
delegate) must exclude comment AND docstring prose, never just comments.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, Node, bind_code, check_capability_conformance
from frob.vet._capability import (
    non_executable_line_numbers,
    scan_file_capabilities,
)

#: reconstructs the reported shape (T-0769 ticket body): docstrings AND
#: comments mention subprocess.Popen(...)/os.fork()/multiprocessing.Pool(...)
#: prose describing hazards, with no real exec-capable code anywhere in the
#: module -- the mitigation already on `main` (T-0695's docstring reword)
#: means this exact shape no longer exists in the live repo, so the
#: regression test must build its own fixture to keep exercising it.
_DOCSTRING_AND_COMMENT_PROSE_ONLY = '''"""Concurrency hazard notes.

Do not fork worker processes with subprocess.Popen(...) or os.fork() here --
this module intentionally avoids multiprocessing.Pool(...) for the reasons
documented in docs/design/concurrency-hazards.md.
"""


def describe_hazards() -> str:
    """Return prose about subprocess.Popen(...) and os.fork() -- documentation
    only, no multiprocessing.Pool(...) call is ever made.
    """
    # subprocess.Popen(...) and os.fork() are mentioned here in a COMMENT too,
    # never actually called -- multiprocessing.Pool(...) likewise.
    return "see docs/design/concurrency-hazards.md"
'''

#: positive control: a real exec call outside any comment/docstring, so the
#: fix must not blind the scanner to genuine exec observations.
_REAL_EXEC_CALL = (
    "import subprocess\n\n\n"
    "def run_it() -> None:\n"
    '    """Run a real subprocess -- an actual exec call, not prose."""\n'
    "    subprocess.Popen(['ls'])\n"
)


class TestDocstringProseNotObservedSetLevel:
    # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
    def test_docstring_and_comment_prose_yields_no_exec_capability(
        self, tmp_path: Path
    ) -> None:
        pkg = tmp_path / "concurrency.py"
        pkg.write_text(_DOCSTRING_AND_COMMENT_PROSE_ONLY)
        assert "exec" not in scan_file_capabilities(pkg)

    # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
    def test_real_exec_call_still_observed(self, tmp_path: Path) -> None:
        pkg = tmp_path / "real_exec.py"
        pkg.write_text(_REAL_EXEC_CALL)
        assert "exec" in scan_file_capabilities(pkg)


class TestDocstringProseNotObservedLineLevel:
    # frob:tests src/frob/vet/_capability.py::non_executable_line_numbers kind="unit"
    def test_prose_only_lines_report_zero_exec_observation_via_selfconform(
        self, tmp_path: Path
    ) -> None:
        # T-0769: the exact reported mechanism -- strata's THREAT004 delegate
        # (`check_capability_conformance`, `frob.strata._effects._line_
        # effects`) is the SYS100 selfconform path that missed this. A node
        # with NO `may` exec declaration must still conform (zero
        # violations) when the only "exec" text in its bound code is
        # docstring/comment prose.
        (tmp_path / "svc").mkdir()
        (tmp_path / "svc" / "concurrency.py").write_text(
            _DOCSTRING_AND_COMMENT_PROSE_ONLY
        )
        model = KernelModel(
            nodes=(Node(id="Svc", trust="trusted", attrs=("code=svc/**",)),)
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/vet/_capability.py::non_executable_line_numbers kind="unit"
    def test_real_exec_call_still_flagged_via_selfconform(self, tmp_path: Path) -> None:
        # Positive control mirroring the prose-only case above: a node with
        # NO `may` exec declaration and a REAL exec call must still be a
        # conformance violation -- the docstring/comment exclusion must not
        # blind the line-level path to genuine exec observations either.
        (tmp_path / "svc").mkdir()
        (tmp_path / "svc" / "real_exec.py").write_text(_REAL_EXEC_CALL)
        model = KernelModel(
            nodes=(Node(id="Svc", trust="trusted", attrs=("code=svc/**",)),)
        )
        binding = bind_code(model, tmp_path).danger_ok
        report = check_capability_conformance(model, binding, tmp_path)
        assert any(v.kind == "exec" for v in report.violations)

    # frob:tests src/frob/vet/_capability.py::non_executable_line_numbers kind="unit"
    def test_non_executable_line_numbers_covers_docstring_and_comment(
        self, tmp_path: Path
    ) -> None:
        pkg = tmp_path / "mixed.py"
        pkg.write_text(_DOCSTRING_AND_COMMENT_PROSE_ONLY)
        lines = pkg.read_text().splitlines()
        prose_lines = non_executable_line_numbers(pkg)
        # every line mentioning a hazard needle in this fixture is either
        # inside the module docstring, the function docstring, or a `#`
        # comment -- none of them is real code, so all must be reported.
        needle_lines = {
            i
            for i, line in enumerate(lines, start=1)
            if "subprocess.Popen" in line or "os.fork" in line or "Pool(" in line
        }
        assert needle_lines
        assert needle_lines <= prose_lines
