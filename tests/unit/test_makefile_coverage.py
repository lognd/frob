"""Regression tests for T-1335's `make coverage` fixes: a
`frob check --stamp-coverage` failure after a green suite must fail the
whole recipe (not silently exit 0), and `coverage xml` must survive a
combined-data entry pointing at a torn-down source path."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


# frob:ticket T-1373
def _coverage_clean_env() -> dict[str, str]:
    """Environment for a NESTED `coverage` subprocess, with every
    `COVERAGE_*` variable stripped.

    T-1373: these tests drive real `coverage run` children. Under an outer
    `make coverage` the parent's `COVERAGE_FILE`/`COVERAGE_PROCESS_START`
    are inherited, so the child writes into -- and `--append`s onto -- the
    parent's data file instead of its own tmp_path one, and exits 1. The
    child must measure only itself.
    """
    return {k: v for k, v in os.environ.items() if not k.startswith("COVERAGE_")}


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
        r"^\tuv run coverage combine --append; \\\n(?:\t.*\\\n)*\texit \$\$stamp_status$",
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
        """`coverage:` must invoke `coverage xml` with `-i`/
        `--ignore-errors` -- this is T-1335 defect (2)'s actual fix (the
        same flag the T-1320 manual recovery used). `coverage-fast:` no
        longer has an inline `coverage xml` call of its own (T-1526: it
        delegates to `frob coverage`, whose own `native_coverage_refresh`
        Python call already passes `-i` -- see
        `TestCoverageFastRunner.test_coverage_fast_delegates_to_frob_coverage`
        for that half's own coverage)."""
        xml_calls = re.findall(r"uv run coverage xml[^\n;]*", _MAKEFILE)
        assert len(xml_calls) == 1, xml_calls
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
            env=_coverage_clean_env(),
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["coverage", "run", "--branch", "--append", str(stale_src)],
            cwd=tmp_path,
            env=_coverage_clean_env(),
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
            ["coverage", "xml"],
            cwd=tmp_path,
            env=_coverage_clean_env(),
            capture_output=True,
            text=True,
        )
        assert no_flag.returncode != 0, (
            "fixture no longer reproduces the T-1320 failure"
        )
        assert not (tmp_path / "coverage.xml").exists()

        with_flag = subprocess.run(
            ["coverage", "xml", "-i"],
            cwd=tmp_path,
            env=_coverage_clean_env(),
            capture_output=True,
            text=True,
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
            env=_coverage_clean_env(),
            check=True,
            capture_output=True,
            text=True,
        )
        # Session B: a SEPARATE invocation (like the recipe's serial
        # recovery rerun), `--append`, only the `else` branch runs.
        subprocess.run(
            ["coverage", "run", "--branch", "--append", str(driver_b)],
            cwd=tmp_path,
            env=_coverage_clean_env(),
            check=True,
            capture_output=True,
            text=True,
        )

        report = subprocess.run(
            ["coverage", "report", "--show-missing", "mod.py"],
            cwd=tmp_path,
            env=_coverage_clean_env(),
            capture_output=True,
            text=True,
        )
        assert report.returncode == 0, report.stdout + report.stderr
        # Both branch bodies (lines 3 and 5) must show as covered in the
        # UNION -- a last-write-wins loss would report one of them missing.
        assert "100%" in report.stdout, report.stdout


def _generated_subprocess_rc(tmp_path: Path) -> str:
    """Run the exact `printf` fragment the `coverage:` recipe uses to
    build `.frob/coverage-subprocess.rc` and return its stdout.

    Extracts the real `printf ... > .frob/coverage-subprocess.rc` block out
    of the live Makefile text (mirroring `_recipe_tail`'s approach above) so
    this test exercises the actual recipe, not a hand-copied reimplementation
    that could silently drift from it.
    """
    match = re.search(
        r"^\tprintf '%s\\n' \\\n(?:\t\t'.*'( \\)?\n)*"
        r"\t\t> \.frob/coverage-subprocess\.rc$",
        _MAKEFILE,
        re.MULTILINE,
    )
    assert match is not None, "coverage-subprocess.rc printf block not found"
    body = match.group(0)
    # Drop the trailing `> .frob/coverage-subprocess.rc` redirect and run
    # just the `printf` call itself, capturing stdout instead of the file.
    # Unlike `_recipe_tail`, the line-continuation backslashes here are
    # bash's OWN multi-line-command syntax (one `printf` call spanning
    # several lines), not Makefile recipe-line escaping -- they must be
    # preserved, only the leading Makefile recipe tab is Makefile-specific.
    body = body.rsplit("\n", 1)[0]
    lines = [line[1:] for line in body.splitlines()]
    script = "\n".join(lines).replace("$(CURDIR)", str(tmp_path))
    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


