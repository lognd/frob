"""Regression tests for T-1335's `make coverage` fixes: a
`frob check --stamp-coverage` failure after a green suite must fail the
whole recipe (not silently exit 0), and `coverage xml` must survive a
combined-data entry pointing at a torn-down source path."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

#: T-1335: repo root, resolved the same way every other Makefile-adjacent
#: test in this repo does (tests/unit/test_makefile_coverage.py -> repo
#: root is two levels up).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MAKEFILE = (_REPO_ROOT / "Makefile").read_text(encoding="utf-8")


def _recipe_tail() -> str:
    """Slice the exact stamp-propagation shell fragment out of the live
    `coverage:` recipe (from `uv run coverage combine` through the final
    `exit $$status`), so this test exercises the REAL Makefile text
    rather than a hand-copied reimplementation that could drift from it.
    """
    match = re.search(
        r"^\tuv run coverage combine; \\\n(?:\t.*\\\n)*\texit \$\$stamp_status$",
        _MAKEFILE,
        re.MULTILINE,
    )
    assert match is not None, "coverage: recipe tail not found in Makefile"
    # Makefile `$$` escapes a literal `$` for make itself; drop one `$`
    # from each `$$` and strip the leading tab + trailing line-continuation
    # backslashes so the fragment is plain, directly-runnable shell.
    body = match.group(0).replace("$$", "$")
    lines = [line[1:].rstrip("\\").rstrip() for line in body.splitlines()]
    return "\n".join(lines)


def _run_fragment(
    tmp_path: Path, stub_bin: Path, env_extra: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run the recipe tail seeded with `status=0` (green suite), the
    scenario `TestStampFailurePropagation` exercises."""
    return _run_fragment_with_status(tmp_path, stub_bin, 0, env_extra)


