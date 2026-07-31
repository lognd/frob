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
        r"^\tuv run coverage combine; \\\n(?:\t.*\\\n)*\texit \$\$status$",
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
    env = {"PATH": f"{stub_bin}:/usr/bin:/bin", **env_extra}
    # `status` is set by the pytest-run block earlier in the real recipe
    # (not part of the sliced fragment); seed it as "green suite already
    # passed" (status=0), the scenario both tests below exercise.
    script = "status=0\n" + _recipe_tail()
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
