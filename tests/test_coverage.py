"""Tests for T-0484's touched-set coverage helper
(frob.testing._incremental_coverage.python_coverage_targets) and T-0538's
natives-clobber guard on the `make coverage`/`make coverage-fast` targets."""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
import time
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
from typani import Err, Ok
from typani.unit import Unit

from frob.gates._models import CoverageData
from frob.graph import build_graph
from frob.testing import _coverage_refresh as _refresh_mod
from frob.testing import (
    fill_from_cache,
    load_file_cache,
    native_coverage_refresh,
    python_coverage_targets,
    update_file_cache,
)

if TYPE_CHECKING:
    from frob.graph import GraphSnapshot

#: ty: GraphSnapshot-typed sentinel for refresh paths where the snapshot is
#: unused (the monkeypatched _run never touches it).
_FAKE_SNAPSHOT = cast("GraphSnapshot", object())

#: T-0538: repo root, resolved the same way every other Makefile-adjacent
#: test in this repo would -- two levels up from this test file
#: (tests/test_coverage.py -> repo root).
_REPO_ROOT = Path(__file__).resolve().parent.parent


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))
    return path


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "main")
    # T-1006: a real repo always gitignores .frob/ (frob's own scratch
    # state); without this a fixture with no .gitignore lets frob's own
    # derived.lock/cache.db writes (produced merely by calling build_graph
    # during the test itself) show up as untouched-by-user files in
    # `git ls-files --others`, which python_coverage_targets then treats
    # as a genuine unknown-language touched file and falls back to a
    # suite-wide '*' selection -- not a real product bug, just an
    # under-configured fixture repo.
    (root / ".gitignore").write_text(".frob/\n", encoding="utf-8")