# frob:ticket T-1363
def _run_fragment_with_status(
    tmp_path: Path, stub_bin: Path, status: int, env_extra: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run the recipe tail seeded with an arbitrary pytest-run `status`
    (0 = green suite, nonzero = the T-1363 failed/partial-run scenario)."""
    env = {"PATH": f"{stub_bin}:/usr/bin:/bin", **env_extra}
    script = f"status={status}\n" + _recipe_tail()
    return subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _write_stub(stub_bin: Path, name: str, body: str) -> None:
    path = stub_bin / name
    path.write_text(f"#!/bin/bash\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


class TestStampFailurePropagation:
    """`frob:tests` T-1335's acceptance criterion 0: a green suite with a
    failing stamp-coverage step must exit the `coverage` recipe nonzero,
    naming the stamp failure."""

    def test_stamp_failure_after_green_suite_fails_the_recipe(self, tmp_path):
        """A `frob check --stamp-coverage` failure after status=0 (the
        pytest run already succeeded) must still fail the whole recipe,
        with an ERROR line naming it -- this is T-1335 defect (1)."""
        stub_bin = tmp_path / "bin"
        stub_bin.mkdir()
        # `uv` stands in for both the pytest run (status=0, "green suite")
        # and the failing stamp-coverage call (`frob check --stamp-coverage`
        # is invoked via `uv run frob ...`).
        _write_stub(
            stub_bin,
            "uv",
            'if [ "$2" = "frob" ] && [ "$3" = "check" ]; then\n  exit 7\nfi\nexit 0\n',
        )
        result = _run_fragment(tmp_path, stub_bin, {})
        assert result.returncode == 7, result.stdout + result.stderr
        assert "stamp-coverage failed" in (result.stdout + result.stderr)

    def test_green_suite_and_green_stamp_still_exits_zero(self, tmp_path):
        """Unchanged success path: a green suite and a successful stamp
        write must still exit 0 (no regression from the propagation fix)."""
        stub_bin = tmp_path / "bin"
        stub_bin.mkdir()
        _write_stub(stub_bin, "uv", "exit 0\n")
        result = _run_fragment(tmp_path, stub_bin, {})
        assert result.returncode == 0, result.stdout + result.stderr


# frob:ticket T-1363
def _write_partial_xml_stub(stub_bin: Path, stamp_marker: Path) -> None:
    """A `uv` stub that answers `coverage combine`/`coverage xml -o PATH`
    for real (writing recognizable content to whatever `-o` path it is
    given) and records whether `frob check --stamp-coverage` was ever
    invoked, without actually touching any real coverage artifact itself."""
    _write_stub(
        stub_bin,
        "uv",
        f"""
if [ "$2" = "coverage" ] && [ "$3" = "xml" ]; then
  out=""
  prev=""
  for a in "$@"; do
    if [ "$prev" = "-o" ]; then out="$a"; fi
    prev="$a"
  done
  echo "PARTIAL_XML_FROM_THIS_RUN" > "$out"
  exit 0
fi
if [ "$2" = "frob" ] && [ "$3" = "check" ]; then
  touch {stamp_marker}
  exit 0
fi
exit 0
""",
    )


# frob:ticket T-1363
class TestFailedRunNeverPromotesPartialData:
    """`frob:tests` T-1363's acceptance criterion 0/1: a nonzero pytest
    exit status must leave the previous `coverage.xml`, `.frob/
    coverage-stamp`, and committed `frob-coverage.lock.json` completely
    untouched -- the failed run's own data must never be promoted, even
    though `coverage combine`/`coverage xml` still ran and produced
    something. This reproduces the real 2026-07-31 incident: a `make
    coverage` run that exited 2 (six failing tests) still overwrote good
    stamp data with a near-empty measurement."""

    # frob:tests tests/unit/test_makefile_coverage.py::TestFailedRunNeverPromotesPartialData.test_failed_run_leaves_coverage_xml_and_stamp_untouched  # noqa: E501
    def test_failed_run_leaves_coverage_xml_and_stamp_untouched(self, tmp_path):
        """A nonzero final `status` must exit nonzero without ever calling
        `frob check --stamp-coverage` (the only writer of the stamp and the
        committed lock), and must leave a pre-existing `coverage.xml`
        byte-for-byte as it was."""
        stub_bin = tmp_path / "bin"
        stub_bin.mkdir()
        stamp_marker = tmp_path / "stamp-coverage-was-called"
        _write_partial_xml_stub(stub_bin, stamp_marker)

        good_xml = tmp_path / "coverage.xml"
        good_xml.write_text("OLD_GOOD_COVERAGE_XML\n", encoding="utf-8")
        (tmp_path / ".frob").mkdir()
        stamp_path = tmp_path / ".frob" / "coverage-stamp"
        stamp_path.write_text('{"source_sha": "old-good-sha"}\n', encoding="utf-8")
        lock_path = tmp_path / "frob-coverage.lock.json"
        lock_path.write_text('{"source_sha": "old-good-sha"}\n', encoding="utf-8")

        result = _run_fragment_with_status(tmp_path, stub_bin, 2, {})

        assert result.returncode == 2, result.stdout + result.stderr
        assert not stamp_marker.exists(), (
            "frob check --stamp-coverage must never be invoked on a failed run"
        )
        assert good_xml.read_text(encoding="utf-8") == "OLD_GOOD_COVERAGE_XML\n"
        assert (
            stamp_path.read_text(encoding="utf-8") == '{"source_sha": "old-good-sha"}\n'
        )
        assert (
            lock_path.read_text(encoding="utf-8") == '{"source_sha": "old-good-sha"}\n'
        )
        # The failed run's own data is still captured for inspection, just
        # never promoted to the trusted paths.
        partial = tmp_path / ".frob" / "coverage.partial.xml"
        assert partial.read_text(encoding="utf-8") == "PARTIAL_XML_FROM_THIS_RUN\n"

    # frob:tests tests/unit/test_makefile_coverage.py::TestFailedRunNeverPromotesPartialData.test_successful_run_still_promotes_coverage_xml  # noqa: E501
    def test_successful_run_still_promotes_coverage_xml(self, tmp_path):
        """Unchanged success path: `status=0` still promotes the combined
        xml to the real `coverage.xml` and calls `frob check
        --stamp-coverage` (no regression from the T-1363 guard)."""
        stub_bin = tmp_path / "bin"
        stub_bin.mkdir()
        stamp_marker = tmp_path / "stamp-coverage-was-called"
        _write_partial_xml_stub(stub_bin, stamp_marker)
        (tmp_path / ".frob").mkdir()

        result = _run_fragment_with_status(tmp_path, stub_bin, 0, {})

        assert result.returncode == 0, result.stdout + result.stderr
        assert stamp_marker.exists()
        good_xml = tmp_path / "coverage.xml"
        assert good_xml.read_text(encoding="utf-8") == "PARTIAL_XML_FROM_THIS_RUN\n"


class TestCoverageXmlIgnoreErrors:
    """`frob:tests` T-1335's acceptance criterion 1: `coverage.xml` must
    still be produced when the combined data references a torn-down
    fixture path with no importable source."""

    def test_coverage_xml_invocations_pass_ignore_errors(self):
        """Both `coverage:` and `coverage-fast:` must invoke `coverage
        xml` with `-i`/`--ignore-errors` -- this is T-1335 defect (2)'s
        actual fix (the same flag the T-1320 manual recovery used)."""
        xml_calls = re.findall(r"uv run coverage xml[^\n;]*", _MAKEFILE)
        assert len(xml_calls) == 2, xml_calls
        assert all("-i" in call for call in xml_calls), xml_calls

    # frob:ticket T-1362
    def test_combine_then_xml_survives_a_stale_fixture_path(self, tmp_path):
        """Reproduction of the T-1320 incident via the same CLI the
        Makefile uses: coverage data referencing a source file that no
        longer exists must still let `coverage xml -i` (as the fixed
        recipe now invokes it) produce a report, not abort outright."""
        real_src = tmp_path / "real.py"
        real_src.write_text("x = 1\n", encoding="utf-8")
        stale_src = tmp_path / "gone.py"
        stale_src.write_text("y = 2\n", encoding="utf-8")

        # kwargs are passed as literals at each call site (not via a
        # dict-unpack) so `ty` can resolve subprocess.run's real overload
        # from the literal `text=True`/`check=True` arguments.
        subprocess.run(
            ["coverage", "run", "--branch", str(real_src)],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["coverage", "run", "--branch", "--append", str(stale_src)],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )
        # Tear down the fixture path AFTER measurement, exactly like the
        # T-1320 incident's ephemeral subprocess-test fixture.
        stale_src.unlink()

        # Without -i this fails outright (coverage.misc.NoSource) on the
        # now-missing gone.py entry -- -i/--ignore-errors is exactly what
        # the fixed Makefile recipe now passes.
        no_flag = subprocess.run(
            ["coverage", "xml"], cwd=tmp_path, capture_output=True, text=True
        )
        assert no_flag.returncode != 0, (
            "fixture no longer reproduces the T-1320 failure"
        )
        assert not (tmp_path / "coverage.xml").exists()

        with_flag = subprocess.run(
            ["coverage", "xml", "-i"], cwd=tmp_path, capture_output=True, text=True
        )
        assert with_flag.returncode == 0, with_flag.stdout + with_flag.stderr
        xml_out = tmp_path / "coverage.xml"
        assert xml_out.exists()
        assert "real.py" in xml_out.read_text(encoding="utf-8")


# frob:ticket T-1353
class TestCombineRecoversDisjointSessions:
    """T-1353: the `coverage:` recipe's crash-recovery shape is exactly two
    separate pytest-cov sessions against the SAME `data_file` (an initial
    parallel run, then a `--cov-append` rerun), unioned by one `coverage
    combine` at the end. Several agents independently reported deflated
    per-symbol numbers (a function's `def` line hit, every body line not)
    that read like this union losing data rather than a crash simply
    dropping it outright. This replays that exact two-session shape
    directly against `coverage`'s own CLI (no pytest/xdist involved, so it
    isolates combine's own behavior from any crash/flake in the suite
    itself) and asserts the union recovers full coverage of BOTH halves --
    a real regression here would mean the recipe's `--cov-append` +
    `combine` shape cannot be trusted to recover a crashed worker's data
    even when nothing crashes on replay."""

    # frob:tests tests/unit/test_makefile_coverage.py::TestCombineRecoversDisjointSessions.test_two_disjoint_sessions_combine_to_full_coverage  # noqa: E501
    def test_two_disjoint_sessions_combine_to_full_coverage(self, tmp_path):
        """Session A covers only `branch_a`, session B (a separate
        `coverage run`, `--append`) covers only `branch_b` of the SAME
        module -- the union must report BOTH branches covered, not just
        whichever session's data happened to combine last."""
        mod = tmp_path / "mod.py"
        mod.write_text(
            "def pick(flag):\n"
            "    if flag:\n"
            "        return 'a'\n"
            "    else:\n"
            "        return 'b'\n",
            encoding="utf-8",
        )
        driver_a = tmp_path / "drive_a.py"
        driver_a.write_text(
            "import mod\nassert mod.pick(True) == 'a'\n", encoding="utf-8"
        )
        driver_b = tmp_path / "drive_b.py"
        driver_b.write_text(
            "import mod\nassert mod.pick(False) == 'b'\n", encoding="utf-8"
        )

        # Session A: only the `if` branch runs.
        subprocess.run(
            ["coverage", "run", "--branch", str(driver_a)],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )
        # Session B: a SEPARATE invocation (like the recipe's serial
        # recovery rerun), `--append`, only the `else` branch runs.
        subprocess.run(
            ["coverage", "run", "--branch", "--append", str(driver_b)],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )

        report = subprocess.run(
            ["coverage", "report", "--show-missing", "mod.py"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert report.returncode == 0, report.stdout + report.stderr
        # Both branch bodies (lines 3 and 5) must show as covered in the
        # UNION -- a last-write-wins loss would report one of them missing.
        assert "100%" in report.stdout, report.stdout