# frob:ticket T-1235
class TestSubprocessRcIsAbsoluteAndConcurrencyAware:
    """`frob:tests` T-1235's acceptance criteria 0 and 1: the generated
    `.frob/coverage-subprocess.rc` must use ABSOLUTE `source`/`data_file`
    (a relative value resolves against a subprocess child's own cwd, not
    the repo root, measuring nothing and stranding empty `.coverage.*`
    files -- loss A of the 2026-07-29 attribution diagnosis), and both the
    rc and `pyproject.toml`'s `[tool.coverage.run]` must declare
    `concurrency = multiprocessing, thread` plus `sigterm = true` so
    ProcessPoolExecutor gate workers are recorded (loss B)."""

    # frob:tests tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware.test_rc_uses_absolute_source_and_data_file  # noqa: E501
    def test_rc_uses_absolute_source_and_data_file(self, tmp_path):
        """The rc's `source =` and `data_file =` lines must be absolute
        paths (rooted at the invoking `$(CURDIR)`), not the bare relative
        `src/frob` that `pyproject.toml` itself uses."""
        rc = _generated_subprocess_rc(tmp_path)
        assert f"source = {tmp_path}/src/frob" in rc, rc
        assert f"data_file = {tmp_path}/.coverage" in rc, rc

    # frob:tests tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware.test_rc_declares_multiprocessing_and_sigterm  # noqa: E501
    def test_rc_declares_multiprocessing_and_sigterm(self, tmp_path):
        """The rc must enable branch/parallel/relative_files, both
        concurrency backends, `sigterm`, and the no-data-collected warning
        suppression (subprocess children legitimately import-only, no-op
        modules) -- any of these missing reproduces a real slice of the
        2026-07-29 attribution loss."""
        rc = _generated_subprocess_rc(tmp_path)
        assert "branch = True" in rc, rc
        assert "parallel = True" in rc, rc
        assert "relative_files = True" in rc, rc
        assert "sigterm = True" in rc, rc
        assert "concurrency = multiprocessing, thread" in rc, rc
        assert "disable_warnings = no-data-collected" in rc, rc

    # frob:tests tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware.test_rc_remaps_paths_back_to_source  # noqa: E501
    def test_rc_remaps_paths_back_to_source(self, tmp_path):
        """The rc's `[paths]` section must remap any `*/src/frob` prefix
        (a subprocess child's own absolute path, e.g. under a tmp fixture)
        back onto `src/frob` so `coverage combine` unions subprocess data
        with the main run's data for the SAME module, not a distinct one."""
        rc = _generated_subprocess_rc(tmp_path)
        assert "[paths]" in rc, rc
        assert "src/frob" in rc.split("[paths]", 1)[1], rc
        assert "*/src/frob" in rc.split("[paths]", 1)[1], rc

    # frob:tests tests/unit/test_makefile_coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware.test_pyproject_declares_concurrency_and_sigterm  # noqa: E501
    def test_pyproject_declares_concurrency_and_sigterm(self):
        """`pyproject.toml`'s own `[tool.coverage.run]` (governing the
        MAIN pytest-cov process, not just subprocess children) must ALSO
        declare both concurrency backends and `sigterm` -- otherwise
        in-process `ProcessPoolExecutor` gate-pool workers spawned by the
        main run itself go unrecorded (loss B of the 2026-07-29 attribution
        diagnosis), independent of the subprocess rc fixed above."""
        import tomllib

        data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text("utf-8"))
        run_cfg = data["tool"]["coverage"]["run"]
        assert run_cfg["concurrency"] == ["multiprocessing", "thread"], run_cfg
        assert run_cfg["sigterm"] is True, run_cfg