def _commit(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


class TestPythonCoverageTargets:
    def test_touched_source_selects_test(self, tmp_path: Path) -> None:
        """T-0484: a source file changed since `base` selects the test bound
        to it via `frob:tests`, mirroring `frob test --base`'s own touched-
        set selection (the shared, already-trusted algorithm) -- the
        touched-set coverage recipe's whole premise."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/foo.py",
            """
            def widget() -> int:
                return 1
            """,
        )
        _write(
            tmp_path,
            "tests/test_foo.py",
            """
            def test_widget() -> None:
                # frob:tests src/foo.py::widget
                pass
            """,
        )
        _commit(tmp_path, "base")

        _write(
            tmp_path,
            "src/foo.py",
            """
            def widget() -> int:
                return 2
            """,
        )
        snapshot = build_graph(tmp_path, tmp_path.parent / "cache.db").danger_ok
        targets = python_coverage_targets(tmp_path, snapshot, "main")
        assert any("test_widget" in t for t in targets)

    def test_nothing_touched_returns_empty(self, tmp_path: Path) -> None:
        """T-0484: an unchanged tree (no diff against `base`) selects nothing
        -- callers treat this as "no incremental re-measurement needed," not
        an error."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/foo.py",
            """
            def widget() -> int:
                return 1
            """,
        )
        _write(
            tmp_path,
            "tests/test_foo.py",
            """
            def test_widget() -> None:
                # frob:tests src/foo.py::widget
                pass
            """,
        )
        _commit(tmp_path, "base")
        snapshot = build_graph(tmp_path, tmp_path.parent / "cache.db").danger_ok
        targets = python_coverage_targets(tmp_path, snapshot, "main")
        assert targets == ()

    def test_bad_base_ref_returns_empty(self, tmp_path: Path) -> None:
        """T-0484: a `working_diff` failure (e.g. an unknown base ref) degrades
        to an empty result rather than propagating an exception -- the
        Makefile recipe calling this must be able to fall back to a full
        `make coverage` run instead of crashing."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/foo.py",
            """
            def widget() -> int:
                return 1
            """,
        )
        _commit(tmp_path, "base")
        snapshot = build_graph(tmp_path, tmp_path.parent / "cache.db").danger_ok
        targets = python_coverage_targets(tmp_path, snapshot, "no-such-ref")
        assert targets == ()


class TestCoverageTargetNativesGuard:
    """T-0538: `make coverage`/`make coverage-fast` both depend on
    `$(STAMP)` (`uv sync`), which silently removes the editable
    `strata_core`/`frob_core` natives `make core` installed -- neither is a
    declared dependency `uv sync` knows to preserve. This dry-runs the real
    Makefile (`make -n`, which never executes a single recipe line) and
    asserts the restore-then-verify guard (`make core` then `frob doctor`)
    appears BEFORE the pytest invocation in both targets' expanded recipe,
    so a regression that reorders or drops the guard fails this test
    without ever running the (slow, `make coverage`-forbidden per the
    playbook's 6b) real recipe."""

    def _dry_run(self, target: str) -> str:
        """`make -n <target>` output: the exact shell commands `make` WOULD
        run, in order, with none of them actually executed -- safe to call
        from a test."""
        result = subprocess.run(
            ["make", "-n", target],
            cwd=_REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout

    def _assert_guard_precedes_pytest(self, output: str) -> None:
        """`make core` and `frob doctor` must both appear, in that relative
        order, strictly before the first `pytest --cov` invocation -- the
        exact ordering that fails loudly on a missing native instead of
        letting pytest collection blow up mid-suite (the T-0538 incident)."""
        core_idx = output.index("make core")
        doctor_idx = output.index("frob doctor")
        pytest_idx = output.index("pytest --cov")
        assert core_idx < doctor_idx < pytest_idx, (
            f"expected 'make core' < 'frob doctor' < 'pytest --cov', "
            f"got indices {core_idx}, {doctor_idx}, {pytest_idx} in:\n{output}"
        )

    # frob:ticket T-1595
    def _assert_guard_precedes_coverage_cli(self, output: str) -> None:
        """`make core` and `frob doctor` must both appear, in that relative
        order, strictly before the `frob coverage .` invocation -- the same
        T-0538 guard shape as `_assert_guard_precedes_pytest`, but for the
        `coverage-fast` target specifically (T-1595): T-1525 moved
        `coverage-fast`'s own coverage orchestration out of a literal
        `pytest --cov` Makefile line and into the frob-native `frob
        coverage` CLI verb (`src/frob/app/coverage_runner.py`), so
        `pytest --cov` no longer appears anywhere in this target's dry-run
        expansion at all -- asserting for it here was stale, not a real
        regression (`frob coverage` still exercises pytest internally, via
        `run_coverage_wait`/`native_coverage_refresh`, just not as a
        Makefile-visible subprocess line)."""
        core_idx = output.index("make core")
        doctor_idx = output.index("frob doctor")
        coverage_idx = output.index("frob coverage .")
        assert core_idx < doctor_idx < coverage_idx, (
            f"expected 'make core' < 'frob doctor' < 'frob coverage .', "
            f"got indices {core_idx}, {doctor_idx}, {coverage_idx} in:\n{output}"
        )

    def test_coverage_target_restores_and_verifies_natives_before_pytest(
        self,
    ) -> None:
        """`make coverage`'s dry-run recipe restores natives (`make core`)
        and verifies them (`frob doctor`) before the coverage pytest run."""
        self._assert_guard_precedes_pytest(self._dry_run("coverage"))

    def test_coverage_fast_incremental_branch_restores_and_verifies_natives(
        self,
    ) -> None:
        """`make coverage-fast`'s incremental branch (the one that does NOT
        fall back to `make coverage`) is subject to the exact same
        `$(STAMP)`/`uv sync` clobber hazard, since it also depends on
        `$(STAMP)` -- this asserts its own `make core && frob doctor`
        guard is present in the dry-run output before its own coverage
        invocation. T-1595: that invocation is `frob coverage .` (T-1525
        moved this target off a literal `pytest --cov` Makefile line), not
        `pytest --cov` -- see `_assert_guard_precedes_coverage_cli`."""
        self._assert_guard_precedes_coverage_cli(self._dry_run("coverage-fast"))


class TestCoverageTargetFlakeTolerance:
    """T-1180: `make coverage` must not let a load-sensitive parallel-run
    flake halt the recipe before combine/xml/stamp -- a failed first pass
    gets exactly one serial (non-xdist) rerun of just the failed tests,
    appended onto the same coverage data, and only a test still failing
    after that rerun fails the target. Asserted against the real dry-run
    recipe text (`make -n coverage`, nothing executed) so a regression that
    drops the rerun, or lets the first pass's exit code halt the recipe
    early, fails this test without ever running the (slow, playbook-6b-
    forbidden-for-a-sub-agent) real target."""

    def _dry_run(self) -> str:
        result = subprocess.run(
            ["make", "-n", "coverage"],
            cwd=_REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout

    def test_first_pass_failure_does_not_abort_the_recipe(self) -> None:
        """The first `pytest --cov` invocation's exit status is captured
        into a shell variable rather than left to `make`'s default
        stop-on-nonzero behavior -- `; \\` continuation into `status=$?`
        immediately after it, not a bare recipe line of its own."""
        output = self._dry_run()
        first_pytest_idx = output.index("pytest --cov")
        # the line immediately following the first pytest invocation must
        # capture its exit status rather than being a fresh `make` recipe
        # line (which would abort the whole recipe on nonzero exit).
        tail = output[first_pytest_idx:]
        assert "status=$?" in tail

    def test_rerun_is_serial_and_scoped_to_last_failed(self) -> None:
        """The rerun disables xdist parallelism (`-n 0` -- NOT `-p
        no:xdist`, which pytest rejects here: `[tool.pytest.ini_options]
        addopts` bakes in `-n auto`, and unloading the xdist plugin
        entirely while `-n` is still in `addopts` makes `-n` an
        unrecognized argument; `-n 0` overrides the count instead, xdist
        plugin still loaded, worker count zero) and scopes to just the
        failed tests (`--last-failed`), appending onto the same coverage
        data (`--cov-append`) -- never a second full-suite parallel run."""
        output = self._dry_run()
        assert "-n 0" in output
        assert "--last-failed" in output
        assert "--cov-append" in output

    def test_combine_xml_stamp_run_unconditionally_after_the_rerun(self) -> None:
        """`coverage combine`, `coverage xml`, and `frob check
        --stamp-coverage` all appear strictly AFTER the serial rerun
        block, on lines that are not gated behind the captured `status`
        (i.e. always reached, not just on success) -- the parallel-run
        failure must never block them."""
        output = self._dry_run()
        rerun_idx = output.index("--last-failed")
        combine_idx = output.index("coverage combine")
        xml_idx = output.index("coverage xml")
        stamp_idx = output.index("frob check --stamp-coverage")
        assert rerun_idx < combine_idx < xml_idx < stamp_idx

    def test_target_exit_reflects_final_status_not_always_zero(self) -> None:
        """The recipe's own shell block ends with `exit $status` -- a test
        still failing after the serial rerun must fail `make coverage`
        itself, not be silently swallowed by combine/xml/stamp's own zero
        exit codes."""
        output = self._dry_run()
        assert "exit $status" in output


# frob:ticket T-1517
class TestCoverageFileCache:
    """T-1517: `.frob/coverage-file-cache.json` keeps an unchanged file's
    coverage percentage available across separate, narrower touched-set
    runs without any test re-execution -- these tests exercise the
    load/fill/update trio directly against `CoverageData`, no real
    `coverage.xml` or pytest run involved."""

    # frob:ticket T-1517
    def test_load_missing_returns_empty(self, tmp_path: Path) -> None:
        """No cache file on disk is a cold start, not an error."""
        assert load_file_cache(tmp_path) == {}

    # frob:ticket T-1517
    def test_fill_from_cache_backfills_unchanged_file(self, tmp_path: Path) -> None:
        """A file absent from this run's `module_line` but present in the
        cache with a MATCHING content hash is backfilled at its last
        measured percentage -- the "unchanged file's coverage is never
        recomputed" contract."""
        data = CoverageData(source_sha="abc", module_line={})
        cache: dict[str, dict[str, object]] = {
            "src/foo.py": {"content_hash": "hash-a", "line_pct": 87.5}
        }
        merged = fill_from_cache(
            data, file_hashes={"src/foo.py": "hash-a"}, cache=cache
        )
        assert merged.module_line["src/foo.py"] == 87.5

    # frob:ticket T-1517
    def test_fill_from_cache_ignores_stale_hash(self, tmp_path: Path) -> None:
        """A file whose current content hash no longer matches the cached
        one is left unbackfilled -- a real miss, not something a stale
        cache entry should paper over."""
        data = CoverageData(source_sha="abc", module_line={})
        cache: dict[str, dict[str, object]] = {
            "src/foo.py": {"content_hash": "hash-old", "line_pct": 87.5}
        }
        merged = fill_from_cache(
            data, file_hashes={"src/foo.py": "hash-new"}, cache=cache
        )
        assert "src/foo.py" not in merged.module_line

    # frob:ticket T-1517
    def test_fill_from_cache_never_overwrites_fresh_data(self, tmp_path: Path) -> None:
        """A file this run DID measure keeps its fresh value even when the
        cache disagrees -- fresh data always wins."""
        data = CoverageData(source_sha="abc", module_line={"src/foo.py": 50.0})
        cache: dict[str, dict[str, object]] = {
            "src/foo.py": {"content_hash": "hash-a", "line_pct": 87.5}
        }
        merged = fill_from_cache(
            data, file_hashes={"src/foo.py": "hash-a"}, cache=cache
        )
        assert merged.module_line["src/foo.py"] == 50.0

    # frob:ticket T-1517
    def test_update_file_cache_persists_measured_files(self, tmp_path: Path) -> None:
        """`update_file_cache` writes every measured file's `(content_hash,
        line_pct)` and `load_file_cache` reads it back."""
        data = CoverageData(source_sha="abc", module_line={"src/foo.py": 42.0})
        update_file_cache(tmp_path, data, file_hashes={"src/foo.py": "hash-a"})
        cache = load_file_cache(tmp_path)
        assert cache["src/foo.py"]["content_hash"] == "hash-a"
        assert cache["src/foo.py"]["line_pct"] == 42.0

    # frob:ticket T-1517
    def test_update_file_cache_roundtrips_through_fill_from_cache(
        self, tmp_path: Path
    ) -> None:
        """A file measured on run 1 and untouched (same content hash) on run
        2's narrower coverage.xml is backfilled by `fill_from_cache` using
        exactly what `update_file_cache` persisted on run 1 -- the whole
        incremental round trip, no real pytest/coverage involved."""
        run1 = CoverageData(source_sha="abc", module_line={"src/foo.py": 66.0})
        update_file_cache(tmp_path, run1, file_hashes={"src/foo.py": "hash-a"})

        # run 2: coverage.xml only measured a DIFFERENT file this time.
        run2 = CoverageData(source_sha="def", module_line={"src/bar.py": 10.0})
        cache = load_file_cache(tmp_path)
        merged = fill_from_cache(
            run2,
            file_hashes={"src/foo.py": "hash-a", "src/bar.py": "hash-b"},
            cache=cache,
        )
        assert merged.module_line["src/foo.py"] == 66.0
        assert merged.module_line["src/bar.py"] == 10.0


# frob:ticket T-1672
class TestComputeWorkerCount:
    """T-1672 item 1: `_compute_worker_count`'s memory-aware xdist pool
    sizing, and `_pytest_argv`'s `-n` override wiring."""

    def test_explicit_zero_opts_out_entirely(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_coverage.py::TestComputeWorkerCount.test_explicit_zero_opts_out_entirely  # noqa: E501
        monkeypatch.setenv(_refresh_mod._MAX_WORKERS_ENV, "0")
        assert _refresh_mod._compute_worker_count() is None

    def test_explicit_positive_override_wins_over_memory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_coverage.py::TestComputeWorkerCount.test_explicit_positive_override_wins_over_memory  # noqa: E501
        monkeypatch.setenv(_refresh_mod._MAX_WORKERS_ENV, "3")
        monkeypatch.setattr(_refresh_mod, "_available_memory_mb", lambda: 1)
        assert _refresh_mod._compute_worker_count() == 3

    def test_malformed_override_falls_back_to_memory_sizing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_coverage.py::TestComputeWorkerCount.test_malformed_override_falls_back_to_memory_sizing  # noqa: E501
        monkeypatch.setenv(_refresh_mod._MAX_WORKERS_ENV, "not-a-number")
        monkeypatch.setattr(_refresh_mod, "_available_memory_mb", lambda: 100000)
        monkeypatch.delenv(_refresh_mod._PER_WORKER_MEM_ENV, raising=False)
        monkeypatch.setattr(_refresh_mod.os, "cpu_count", lambda: 16)
        # 100000MB / 1536MB(default) ~= 65 workers, capped at cpu_count=16.
        assert _refresh_mod._compute_worker_count() == 16

    def test_memory_is_the_binding_constraint(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_coverage.py::TestComputeWorkerCount.test_memory_is_the_binding_constraint  # noqa: E501
        """The field incident's exact shape: 16 cores, not enough memory
        for 16 workers -- the computed count must be memory-bound, not
        core-bound."""
        monkeypatch.delenv(_refresh_mod._MAX_WORKERS_ENV, raising=False)
        monkeypatch.setattr(_refresh_mod, "_available_memory_mb", lambda: 4096)
        monkeypatch.setenv(_refresh_mod._PER_WORKER_MEM_ENV, "1536")
        monkeypatch.setattr(_refresh_mod.os, "cpu_count", lambda: 16)
        # 4096MB / 1536MB ~= 2 workers -- far below the 16 cores available.
        assert _refresh_mod._compute_worker_count() == 2

    def test_unmeasurable_memory_returns_none_not_a_guess(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_coverage.py::TestComputeWorkerCount.test_unmeasurable_memory_returns_none_not_a_guess  # noqa: E501
        """Non-Linux (or any measurement failure): `None` (keep `-n auto`
        untouched), never a fabricated number -- a wrong guess here is
        exactly the class of silent misbehavior this ticket is about."""
        monkeypatch.delenv(_refresh_mod._MAX_WORKERS_ENV, raising=False)
        monkeypatch.setattr(_refresh_mod, "_available_memory_mb", lambda: None)
        assert _refresh_mod._compute_worker_count() is None

    def test_available_memory_mb_parses_real_proc_meminfo_shape(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_coverage.py::TestComputeWorkerCount.test_available_memory_mb_parses_real_proc_meminfo_shape  # noqa: E501
        fake_meminfo = tmp_path / "meminfo"
        fake_meminfo.write_text(
            "MemTotal:       16384000 kB\n"
            "MemFree:         1024000 kB\n"
            "MemAvailable:    8192000 kB\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            _refresh_mod,
            "Path",
            lambda p: fake_meminfo if p == "/proc/meminfo" else Path(p),
        )  # noqa: E501
        assert _refresh_mod._available_memory_mb() == 8192000 // 1024

    def test_available_memory_mb_missing_file_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_coverage.py::TestComputeWorkerCount.test_available_memory_mb_missing_file_returns_none  # noqa: E501
        missing = tmp_path / "does-not-exist"
        monkeypatch.setattr(
            _refresh_mod, "Path", lambda p: missing if p == "/proc/meminfo" else Path(p)
        )  # noqa: E501
        assert _refresh_mod._available_memory_mb() is None

    def test_pytest_argv_appends_computed_n_flag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_coverage.py::TestComputeWorkerCount.test_pytest_argv_appends_computed_n_flag  # noqa: E501
        """`-n <computed>` must land AFTER `pytest`'s own base args so it
        overrides `addopts`'s `-n auto` (last `-n` on the command line
        wins for xdist's plain argparse `store` option)."""
        monkeypatch.setattr(_refresh_mod, "_compute_worker_count", lambda: 4)
        argv = _refresh_mod._pytest_argv(
            targets=(), cov_target="src/frob", append=False
        )
        assert "-n" in argv
        assert argv[argv.index("-n") + 1] == "4"

    def test_pytest_argv_omits_n_flag_when_unmeasurable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_coverage.py::TestComputeWorkerCount.test_pytest_argv_omits_n_flag_when_unmeasurable  # noqa: E501
        monkeypatch.setattr(_refresh_mod, "_compute_worker_count", lambda: None)
        argv = _refresh_mod._pytest_argv(
            targets=(), cov_target="src/frob", append=False
        )
        assert "-n" not in argv


# frob:ticket T-1516
class TestNativeCoverageRefresh:
    """T-1516: `native_coverage_refresh`'s branching logic (full/cold-start
    vs. incremental vs. nothing-to-do), exercised with `_run` and
    `frob.gates._coverage.load_stamp`/`stamp_coverage` monkeypatched --
    never spawns a real `pytest`/`coverage` subprocess."""

    # frob:ticket T-1516
    def _patch_stamp(
        self, monkeypatch: pytest.MonkeyPatch, *, stamp: dict | None, ok: bool = True
    ) -> list[object]:
        """Monkeypatch the deferred `frob.gates._coverage` import target
        (imported fresh inside `native_coverage_refresh` on every call, so
        patching the real module attribute is enough) and return the list
        `stamp_coverage` calls get appended to."""
        import frob.gates._coverage as coverage_mod

        calls: list[object] = []
        monkeypatch.setattr(coverage_mod, "load_stamp", lambda _root: stamp)

        def _fake_stamp(root, snapshot):  # noqa: ANN001, ARG001
            calls.append((root, snapshot))
            return Ok(Unit()) if ok else Err("boom")

        monkeypatch.setattr(coverage_mod, "stamp_coverage", _fake_stamp)
        return calls

    # frob:ticket T-1516
    def test_full_run_when_no_stamp_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No stamp -> cold start -> a full (untargeted, non-append) pytest
        run, then `coverage xml -i`, then `stamp_coverage`."""
        calls: list[list[str]] = []

        def _fake_spawn(argv, *, cwd):  # noqa: ANN001, ARG001
            calls.append(list(argv))
            return Ok(subprocess.CompletedProcess(argv, 0))

        monkeypatch.setattr(_refresh_mod, "_spawn", _fake_spawn)
        stamp_calls = self._patch_stamp(monkeypatch, stamp=None)

        result = native_coverage_refresh(tmp_path, _FAKE_SNAPSHOT)
        assert result.is_ok
        assert calls[0][0] == "pytest"
        assert "--cov-append" not in calls[0]
        assert calls[1] == ["coverage", "xml", "-i"]
        assert len(stamp_calls) == 1

    # frob:ticket T-1516
    def test_incremental_run_uses_touched_set_targets(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A stamp exists (not cold start) and the touched-set selects a
        target -- the pytest run is `--cov-append`-restricted to it."""
        calls: list[list[str]] = []

        def _fake_spawn(argv, *, cwd):  # noqa: ANN001, ARG001
            calls.append(list(argv))
            return Ok(subprocess.CompletedProcess(argv, 0))

        monkeypatch.setattr(_refresh_mod, "_spawn", _fake_spawn)
        monkeypatch.setattr(
            _refresh_mod,
            "python_coverage_targets",
            lambda *a, **k: ("tests/test_foo.py::test_widget",),  # noqa: ARG005
        )
        self._patch_stamp(monkeypatch, stamp={"source_sha": "x", "file_hashes": {}})

        result = native_coverage_refresh(tmp_path, _FAKE_SNAPSHOT)
        assert result.is_ok
        assert calls[0][0] == "pytest"
        assert "--cov-append" in calls[0]
        assert "tests/test_foo.py::test_widget" in calls[0]

    # frob:ticket T-1516
    def test_nothing_touched_only_restamps(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A stamp exists, nothing touched selects a python test, AND
        `coverage.xml` already exists on disk -- no pytest/coverage
        subprocess is spawned at all, only `stamp_coverage` runs."""
        (tmp_path / "coverage.xml").write_text("<coverage/>", encoding="utf-8")
        calls: list[list[str]] = []

        def _fake_spawn(argv, *, cwd):  # noqa: ANN001, ARG001
            calls.append(list(argv))
            return Ok(subprocess.CompletedProcess(argv, 0))

        monkeypatch.setattr(_refresh_mod, "_spawn", _fake_spawn)
        monkeypatch.setattr(
            _refresh_mod,
            "python_coverage_targets",
            lambda *a, **k: (),  # noqa: ARG005
        )
        stamp_calls = self._patch_stamp(
            monkeypatch, stamp={"source_sha": "x", "file_hashes": {}}
        )

        result = native_coverage_refresh(tmp_path, _FAKE_SNAPSHOT)
        assert result.is_ok
        assert calls == []
        assert len(stamp_calls) == 1

    # frob:ticket T-1516
    def test_red_suite_keeps_coverage_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-1676 REGRESSION LOCK -- inverted from the original
        `test_pytest_failure_is_err`, which asserted the behavior this
        ticket removed.

        A red suite must NOT discard the run: `coverage xml` still runs,
        `stamp_coverage` still runs, the refresh still succeeds, and the
        artifact is marked degraded. The incident this locks out cost a
        7m32s full run in which 8622 of 8654 tests passed and no
        coverage.xml was produced at all."""
        calls: list[list[str]] = []

        def _fake_spawn(argv, *, cwd):  # noqa: ANN001, ARG001
            calls.append(list(argv))
            code = 1 if argv[0] == "pytest" else 0
            return Ok(subprocess.CompletedProcess(argv, code))

        monkeypatch.setattr(_refresh_mod, "_spawn", _fake_spawn)
        stamp_calls = self._patch_stamp(monkeypatch, stamp=None)

        result = native_coverage_refresh(tmp_path, _FAKE_SNAPSHOT)
        assert result.is_ok
        assert calls[0][0] == "pytest"
        assert ["coverage", "xml", "-i"] in calls
        assert len(stamp_calls) == 1

        record = json.loads(
            (tmp_path / _refresh_mod._RUN_PROVENANCE_REL).read_text(encoding="utf-8")
        )
        assert record["degraded"] is True
        assert record["pytest_exit_code"] == 1

    # frob:ticket T-1676
    def test_refused_spawn_is_err(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The one case that still aborts: pytest never ran at all
        (`FROB_DISABLE_EXEC=1`), so there is genuinely no measurement to
        keep and nothing to stamp."""
        # frob:ticket T-1677
        # `_spawn` now returns `_SpawnError` (not a bare `Unit`) so
        # `_pytest_outcome`'s caller can distinguish a refused spawn from
        # either watchdog deadline.
        monkeypatch.setattr(
            _refresh_mod,
            "_spawn",
            lambda *a, **k: Err(_refresh_mod._SpawnError.Refused),  # noqa: ARG005
        )
        stamp_calls = self._patch_stamp(monkeypatch, stamp=None)

        result = native_coverage_refresh(tmp_path, _FAKE_SNAPSHOT)
        assert result.is_err
        assert result.danger_err == _refresh_mod.CoverageRefreshError.PytestRefused
        assert stamp_calls == []

    # frob:ticket T-1676
    def test_green_suite_records_not_degraded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A green run overwrites the provenance record rather than leaving
        a previous run's `degraded` note in place to be misread as a
        property of the current artifact."""
        stale = tmp_path / _refresh_mod._RUN_PROVENANCE_REL
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text(
            '{"degraded": true, "pytest_exit_code": 1}\n', encoding="utf-8"
        )

        monkeypatch.setattr(
            _refresh_mod,
            "_spawn",
            lambda argv, **k: Ok(subprocess.CompletedProcess(argv, 0)),  # noqa: ARG005
        )
        self._patch_stamp(monkeypatch, stamp=None)

        result = native_coverage_refresh(tmp_path, _FAKE_SNAPSHOT)
        assert result.is_ok
        record = json.loads(stale.read_text(encoding="utf-8"))
        assert record["degraded"] is False
        assert record["pytest_exit_code"] == 0


# frob:ticket T-1677
class TestSpawnWithWatchdog:
    """T-1677: `_spawn_with_watchdog`'s wall-clock deadline, no-progress
    deadline, and process-group teardown, exercised against REAL spawned
    subprocesses (small shell one-liners) -- this is the layer that
    replaces a blocking, un-timed-out `subprocess.run`/
    `guarded_subprocess_run` call, so a mock would not actually prove the
    kill/no-hang behavior the ticket is about."""

    def test_normal_completion_returns_exit_code_and_output(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_coverage.py::TestSpawnWithWatchdog.test_normal_completion_returns_exit_code_and_output  # noqa: E501
        config = _refresh_mod._WatchdogConfig(wall_clock_s=10.0, no_progress_s=10.0)
        result = _refresh_mod._spawn_with_watchdog(
            ["python3", "-c", "print('hello')"], cwd=tmp_path, config=config
        )
        assert result.is_ok
        proc = result.danger_ok
        assert proc.returncode == 0
        assert "hello" in proc.stdout

    def test_nonzero_exit_still_returns_ok_with_output(self, tmp_path: Path) -> None:
        # frob:tests tests/test_coverage.py::TestSpawnWithWatchdog.test_nonzero_exit_still_returns_ok_with_output  # noqa: E501
        """A subprocess that RUNS to completion and exits non-zero is not
        a watchdog concern at all -- classifying that exit is the
        caller's job (`_pytest_outcome`), same as before this ticket."""
        config = _refresh_mod._WatchdogConfig(wall_clock_s=10.0, no_progress_s=10.0)
        result = _refresh_mod._spawn_with_watchdog(
            ["python3", "-c", "import sys; sys.exit(7)"], cwd=tmp_path, config=config
        )
        assert result.is_ok
        assert result.danger_ok.returncode == 7

    def test_wall_clock_deadline_kills_and_reports(self, tmp_path: Path) -> None:
        # frob:tests tests/test_coverage.py::TestSpawnWithWatchdog.test_wall_clock_deadline_kills_and_reports  # noqa: E501
        """A process that keeps producing output (so no-progress never
        trips) but never finishes must still be killed once the
        wall-clock deadline elapses -- this is the 2026-08-06 field
        incident's exact shape (alive, "progressing", never ending)."""
        config = _refresh_mod._WatchdogConfig(
            wall_clock_s=0.5, no_progress_s=60.0, poll_interval_s=0.1
        )
        script = (
            "import sys, time\n"
            "for _ in range(1000):\n"
            "    print('tick', flush=True)\n"
            "    time.sleep(0.05)\n"
        )
        start = time.monotonic()
        result = _refresh_mod._spawn_with_watchdog(
            ["python3", "-c", script], cwd=tmp_path, config=config
        )
        elapsed = time.monotonic() - start
        assert result.is_err
        assert result.danger_err == _refresh_mod._WatchdogAbortReason.WallClockExceeded
        # Killed close to the deadline, not left running (generous bound
        # for CI/WSL scheduling jitter -- the field incident was off by
        # HOURS, not fractions of a second).
        assert elapsed < 5.0

    def test_no_progress_deadline_kills_a_silent_hang(self, tmp_path: Path) -> None:
        # frob:tests tests/test_coverage.py::TestSpawnWithWatchdog.test_no_progress_deadline_kills_a_silent_hang  # noqa: E501
        """A process that prints once and then goes silent (the exact
        futex_wait_queue shape from the field incident) trips the
        no-progress deadline long before any generous wall-clock deadline
        would."""
        config = _refresh_mod._WatchdogConfig(
            wall_clock_s=60.0, no_progress_s=0.5, poll_interval_s=0.1
        )
        script = "print('starting', flush=True)\nimport time\ntime.sleep(30)\n"
        start = time.monotonic()
        result = _refresh_mod._spawn_with_watchdog(
            ["python3", "-c", script], cwd=tmp_path, config=config
        )
        elapsed = time.monotonic() - start
        assert result.is_err
        assert result.danger_err == _refresh_mod._WatchdogAbortReason.NoProgress
        assert elapsed < 5.0

    def test_killed_process_group_leaves_no_surviving_children(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_coverage.py::TestSpawnWithWatchdog.test_killed_process_group_leaves_no_surviving_children  # noqa: E501
        """T-1677 item 4 ("never leave zombies"): killing the CONTROLLER
        alone (a plain `proc.kill()`) leaves a forked child running as an
        orphan -- the process-GROUP kill must reach it too. Spawns a
        parent that forks a long-lived child and writes the child's pid
        to a file, then asserts the child pid is gone shortly after the
        watchdog trips."""
        marker = tmp_path / "child.pid"
        script = (
            "import os, sys, time\n"
            f"pid = os.fork()\n"
            "if pid == 0:\n"
            "    time.sleep(30)\n"
            "    sys.exit(0)\n"
            f"open({str(marker)!r}, 'w').write(str(pid))\n"
            "time.sleep(30)\n"
        )
        config = _refresh_mod._WatchdogConfig(
            wall_clock_s=0.5, no_progress_s=60.0, poll_interval_s=0.1
        )
        result = _refresh_mod._spawn_with_watchdog(
            ["python3", "-c", script], cwd=tmp_path, config=config
        )
        assert result.is_err
        # Give the killed child a brief moment to actually be reaped by
        # the kernel/init before checking -- `_kill_process_group` itself
        # already waited out its own grace period.
        deadline = time.monotonic() + 2.0
        child_pid = int(marker.read_text().strip()) if marker.exists() else None
        if child_pid is not None:
            while time.monotonic() < deadline:
                try:
                    os.kill(child_pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.1)
            else:
                pytest.fail(f"forked child pid {child_pid} survived the group kill")


# frob:ticket T-1677
class TestPytestOutcomeWorkerCrashRecovery:
    """T-1677/T-1672: `_pytest_outcome`'s xdist worker-crash detection and
    one-shot serial retry, `_spawn` mocked (the crash signature is a pure
    string match, no real subprocess needed to exercise the branching)."""

    _CRASH_OUTPUT = (
        "INTERNALERROR> Traceback (most recent call last):\n"
        "INTERNALERROR> KeyError: <WorkerController gw15>\n"
    )

    def test_crash_signature_triggers_one_serial_retry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery.test_crash_signature_triggers_one_serial_retry  # noqa: E501
        calls: list[list[str]] = []

        def _fake_spawn(argv, *, cwd):  # noqa: ANN001, ARG001
            calls.append(list(argv))
            if len(calls) == 1:
                return Ok(
                    subprocess.CompletedProcess(argv, 3, stdout=self._CRASH_OUTPUT)
                )
            return Ok(subprocess.CompletedProcess(argv, 0, stdout="8654 passed\n"))

        monkeypatch.setattr(_refresh_mod, "_spawn", _fake_spawn)

        result = _refresh_mod._pytest_outcome(["pytest", "-n", "auto"], cwd=tmp_path)
        assert result.is_ok
        outcome = result.danger_ok
        assert outcome.worker_crash is True
        assert outcome.degraded is False  # the retry succeeded
        assert outcome.exit_code == 0
        assert len(calls) == 2
        assert calls[1][-2:] == ["-p", "no:xdist"]

    def test_crash_signature_with_failing_retry_stays_degraded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery.test_crash_signature_with_failing_retry_stays_degraded  # noqa: E501
        """The retry itself finding a REAL failure (not another crash) is
        reported as an honest red suite, not silently swallowed."""

        def _fake_spawn(argv, *, cwd):  # noqa: ANN001, ARG001
            if "-p" in argv:
                return Ok(subprocess.CompletedProcess(argv, 1, stdout="1 failed\n"))
            return Ok(subprocess.CompletedProcess(argv, 3, stdout=self._CRASH_OUTPUT))

        monkeypatch.setattr(_refresh_mod, "_spawn", _fake_spawn)

        result = _refresh_mod._pytest_outcome(["pytest", "-n", "auto"], cwd=tmp_path)
        assert result.is_ok
        outcome = result.danger_ok
        assert outcome.worker_crash is True
        assert outcome.degraded is True
        assert outcome.exit_code == 1

    def test_ordinary_red_suite_is_not_classified_as_worker_crash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery.test_ordinary_red_suite_is_not_classified_as_worker_crash  # noqa: E501
        """T-1672 item 3 -- an ordinary test failure must NOT be
        misclassified as an environment abort (that would send a reader
        hunting for a nonexistent resource-kill instead of the real
        regression)."""
        calls: list[list[str]] = []

        def _fake_spawn(argv, *, cwd):  # noqa: ANN001, ARG001
            calls.append(list(argv))
            return Ok(
                subprocess.CompletedProcess(argv, 1, stdout="1 failed, 99 passed\n")
            )

        monkeypatch.setattr(_refresh_mod, "_spawn", _fake_spawn)

        result = _refresh_mod._pytest_outcome(["pytest"], cwd=tmp_path)
        assert result.is_ok
        outcome = result.danger_ok
        assert outcome.worker_crash is False
        assert outcome.degraded is True
        assert len(calls) == 1  # no retry for an ordinary red suite


# frob:ticket T-1677
class TestNativeCoverageRefreshAbort:
    """T-1677: a watchdog abort (either deadline) must never touch
    `coverage.xml`/`stamp_coverage`, and must record itself explicitly so
    a stale-but-present `coverage.xml` (T-1672's memory-level precedent
    for this exact trap) is never silently read as fresh."""

    @pytest.mark.parametrize(
        ("spawn_error", "expected_refresh_error"),
        [
            (
                _refresh_mod._SpawnError.WallClockExceeded,
                _refresh_mod.CoverageRefreshError.PytestWallClockExceeded,
            ),
            (
                _refresh_mod._SpawnError.NoProgress,
                _refresh_mod.CoverageRefreshError.PytestNoProgress,
            ),
        ],
    )
    def test_watchdog_abort_skips_xml_and_stamp_and_records_provenance(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        spawn_error,
        expected_refresh_error,
    ) -> None:
        # frob:tests tests/test_coverage.py::TestNativeCoverageRefreshAbort.test_watchdog_abort_skips_xml_and_stamp_and_records_provenance  # noqa: E501
        # A pre-existing coverage.xml must survive UNTOUCHED -- this is
        # the "stale artifact silently read as current" trap the ticket
        # names directly.
        existing_xml = tmp_path / "coverage.xml"
        existing_xml.write_text("<coverage>old</coverage>", encoding="utf-8")

        xml_calls: list[list[str]] = []

        def _fake_spawn(argv, *, cwd):  # noqa: ANN001, ARG001
            if argv[0] == "pytest":
                return Err(spawn_error)
            xml_calls.append(list(argv))
            return Ok(subprocess.CompletedProcess(argv, 0))

        monkeypatch.setattr(_refresh_mod, "_spawn", _fake_spawn)
        import frob.gates._coverage as coverage_mod

        stamp_calls: list[object] = []
        monkeypatch.setattr(coverage_mod, "load_stamp", lambda _root: None)
        monkeypatch.setattr(
            coverage_mod,
            "stamp_coverage",
            lambda root, snapshot: stamp_calls.append((root, snapshot)) or Ok(Unit()),  # noqa: ARG005, E501
        )

        result = native_coverage_refresh(tmp_path, _FAKE_SNAPSHOT)
        assert result.is_err
        assert result.danger_err == expected_refresh_error
        assert xml_calls == []
        assert stamp_calls == []
        assert existing_xml.read_text(encoding="utf-8") == "<coverage>old</coverage>"

        record = json.loads(
            (tmp_path / _refresh_mod._RUN_PROVENANCE_REL).read_text(encoding="utf-8")
        )
        assert record["aborted"] is True
        assert record["abort_reason"] == expected_refresh_error.value


# frob:ticket T-1516
class TestRunCoverageWaitNativeDefault:
    """T-1516: `run_coverage_wait(root)` with NO `command=` argument (the
    real production call shape, `frob.app.test_runner`'s own call site)
    now drives the refresh through `native_coverage_refresh` in-process
    instead of spawning `make coverage-fast` -- the auto-wiring T-1205
    acceptance[4] describes, with zero call-site changes required."""

    # frob:ticket T-1516
    def test_default_command_none_calls_native_refresh(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.testing._coverage_wait import run_coverage_wait

        root = tmp_path / "repo"
        pkg = root / "src" / "pkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "mod.py").write_text("def fn():\n    return 1\n", encoding="utf-8")

        calls: list[Path] = []

        def _fake_native(refresh_root, snapshot, **kw):  # noqa: ANN001, ARG001
            calls.append(refresh_root)
            return Ok(Unit())

        monkeypatch.setattr(_refresh_mod, "native_coverage_refresh", _fake_native)

        result = run_coverage_wait(root)
        assert result.is_ok
        assert calls == [root]
