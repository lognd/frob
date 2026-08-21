"""Regression coverage for T-0769: docstring prose counted as an observed
capability (the `_concurrency.py` fork/pool-hazard-documentation false
positive) -- both the set-level `frob.vet._capability.scan_file_capabilities`
raw-text scanner and the line-level `frob.strata._effects` observation used
by THREAT004/`check_capability_conformance` (strata's SYS100 selfconform
delegate) must exclude comment AND docstring prose, never just comments.
"""

from __future__ import annotations

from pathlib import Path

import frob.vet._capability as _capability_mod
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
    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
    def test_docstring_and_comment_prose_yields_no_exec_capability(
        self, tmp_path: Path
    ) -> None:
        pkg = tmp_path / "concurrency.py"
        pkg.write_text(_DOCSTRING_AND_COMMENT_PROSE_ONLY)
        assert "exec" not in scan_file_capabilities(pkg)

    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
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

    # frob:tests src/frob/vet/_capability.py::non_executable_line_numbers kind="unit"
    def test_non_executable_line_numbers_no_spans_is_empty(
        self, tmp_path: Path
    ) -> None:
        # A file with no comment/docstring spans at all (pure code, no
        # prose) hits the early `if not spans: return frozenset()` guard.
        pkg = tmp_path / "plain.py"
        pkg.write_text("x = 1\ny = 2\n")
        assert non_executable_line_numbers(pkg) == frozenset()

    # frob:tests src/frob/vet/_capability.py::non_executable_line_numbers kind="unit"
    def test_non_executable_line_numbers_missing_file_is_empty(
        self, tmp_path: Path
    ) -> None:
        # A path that does not exist at all: `_non_executable_byte_spans`
        # itself reads nothing, so the OSError-tolerant "never raises"
        # contract holds even before `read_bytes()` is reached.
        assert (
            non_executable_line_numbers(tmp_path / "does-not-exist.py") == frozenset()
        )

    # frob:tests src/frob/vet/_capability.py::non_executable_line_numbers kind="unit"
    def test_non_executable_line_numbers_read_bytes_oserror_is_empty(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # Specifically exercises the function's own `raw = path.read_bytes()`
        # except-OSError branch (distinct from the "no spans at all" guard
        # above): the file DOES have a real comment span (so spans is
        # non-empty and the code proceeds past the first guard), but the
        # `Path.read_bytes()` call inside `non_executable_line_numbers`
        # itself fails.
        pkg = tmp_path / "commented.py"
        pkg.write_text("# a comment\nx = 1\n")
        # Warm the module-level span cache with a real, successful parse
        # first -- `_non_executable_byte_spans` memoizes per (path,
        # content-hash), so the SECOND call below reaches this function's
        # own `raw = path.read_bytes()` line without needing tree-sitter
        # to parse again.
        assert non_executable_line_numbers(pkg) == {1}

        from pathlib import Path as _Path

        real_read_bytes = _Path.read_bytes

        def _raising_read_bytes(self):
            if self == pkg:
                raise OSError("simulated: read failure")
            return real_read_bytes(self)

        monkeypatch.setattr(_Path, "read_bytes", _raising_read_bytes)
        assert non_executable_line_numbers(pkg) == frozenset()

    # frob:tests src/frob/vet/_capability.py::non_executable_line_numbers kind="unit"
    def test_non_executable_line_numbers_surprising_span_shape_is_empty(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # T-1371: "never raises" covers a surprising span shape from
        # `_non_executable_byte_spans` too, not just the read failure --
        # a non-int span element makes `raw.count(b"\n", 0, start)` raise
        # TypeError, which the function's own except clause must swallow
        # rather than propagate.
        pkg = tmp_path / "plain.py"
        pkg.write_text("x = 1\ny = 2\n")

        monkeypatch.setattr(
            _capability_mod,
            "_non_executable_byte_spans",
            lambda path: ((None, 3),),
        )
        assert non_executable_line_numbers(pkg) == frozenset()


# T-1626: capability detection must be symbol-resolved with full alias
# support, not lexical needles -- these are the ticket's own worked
# evasion examples (indirect binding through a dict/list literal,
# `functools.partial(dangerous, ...)`), each as a set-level
# `scan_file_capabilities` regression. A plain substring needle scan finds
# NONE of these (no literal "subprocess.run(" text anywhere in the
# fixtures below); the T-0328/T-1626 import-and-container-alias-aware
# resolver must.
class TestSymbolResolvedContainerAndPartialEvasions:
    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
    def test_dict_literal_dispatch_resolves(self, tmp_path: Path) -> None:
        pkg = tmp_path / "dict_dispatch.py"
        pkg.write_text(
            "import subprocess\n\n\n"
            "def run(cmd):\n"
            '    handlers = {"run": subprocess.run}\n'
            '    handlers["run"](cmd)\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
    def test_list_literal_dispatch_resolves(self, tmp_path: Path) -> None:
        pkg = tmp_path / "list_dispatch.py"
        pkg.write_text(
            "import subprocess\n\n\n"
            "def run(cmd):\n"
            "    handlers = [subprocess.run]\n"
            "    handlers[0](cmd)\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
    def test_dict_literal_dispatch_with_non_dangerous_value_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # Negative control: a literal-keyed dict dispatch to a BENIGN
        # callable must not spuriously flag "exec" -- the container-alias
        # resolver must resolve to the real target, not just to "any
        # subscript dispatch".
        pkg = tmp_path / "dict_dispatch_benign.py"
        pkg.write_text(
            "def helper(x):\n"
            "    return x\n\n\n"
            "def run(cmd):\n"
            '    handlers = {"run": helper}\n'
            '    handlers["run"](cmd)\n'
        )
        assert "exec" not in scan_file_capabilities(pkg)

    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
    def test_functools_partial_wrapping_dangerous_op_resolves(
        self, tmp_path: Path
    ) -> None:
        pkg = tmp_path / "partial_dispatch.py"
        pkg.write_text(
            "import functools\n"
            "import subprocess\n\n\n"
            "def run(cmd):\n"
            "    p = functools.partial(subprocess.run, cmd)\n"
            "    p()\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
    def test_functools_partial_called_directly_resolves(self, tmp_path: Path) -> None:
        pkg = tmp_path / "partial_direct.py"
        pkg.write_text(
            "import functools\n"
            "import subprocess\n\n\n"
            "def run(cmd):\n"
            "    functools.partial(subprocess.run, cmd)()\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
    def test_partial_from_import_alias_resolves(self, tmp_path: Path) -> None:
        # `from functools import partial as p` -- the alias itself must
        # resolve through the ordinary import table before the
        # functools.partial special-case in `_resolve_py_expr` can fire.
        pkg = tmp_path / "partial_alias.py"
        pkg.write_text(
            "from functools import partial as p\n"
            "import subprocess\n\n\n"
            "def run(cmd):\n"
            "    wrapped = p(subprocess.run, cmd)\n"
            "    wrapped()\n"
        )
        assert "exec" in scan_file_capabilities(pkg)


class TestModeAwareOpenCall:
    """T-2457: `open()`/`.open()` must be classified by its MODE ARGUMENT,
    not by the bare presence of the substring `open(` -- the pre-fix
    detector reported `fs-write` for a read-only `toml_path.open("rb")`
    call, forcing seven false capability declarations into
    `design/frob.strata` (ticket body). Covers all three of the ticket's
    own acceptance controls: must-now-be-silent, must-still-fire, and
    must-still-fire-indirect."""

    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
    def test_read_mode_open_reports_fs_read_not_fs_write(self, tmp_path: Path) -> None:
        """Control 1 (must-now-be-silent): a module whose only filesystem
        access is `open(path, "rb")` must report `fs-read`, never
        `fs-write`."""
        pkg = tmp_path / "read_only.py"
        pkg.write_text(
            "def load(toml_path):\n"
            '    with toml_path.open("rb") as f:\n'
            "        return f.read()\n"
        )
        observed = scan_file_capabilities(pkg)
        assert "fs-write" not in observed
        assert "fs-read" in observed

    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
    def test_default_mode_open_is_read_not_write(self, tmp_path: Path) -> None:
        """A bare `open(path)` (Python's own default mode is `"r"`) must
        report `fs-read`, never `fs-write` -- default-mode opens are the
        most common shape and must not regress into a false positive."""
        pkg = tmp_path / "default_mode.py"
        pkg.write_text(
            "def load(path):\n    with open(path) as f:\n        return f.read()\n"
        )
        observed = scan_file_capabilities(pkg)
        assert "fs-write" not in observed
        assert "fs-read" in observed

    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
    def test_write_mode_open_still_reports_fs_write(self, tmp_path: Path) -> None:
        """Control 2 (must-still-fire): `open(path, "w")` must still report
        `fs-write` -- the false-positive fix must not become a false
        negative."""
        pkg = tmp_path / "write_mode.py"
        pkg.write_text(
            'def save(path):\n    with open(path, "w") as f:\n        f.write("x")\n'
        )
        assert "fs-write" in scan_file_capabilities(pkg)

    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
    def test_append_mode_open_still_reports_fs_write(self, tmp_path: Path) -> None:
        """Control 2 (must-still-fire): `open(path, "a")` must still report
        `fs-write`."""
        pkg = tmp_path / "append_mode.py"
        pkg.write_text(
            'def log(path):\n    with open(path, "a") as f:\n        f.write("x")\n'
        )
        assert "fs-write" in scan_file_capabilities(pkg)

    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
    def test_dotwrite_call_still_reports_fs_write(self, tmp_path: Path) -> None:
        """Control 2 (must-still-fire): a bare `.write(...)` call (the
        entry's other, unambiguous needle) must still report `fs-write`
        independent of the mode-aware `open()` classification."""
        pkg = tmp_path / "dotwrite.py"
        pkg.write_text("def dump(stream):\n    stream.write('x')\n")
        assert "fs-write" in scan_file_capabilities(pkg)

    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
    def test_indirect_write_operations_still_reported(self, tmp_path: Path) -> None:
        """Control 3 (must-still-fire-indirect): `Path.write_text`,
        `shutil.move`, and `os.replace` -- write operations that never go
        through `open()` at all -- must still report `fs-write`, proving
        the mode-aware `open()` change did not disturb the OTHER,
        already-precise fs-write registry entries."""
        pkg = tmp_path / "indirect.py"
        pkg.write_text(
            "from pathlib import Path\n"
            "import shutil, os\n\n\n"
            "def mutate(p, q):\n"
            '    Path(p).write_text("x")\n'
            "    shutil.move(p, q)\n"
            "    os.replace(p, q)\n"
        )
        assert "fs-write" in scan_file_capabilities(pkg)

    # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities kind="unit"
    def test_dynamic_mode_expression_fails_closed_to_write(
        self, tmp_path: Path
    ) -> None:
        """A non-literal mode expression (a variable, not a plain string
        literal) is classified OPAQUE and treated as `fs-write`, fail-
        closed -- a security detector's false negative is worse than its
        false positive (ticket body, "the direction that actually hurts
        in a security detector")."""
        pkg = tmp_path / "dynamic_mode.py"
        pkg.write_text(
            "def load(path, mode):\n    with open(path, mode) as f:\n        return f\n"
        )
        assert "fs-write" in scan_file_capabilities(pkg)