class TestCombineAppendPreservesBaseData:
    """T-1426: `coverage combine` (no `--append`) silently ERASES whatever
    real data is already in the base `.coverage` file the first time
    `CoverageData.update()` touches it in that process
    (`CoverageData._start_using`: `if not self._have_used: self.erase()`,
    only skipped when `--append` triggers `self.coverage.load()` first --
    coverage/cmdline.py's `combine` action). The `coverage:` recipe's base
    `.coverage` file already holds real data by the time it reaches
    `combine` (pytest-cov's own xdist `DistMaster.finish()` combines every
    worker's data into it in-process before pytest exits) -- so calling
    `combine` without `--append` discarded that entire in-process run,
    keeping only whatever separate satellite (subprocess-traced) data
    files happened to be lying around. This directly reproduces both the
    Makefile recipe's real invocation shape and the T-1418 finding it
    explains, using the `coverage` CLI itself (no pytest/xdist involved),
    and locks the Makefile's own recipe text so `--append` cannot silently
    regress back out."""

    # frob:tests \
    # tests/unit/test_makefile_coverage.py::TestCombineAppendPreservesBaseData.test_mak\
    # efile_recipe_uses_append
    def test_makefile_recipe_uses_append(self):
        """The live `coverage:` recipe text must call `coverage combine
        --append`, never bare `coverage combine` -- a regression here
        silently reintroduces the T-1426 data-loss mechanism with no
        other visible symptom until TEST005 numbers go inexplicably
        deflated again."""
        assert "uv run coverage combine --append" in _MAKEFILE, _MAKEFILE
        assert "uv run coverage combine;" not in _MAKEFILE, _MAKEFILE
        assert "uv run coverage combine 2>/dev/null" not in _MAKEFILE, _MAKEFILE

    # frob:tests \
    # tests/unit/test_makefile_coverage.py::TestCombineAppendPreservesBaseData.test_com\
    # bine_without_append_erases_base_data
    def test_combine_without_append_erases_base_data(self, tmp_path):
        """Ground-truth reproduction of the bug: a base data file with
        real coverage of a canary module, PLUS a separate satellite
        parallel-mode data file, combined WITHOUT `--append` -- the
        canary's real, pre-existing coverage must NOT survive (this pins
        the exact defective behavior `--append` exists to route around;
        if this ever starts passing, coverage.py's own `combine` semantics
        changed and the Makefile fix may no longer be load-bearing)."""
        canary = tmp_path / "canary.py"
        canary.write_text("def f():\n    return 1\n", encoding="utf-8")
        env = _coverage_clean_env()

        # Base run: real, non-trivial coverage of the canary lands in the
        # plain `.coverage` file -- this stands in for pytest-cov's own
        # in-process xdist combine, already done by the time the Makefile
        # reaches its own `coverage combine` step.
        subprocess.run(
            ["coverage", "run", "--branch", str(canary.name)],
            cwd=tmp_path,
            env={**env, "PYTHONPATH": str(tmp_path)},
            check=False,
            capture_output=True,
            text=True,
        )
        driver = tmp_path / "drive.py"
        driver.write_text("import canary\nassert canary.f() == 1\n", encoding="utf-8")
        subprocess.run(
            ["coverage", "run", "--branch", str(driver.name)],
            cwd=tmp_path,
            env={**env, "PYTHONPATH": str(tmp_path)},
            check=True,
            capture_output=True,
            text=True,
        )
        pre_combine = subprocess.run(
            ["coverage", "report", str(canary.name)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
        )
        assert "100%" in pre_combine.stdout, pre_combine.stdout + pre_combine.stderr

        # A separate, genuinely-parallel satellite data file (mimics a
        # COVERAGE_PROCESS_START subprocess trace) that touches an
        # unrelated file only -- the recipe's real satellite files are
        # exactly this shape.
        other = tmp_path / "other.py"
        other.write_text("def g():\n    return 2\n", encoding="utf-8")
        subprocess.run(
            [
                "coverage",
                "run",
                "--branch",
                "--parallel-mode",
                str(other.name),
            ],
            cwd=tmp_path,
            env={**env, "PYTHONPATH": str(tmp_path)},
            check=False,
            capture_output=True,
            text=True,
        )

        # WITHOUT --append: the base file's real canary data is erased.
        subprocess.run(
            ["coverage", "combine"],
            cwd=tmp_path,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        post_combine = subprocess.run(
            ["coverage", "report", str(canary.name)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
        )
        assert "0%" in post_combine.stdout, (
            "expected the known combine-without-append erasure -- if this "
            "assertion now fails, coverage.py's own semantics changed and "
            f"the Makefile's --append fix should be re-verified: {post_combine.stdout}"
        )

    # frob:tests \
    # tests/unit/test_makefile_coverage.py::TestCombineAppendPreservesBaseData.test_com\
    # bine_with_append_preserves_base_data
    def test_combine_with_append_preserves_base_data(self, tmp_path):
        """Same setup as the erasure repro above, but with `--append` (the
        Makefile's actual, fixed invocation) -- the canary's real,
        pre-existing coverage MUST survive the combine."""
        canary = tmp_path / "canary.py"
        canary.write_text("def f():\n    return 1\n", encoding="utf-8")
        env = _coverage_clean_env()

        subprocess.run(
            ["coverage", "run", "--branch", str(canary.name)],
            cwd=tmp_path,
            env={**env, "PYTHONPATH": str(tmp_path)},
            check=False,
            capture_output=True,
            text=True,
        )
        driver = tmp_path / "drive.py"
        driver.write_text("import canary\nassert canary.f() == 1\n", encoding="utf-8")
        subprocess.run(
            ["coverage", "run", "--branch", str(driver.name)],
            cwd=tmp_path,
            env={**env, "PYTHONPATH": str(tmp_path)},
            check=True,
            capture_output=True,
            text=True,
        )

        other = tmp_path / "other.py"
        other.write_text("def g():\n    return 2\n", encoding="utf-8")
        subprocess.run(
            [
                "coverage",
                "run",
                "--branch",
                "--parallel-mode",
                str(other.name),
            ],
            cwd=tmp_path,
            env={**env, "PYTHONPATH": str(tmp_path)},
            check=False,
            capture_output=True,
            text=True,
        )

        # WITH --append (the Makefile's fixed shape): the base file's
        # real canary data survives.
        subprocess.run(
            ["coverage", "combine", "--append"],
            cwd=tmp_path,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        post_combine = subprocess.run(
            ["coverage", "report", str(canary.name)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
        )
        assert "100%" in post_combine.stdout, post_combine.stdout + post_combine.stderr


# frob:ticket T-1433
class TestSerialRerunHasABoundedDeadline:
    """T-1433: two independent `make coverage` runs wedged forever in the
    serial (`-n 0`) rerun phase on a dead-holder futex -- a single-
    threaded pytest process, no children, blocked in `futex_wait_queue`
    with zero CPU seconds consumed. `addopts`' `--timeout=120` is a
    PER-TEST watchdog (pytest-timeout) that cannot catch a hang between
    tests or in teardown/lock machinery, exactly where this wedge sat.
    These tests lock the Makefile's own recipe text so both `-n 0` rerun
    invocations stay wrapped in a bounded `timeout`, and prove the wrapping
    mechanism itself actually bounds a wedged child rather than just
    looking like it does."""

    # frob:ticket T-1433
    # frob:tests \
    # tests/unit/test_makefile_coverage.py::TestSerialRerunHasABoundedDeadline.test_bot\
    # h_serial_reruns_are_wrapped_in_a_bounded_timeout
    def test_both_serial_reruns_are_wrapped_in_a_bounded_timeout(self):
        """Both the node-down-recovery and the failure-recovery `-n 0`
        reruns must be wrapped in a coreutils `timeout` invocation, and
        `COVERAGE_RERUN_DEADLINE` must be a real Makefile variable with a
        default -- a regression here silently reintroduces the T-1433
        indefinite-hang mechanism with no other visible symptom until the
        next multi-hour wedge."""
        assert "COVERAGE_RERUN_DEADLINE ?= " in _MAKEFILE, _MAKEFILE
        rerun_lines = [
            line
            for line in _MAKEFILE.splitlines()
            if "-n 0" in line and "pytest" in line
        ]
        assert len(rerun_lines) == 2, rerun_lines
        for line in rerun_lines:
            assert "timeout -k 30 $(COVERAGE_RERUN_DEADLINE)" in line, line

    # frob:ticket T-1433
    # frob:tests \
    # tests/unit/test_makefile_coverage.py::TestSerialRerunHasABoundedDeadline.test_tim\
    # eout_wrapping_kills_a_wedged_child_instead_of_hanging
    def test_timeout_wrapping_kills_a_wedged_child_instead_of_hanging(self):
        """Ground-truth reproduction of the FIX (not the bug): the exact
        `timeout -k 30 <deadline> env ...` shape used in the recipe,
        applied to a child that blocks forever (simulating the observed
        dead-holder futex_wait), exits 124 (coreutils `timeout`'s signal
        for "deadline exceeded") within a small bounded wall-clock window
        instead of hanging -- proving the wrapper is load-bearing, not
        decorative Makefile text."""
        result = subprocess.run(
            ["timeout", "-k", "1", "2", "python3", "-c", "import time; time.sleep(60)"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 124, (
            result.returncode,
            result.stdout,
            result.stderr,
        )


# frob:ticket T-1433
class TestXdistPhaseHasABoundedDeadlineAndStackdump:
    """T-1433 follow-up instrumentation: the xdist (parallel) phase had NO
    bound at all before this -- only the `-n 0` serial rerun did. Neither
    incident's own diagnostics pinned down which phase the dead-holder
    futex sat in, so leaving the xdist phase unbounded left half the
    recipe still able to hang indefinitely. This also locks in that
    `FROB_COVERAGE_STACKDUMP=1` (tests/conftest.py's SIGUSR1 handler) is
    set for every phase's pytest invocation -- the next wedge, in
    whichever phase, self-diagnoses via `.frob/stackdumps/*.txt` instead
    of leaving only a bare `wchan=futex_wait_queue` with no indication of
    which lock, in which function, on which process."""

    # frob:tests tests/unit/test_makefile_coverage.py::TestXdistPhaseHasABoundedDeadlineAndStackdump.test_xdist_phase_is_wrapped_in_a_bounded_timeout  # noqa: E501
    def test_xdist_phase_is_wrapped_in_a_bounded_timeout(self) -> None:
        """`COVERAGE_XDIST_DEADLINE` must be a real Makefile variable with
        a default, and the xdist-phase pytest invocation (`-n
        $(COVERAGE_WORKERS)`, distinct from the `-n 0` serial reruns) must
        be wrapped in `timeout -k 30 $(COVERAGE_XDIST_DEADLINE)` -- a
        regression here silently reopens the xdist half of T-1433's
        unbounded-hang mechanism."""
        assert "COVERAGE_XDIST_DEADLINE ?= " in _MAKEFILE, _MAKEFILE
        xdist_lines = [
            line
            for line in _MAKEFILE.splitlines()
            if "-n $(COVERAGE_WORKERS)" in line and "pytest" in line
        ]
        assert len(xdist_lines) == 1, xdist_lines
        assert "timeout -k 30 $(COVERAGE_XDIST_DEADLINE)" in xdist_lines[0], (
            xdist_lines[0]
        )

    # frob:tests tests/unit/test_makefile_coverage.py::TestXdistPhaseHasABoundedDeadlineAndStackdump.test_every_coverage_pytest_invocation_enables_the_stackdump_handler  # noqa: E501
    def test_every_coverage_pytest_invocation_enables_the_stackdump_handler(
        self,
    ) -> None:
        """Every `pytest` invocation in the `coverage:` recipe (the xdist
        phase and both `-n 0` serial reruns) must set
        `FROB_COVERAGE_STACKDUMP=1` so `tests/conftest.py`'s `SIGUSR1`
        handler is installed in every controller/worker process this
        recipe spawns -- a wedge in any one of them is now diagnosable."""
        assert "COVERAGE_STACKDUMP_ENV = FROB_COVERAGE_STACKDUMP=1" in _MAKEFILE, (
            _MAKEFILE
        )
        match = re.search(
            r"^coverage: \$\(STAMP\)\n(?:\t.*\n)*", _MAKEFILE, re.MULTILINE
        )
        assert match is not None, "coverage: recipe not found in Makefile"
        recipe = match.group(0)
        pytest_lines = [
            line
            for line in recipe.splitlines()
            if "uv run pytest" in line
            and "$(CURDIR)/.frob/coverage-subprocess.rc" in line
        ]
        assert len(pytest_lines) == 3, pytest_lines
        for line in pytest_lines:
            assert "$(COVERAGE_STACKDUMP_ENV)" in line, line


# frob:ticket T-1397
# frob:ticket T-1526
class TestCoverageFastUsesAbsoluteSubprocessRc:
    """T-1397's original defect (`coverage-fast` pointing
    `COVERAGE_PROCESS_START` at a relative-path `pyproject.toml`) can no
    longer reappear at all: T-1526 rewrote `coverage-fast:` into a thin
    wrapper delegating to `frob coverage` (T-1525) -- there is no more
    inline `COVERAGE_PROCESS_START=...`/`xargs` shell fragment in this
    target for that Loss-A shape to live in. This class (T-1397's own
    evidence binding) now asserts the STRONGER, simpler invariant that
    subsumes the original: the whole class of shell-side subprocess-rc
    bugs is structurally impossible here because `coverage-fast:` no
    longer runs `pytest`/`coverage` inline at all."""

    # frob:tests tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc.test_coverage_fast_never_points_at_pyproject_toml  # noqa: E501
    def test_coverage_fast_never_points_at_pyproject_toml(self) -> None:
        """The literal Loss-A shape T-1397 exists to prevent must never
        reappear in the live Makefile text."""
        assert "COVERAGE_PROCESS_START=$(CURDIR)/pyproject.toml" not in _MAKEFILE, (
            _MAKEFILE
        )

    # frob:tests tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc.test_coverage_fast_uses_the_shared_absolute_rc  # noqa: E501
    def test_coverage_fast_uses_the_shared_absolute_rc(self) -> None:
        """T-1526: `coverage-fast:`'s recipe is `make core` + `frob
        doctor` + `frob coverage` -- no inline pytest/coverage/xargs
        invocation, and so no `COVERAGE_PROCESS_START=...` reference of
        its own to get wrong; the coverage-subprocess.rc concern this
        test originally exercised is now entirely `frob coverage`'s
        (T-1525)/`native_coverage_refresh`'s (T-1516) own responsibility,
        not Makefile shell text."""
        match = re.search(
            r"^coverage-fast: \$\(STAMP\)\n(?:\t.*\n)*",
            _MAKEFILE,
            re.MULTILINE,
        )
        assert match is not None, "coverage-fast: recipe not found in Makefile"
        recipe = match.group(0)
        assert "uv run frob coverage" in recipe, recipe
        assert "xargs" not in recipe, recipe
        assert "uv run pytest" not in recipe, recipe
        assert "COVERAGE_PROCESS_START" not in recipe, recipe

    # frob:tests tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc.test_rc_file_target_is_shared_not_duplicated  # noqa: E501
    def test_rc_file_target_is_shared_not_duplicated(self) -> None:
        """Only ONE place in the Makefile generates
        `.frob/coverage-subprocess.rc` now -- `coverage:`'s own file
        target; `coverage-fast:` no longer embeds a second copy (T-1526:
        it has no inline subprocess invocation left to need one)."""
        assert _MAKEFILE.count("> .frob/coverage-subprocess.rc") == 1, _MAKEFILE

    # frob:tests tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc.test_coverage_fast_still_rebuilds_natives_first  # noqa: E501
    def test_coverage_fast_still_rebuilds_natives_first(self) -> None:
        """The natives-clobber guard (T-0538: `make core && uv run frob
        doctor`) this target has always needed before any pytest
        collection survives the T-1526 rewrite unchanged."""
        match = re.search(
            r"^coverage-fast: \$\(STAMP\)\n(?:\t.*\n)*",
            _MAKEFILE,
            re.MULTILINE,
        )
        assert match is not None
        recipe = match.group(0)
        assert "$(MAKE) core" in recipe, recipe
        assert "uv run frob doctor" in recipe, recipe


# frob:ticket T-1235
class TestPreviouslyZeroModulesNowAttributeInTheCommittedLock:
    """T-1235's acceptance [2]: previously-exercised-but-zero symbols
    (excludes.py, doctor.py, serve/, __main__.py) report real coverage in
    a corrected full run, and the TEST005 count reflects it.

    This ticket's own scope has no direct pytest surface for "the next
    full `make coverage` run" -- that run is a coordinator-only step
    (docs/guides/agent-playbook.md section 6b), and its raw `coverage.xml`
    does not survive past the run that produced it (section 6d). The
    committed `frob-coverage.lock.json` (`write_coverage_lock`,
    `frob.gates._coverage`) is this repo's own durable, attestable summary
    of that same run -- reading it directly, rather than re-deriving a
    fresh (and necessarily locally-scoped, per section 6c) coverage.xml
    from this worktree, is the only way to verify this acceptance
    criterion without forcing an unverifiable claim.
    """

    #: T-1235's own named acceptance-criterion module groups.
    _NAMED_MODULES = (
        "src/frob/excludes.py",
        "src/frob/doctor.py",
        "src/frob/serve/_socketd.py",
        "src/frob/__main__.py",
    )

    def _load_committed_lock(self) -> dict[str, float]:
        """`module_line` mapping read from the repo-root committed lock."""
        lock_path = _REPO_ROOT / "frob-coverage.lock.json"
        data = json.loads(lock_path.read_text())
        return data["module_line"]

    def test_named_module_groups_are_nonzero_in_the_committed_lock(self) -> None:
        """excludes.py/doctor.py/serve/_socketd.py/__main__.py must not be 0.0%.

        Measured directly against `frob-coverage.lock.json` as committed
        on `main` (commit `5ffa0159`, "chore(coverage): stamp lock from
        green suite run", 2026-08-03 -- after both this ticket's own
        subprocess-rc fix and T-1433's xdist-wedge fix landed): every
        named module reads well above 0.0% (measured: excludes.py 100.0%,
        doctor.py 93.8%, serve/_socketd.py 90.7%, __main__.py 89.5%),
        versus the 0.0% each read before T-1235's fix (T-0969's 2026-07-29
        diagnosis).
        """
        module_line = self._load_committed_lock()
        for module in self._NAMED_MODULES:
            assert module in module_line, f"{module} missing from committed lock"
            assert module_line[module] > 0.0, (
                f"{module} regressed to the pre-T-1235 zero-coverage "
                f"attribution failure (module_line[{module}] = "
                f"{module_line[module]})"
            )


# frob:ticket T-1469
class TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor:
    """T-1469: `coverage:`/`coverage-fast:` must run `frob ticket
    reconcile --apply` before `frob doctor` -- a stale IN_PROGRESS
    ticket hold with no live lease (`scan_stale_ticket_leases`, T-1131)
    used to make the doctor precondition abort the whole recipe before
    pytest ever ran; `reconcile --apply` auto-requeues exactly that shape
    (logging which ticket(s) it requeued) and is a no-op otherwise, so
    the precondition can no longer abort on THIS specific, mechanically
    healable condition while every other doctor-checked condition
    (missing natives, corrupt derived state, a live land.lock, venv shim
    drift) still fails the recipe hard."""

    # frob:tests tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor.test_coverage_reconciles_before_doctor  # noqa: E501
    def test_coverage_reconciles_before_doctor(self) -> None:
        match = re.search(
            r"^coverage: \$\(STAMP\)\n(?:\t.*\n)*", _MAKEFILE, re.MULTILINE
        )
        assert match is not None, "coverage: recipe not found in Makefile"
        recipe = match.group(0)
        reconcile_idx = recipe.index("uv run frob ticket reconcile --apply")
        doctor_idx = recipe.index("uv run frob doctor")
        assert reconcile_idx < doctor_idx, recipe

    # frob:tests tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor.test_coverage_fast_reconciles_before_doctor  # noqa: E501
    def test_coverage_fast_reconciles_before_doctor(self) -> None:
        match = re.search(
            r"^coverage-fast: \$\(STAMP\)\n(?:\t.*\n)*", _MAKEFILE, re.MULTILINE
        )
        assert match is not None, "coverage-fast: recipe not found in Makefile"
        recipe = match.group(0)
        reconcile_idx = recipe.index("uv run frob ticket reconcile --apply")
        doctor_idx = recipe.index("uv run frob doctor")
        assert reconcile_idx < doctor_idx, recipe
