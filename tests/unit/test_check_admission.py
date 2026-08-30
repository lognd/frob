"""T-3256: cross-process, memory-aware admission budget for
`frob.check`'s worker pools.

Direct (non-CLI) unit tests over the pure math (`_compute_admitted_
workers`) and the registry/context-manager mechanics (`_admission_
budget`) -- no real `frob check` run, no real concurrent processes; the
registry and `/proc/meminfo` reads are exercised against a tmp_path
fixture and monkeypatched module functions.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import frob.check as check_mod


class TestComputeAdmittedWorkers:
    """`_compute_admitted_workers`'s pure math, `os.cpu_count`/`_available_
    memory_mb`/`_live_concurrent_checks` monkeypatched so each case is
    deterministic regardless of the real host."""

    def test_idle_box_admits_full_pool(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_compute_admitted_workers kind="unit"
        monkeypatch.setattr(os, "cpu_count", lambda: 12)
        monkeypatch.setattr(check_mod, "_live_concurrent_checks", lambda root: 1)
        monkeypatch.setattr(check_mod, "_available_memory_mb", lambda: 20_000)
        admitted, real_cpu, mem_mb, concurrent = check_mod._compute_admitted_workers(
            tmp_path
        )
        assert admitted == 12
        assert real_cpu == 12
        assert mem_mb == 20_000
        assert concurrent == 1

    def test_six_concurrent_checks_reduce_the_pool(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_compute_admitted_workers kind="unit"
        # Mirrors T-3256's own field measurement shape: 12 cores, memory
        # tight (14.5GB used of 23GB -> ~2GB available at 300MB/worker
        # default caps at 6 anyway), six concurrent checks.
        monkeypatch.setattr(os, "cpu_count", lambda: 12)
        monkeypatch.setattr(check_mod, "_live_concurrent_checks", lambda root: 6)
        monkeypatch.setattr(check_mod, "_available_memory_mb", lambda: 2_000)
        admitted, real_cpu, mem_mb, concurrent = check_mod._compute_admitted_workers(
            tmp_path
        )
        assert admitted < real_cpu
        assert admitted >= 1
        assert concurrent == 6

    def test_memory_bound_beats_cpu_bound(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_compute_admitted_workers kind="unit"
        # Plenty of cores, almost no memory -- T-3256's explicit
        # requirement that memory, not CPU, is the binding constraint.
        monkeypatch.setattr(os, "cpu_count", lambda: 64)
        monkeypatch.setattr(check_mod, "_live_concurrent_checks", lambda root: 1)
        monkeypatch.setattr(check_mod, "_available_memory_mb", lambda: 300)
        admitted, real_cpu, mem_mb, concurrent = check_mod._compute_admitted_workers(
            tmp_path
        )
        assert admitted == 1
        assert real_cpu == 64

    def test_never_admits_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_compute_admitted_workers kind="unit"
        # Degrade, never refuse (T-3256 requirement 2): even an absurd
        # concurrency count floors at 1, never 0.
        monkeypatch.setattr(os, "cpu_count", lambda: 4)
        monkeypatch.setattr(check_mod, "_live_concurrent_checks", lambda root: 500)
        monkeypatch.setattr(check_mod, "_available_memory_mb", lambda: 50_000)
        admitted, _real_cpu, _mem_mb, _concurrent = check_mod._compute_admitted_workers(
            tmp_path
        )
        assert admitted == 1

    def test_unmeasurable_memory_falls_back_to_concurrency_split(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_compute_admitted_workers kind="unit"
        monkeypatch.setattr(os, "cpu_count", lambda: 8)
        monkeypatch.setattr(check_mod, "_live_concurrent_checks", lambda root: 4)
        monkeypatch.setattr(check_mod, "_available_memory_mb", lambda: None)
        admitted, real_cpu, mem_mb, concurrent = check_mod._compute_admitted_workers(
            tmp_path
        )
        assert mem_mb is None
        assert admitted == max(1, real_cpu // concurrent)
        assert concurrent == 4

    def test_max_workers_env_zero_is_full_opt_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_compute_admitted_workers kind="unit"
        monkeypatch.setattr(os, "cpu_count", lambda: 12)
        monkeypatch.setenv("FROB_CHECK_MAX_WORKERS", "0")
        monkeypatch.setattr(
            check_mod,
            "_live_concurrent_checks",
            lambda root: (_ for _ in ()).throw(
                AssertionError("must not measure concurrency under an override")
            ),
        )
        admitted, real_cpu, mem_mb, concurrent = check_mod._compute_admitted_workers(
            tmp_path
        )
        assert admitted == real_cpu == 12
        assert mem_mb is None
        assert concurrent == 1

    def test_max_workers_env_pins_an_exact_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_compute_admitted_workers kind="unit"
        monkeypatch.setattr(os, "cpu_count", lambda: 12)
        monkeypatch.setenv("FROB_CHECK_MAX_WORKERS", "3")
        admitted, _real_cpu, _mem_mb, _concurrent = check_mod._compute_admitted_workers(
            tmp_path
        )
        assert admitted == 3

    def test_malformed_max_workers_env_is_ignored(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_compute_admitted_workers kind="unit"
        monkeypatch.setattr(os, "cpu_count", lambda: 12)
        monkeypatch.setenv("FROB_CHECK_MAX_WORKERS", "not-a-number")
        monkeypatch.setattr(check_mod, "_live_concurrent_checks", lambda root: 1)
        monkeypatch.setattr(check_mod, "_available_memory_mb", lambda: 20_000)
        admitted, real_cpu, _mem_mb, _concurrent = check_mod._compute_admitted_workers(
            tmp_path
        )
        assert admitted == real_cpu == 12

    def test_malformed_per_worker_mem_env_uses_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_per_worker_mem_budget_mb kind="unit"
        monkeypatch.setenv("FROB_CHECK_PER_WORKER_MEM_MB", "bogus")
        assert (
            check_mod._per_worker_mem_budget_mb()
            == check_mod._DEFAULT_PER_WORKER_MEM_MB
        )

    def test_per_worker_mem_env_overrides_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_per_worker_mem_budget_mb kind="unit"
        monkeypatch.setenv("FROB_CHECK_PER_WORKER_MEM_MB", "512")
        assert check_mod._per_worker_mem_budget_mb() == 512


class TestAdmissionRegistry:
    """`_register_admission`/`_live_concurrent_checks`/`_pid_alive`: the
    cross-process registry mechanics, exercised against a real tmp_path
    directory (no real concurrent processes needed -- markers are written
    directly)."""

    def test_registration_writes_a_marker_and_counts_self(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::_register_admission kind="unit"
        # frob:tests src/frob/check/__init__.py::_live_concurrent_checks kind="unit"
        marker = check_mod._register_admission(tmp_path)
        assert marker.exists()
        assert check_mod._live_concurrent_checks(tmp_path) == 1

    def test_dead_pid_marker_is_reaped_and_not_counted(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::_live_concurrent_checks kind="unit"
        directory = check_mod._admission_dir(tmp_path)
        directory.mkdir(parents=True)
        # A pid essentially guaranteed dead/unowned: PID 1 exists on a
        # normal Linux box (init) but under a permission-denied kill(0) it
        # still reads as alive per `_pid_alive`'s own contract, so use an
        # implausibly large pid instead -- ESRCH (ProcessLookupError) is
        # the reliable case being tested.
        dead_marker = directory / "999999999.json"
        dead_marker.write_text("{}", encoding="utf-8")
        assert check_mod._live_concurrent_checks(tmp_path) == 0
        assert not dead_marker.exists()

    def test_multiple_live_markers_all_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_live_concurrent_checks kind="unit"
        # _live_concurrent_checks keys off the FILENAME stem as the pid, so
        # three distinct numeric marker names simulate three concurrent
        # checks without spawning real processes -- _pid_alive is
        # monkeypatched to treat all of them as live.
        directory = check_mod._admission_dir(tmp_path)
        directory.mkdir(parents=True)
        for pid in (11111, 22222, 33333):
            (directory / f"{pid}.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr(check_mod, "_pid_alive", lambda pid: True)
        assert check_mod._live_concurrent_checks(tmp_path) == 3

    def test_non_numeric_marker_names_are_skipped(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::_live_concurrent_checks kind="unit"
        directory = check_mod._admission_dir(tmp_path)
        directory.mkdir(parents=True)
        (directory / "not-a-pid.json").write_text("{}", encoding="utf-8")
        assert check_mod._live_concurrent_checks(tmp_path) == 0

    def test_missing_registry_directory_counts_zero(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::_live_concurrent_checks kind="unit"
        assert check_mod._live_concurrent_checks(tmp_path / "never-created") == 0

    def test_pid_alive_true_for_self(self) -> None:
        # frob:tests src/frob/check/__init__.py::_pid_alive kind="unit"
        assert check_mod._pid_alive(os.getpid()) is True

    def test_pid_alive_false_for_implausible_pid(self) -> None:
        # frob:tests src/frob/check/__init__.py::_pid_alive kind="unit"
        assert check_mod._pid_alive(999_999_999) is False


class TestAdmissionBudgetContextManager:
    """`_admission_budget`: the end-to-end context manager -- patches and
    restores `os.cpu_count`, registers and deregisters the marker, and
    only logs/patches when the admitted budget is actually smaller."""

    def test_reduced_budget_patches_cpu_count_for_the_duration(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_admission_budget kind="unit"
        real_cpu_count = os.cpu_count
        monkeypatch.setattr(
            check_mod,
            "_compute_admitted_workers",
            lambda root: (2, 12, 4_000, 6),
        )
        with check_mod._admission_budget(tmp_path) as admitted:
            assert admitted == 2
            assert os.cpu_count() == 2
        assert os.cpu_count is real_cpu_count

    def test_full_budget_never_patches_cpu_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_admission_budget kind="unit"
        # MUST-STAY-QUIET: an idle-box admission (admitted == real cpu)
        # must not touch os.cpu_count at all.
        real_cpu_count = os.cpu_count
        monkeypatch.setattr(
            check_mod,
            "_compute_admitted_workers",
            lambda root: (12, 12, 20_000, 1),
        )
        with check_mod._admission_budget(tmp_path):
            assert os.cpu_count is real_cpu_count
        assert os.cpu_count is real_cpu_count

    def test_cpu_count_restored_even_on_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_admission_budget kind="unit"
        real_cpu_count = os.cpu_count
        monkeypatch.setattr(
            check_mod,
            "_compute_admitted_workers",
            lambda root: (2, 12, 4_000, 6),
        )
        with pytest.raises(RuntimeError):
            with check_mod._admission_budget(tmp_path):
                assert os.cpu_count() == 2
                raise RuntimeError("boom")
        assert os.cpu_count is real_cpu_count

    def test_marker_removed_on_exit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_admission_budget kind="unit"
        monkeypatch.setattr(
            check_mod,
            "_compute_admitted_workers",
            lambda root: (12, 12, 20_000, 1),
        )
        marker_path = check_mod._admission_dir(tmp_path) / f"{os.getpid()}.json"
        with check_mod._admission_budget(tmp_path):
            assert marker_path.exists()
        assert not marker_path.exists()

    def test_marker_removed_even_on_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_admission_budget kind="unit"
        monkeypatch.setattr(
            check_mod,
            "_compute_admitted_workers",
            lambda root: (12, 12, 20_000, 1),
        )
        marker_path = check_mod._admission_dir(tmp_path) / f"{os.getpid()}.json"
        with pytest.raises(RuntimeError):
            with check_mod._admission_budget(tmp_path):
                raise RuntimeError("boom")
        assert not marker_path.exists()

    def test_reduced_budget_logs_a_warning_naming_the_numbers(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_admission_budget kind="unit"
        monkeypatch.setattr(
            check_mod,
            "_compute_admitted_workers",
            lambda root: (2, 12, 4_000, 6),
        )
        with caplog.at_level("WARNING", logger="frob.check"):
            with check_mod._admission_budget(tmp_path):
                pass
        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert "reduced worker pool to 2" in messages
        assert "6 concurrent frob check process" in messages
        assert "FROB_CHECK_MAX_WORKERS" in messages

    def test_full_budget_logs_nothing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_admission_budget kind="unit"
        monkeypatch.setattr(
            check_mod,
            "_compute_admitted_workers",
            lambda root: (12, 12, 20_000, 1),
        )
        with caplog.at_level("WARNING", logger="frob.check"):
            with check_mod._admission_budget(tmp_path):
                pass
        assert caplog.records == []


class TestAvailableMemoryMb:
    """`frob.check._available_memory_mb` (T-3256) is a thin delegating
    wrapper around `frob.testing._coverage_refresh._available_memory_mb`
    (DUP001 caught the would-be second, byte-identical `/proc/meminfo`
    parser -- see that function's own docstring for why the import is
    LOCAL, not top-level). The actual parsing behavior is
    `_coverage_refresh`'s own to test; this only proves the delegation
    itself actually reaches it."""

    def test_delegates_to_the_shared_coverage_refresh_implementation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::_available_memory_mb kind="unit"
        import frob.testing._coverage_refresh as coverage_refresh_mod

        monkeypatch.setattr(coverage_refresh_mod, "_available_memory_mb", lambda: 12345)
        assert check_mod._available_memory_mb() == 12345


class TestAdmissionRegistryAnchor:
    """T-3287: the admission registry is anchored to the REPOSITORY (the
    git common dir's parent), shared across every linked worktree of one
    repo, not per-worktree (T-3256's original, inert-for-the-fleet
    choice)."""

    @staticmethod
    def _init_repo(root: Path) -> None:
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
        (root / "README.md").write_text("x", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "c"], cwd=root, check=True)

    def test_non_git_root_falls_back_to_itself(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET half: a plain (non-git) directory anchors to
        itself, exactly T-3256's original per-`root` behavior -- and
        does so WITHOUT emitting `git_common_dir`'s own failed-lookup
        WARNING (that warning is correct for its other callers, but
        would make every non-git `frob check` invocation noisy here)."""
        assert check_mod._admission_registry_anchor(tmp_path) == tmp_path

    def test_primary_checkout_anchors_to_itself(self, tmp_path: Path) -> None:
        """A plain (non-worktree) git checkout anchors to its own root --
        the single-repo case is unaffected by the T-3287 change."""
        self._init_repo(tmp_path)
        assert check_mod._admission_registry_anchor(tmp_path) == tmp_path.resolve()

    def test_two_worktrees_of_one_repo_share_one_anchor(self, tmp_path: Path) -> None:
        """MUST-FIRE: two DIFFERENT linked worktrees of the SAME repo
        resolve to the IDENTICAL anchor -- so two `frob check` runs, one
        per worktree (`frob ticket work`'s own normal shape), register
        in and see ONE shared registry instead of two empty ones."""
        import subprocess

        primary = tmp_path / "primary"
        primary.mkdir()
        self._init_repo(primary)
        wt_a = tmp_path / "wt-a"
        wt_b = tmp_path / "wt-b"
        subprocess.run(
            ["git", "worktree", "add", "-b", "wt-a", str(wt_a)],
            cwd=primary,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "worktree", "add", "-b", "wt-b", str(wt_b)],
            cwd=primary,
            check=True,
            capture_output=True,
        )

        anchor_a = check_mod._admission_registry_anchor(wt_a)
        anchor_b = check_mod._admission_registry_anchor(wt_b)

        assert anchor_a == anchor_b == primary.resolve()

    def test_two_worktrees_see_each_others_markers(self, tmp_path: Path) -> None:
        """MUST-FIRE, end to end: registering from two different linked
        worktrees, `_live_concurrent_checks` called from EITHER worktree
        counts BOTH -- the concrete fix for T-3256's inert divisor."""
        import subprocess

        primary = tmp_path / "primary"
        primary.mkdir()
        self._init_repo(primary)
        wt_a = tmp_path / "wt-a"
        wt_b = tmp_path / "wt-b"
        subprocess.run(
            ["git", "worktree", "add", "-b", "wt-a", str(wt_a)],
            cwd=primary,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "worktree", "add", "-b", "wt-b", str(wt_b)],
            cwd=primary,
            check=True,
            capture_output=True,
        )

        # Two DISTINCT pids -- this process's own real pid (registered
        # from wt_a) plus PID 1 (init: exists on any normal Linux box,
        # and `_pid_alive` treats a permission-denied kill(0) as alive
        # too, so this is reliable regardless of the sandbox's
        # permissions) written directly as a second worktree's marker,
        # since a single test process cannot literally BE two pids at
        # once.
        check_mod._register_admission(wt_a)
        (check_mod._admission_dir(wt_b) / "1.json").write_text("{}", encoding="utf-8")

        assert check_mod._live_concurrent_checks(wt_a) == 2
        assert check_mod._live_concurrent_checks(wt_b) == 2
        # T-3256's original per-worktree registries stay UNUSED now --
        # nothing is written directly under either worktree's own .frob/.
        assert not (wt_a / ".frob" / "check-admission").exists()
        assert not (wt_b / ".frob" / "check-admission").exists()

    def test_two_unrelated_repos_do_not_throttle_each_other(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET: two SEPARATE repos (not worktrees of one
        another) anchor to two DIFFERENT paths, so a check registered in
        one is invisible to the other -- the fix must not become a
        machine-global registry."""
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        repo_a.mkdir()
        repo_b.mkdir()
        self._init_repo(repo_a)
        self._init_repo(repo_b)

        check_mod._register_admission(repo_a)

        assert check_mod._live_concurrent_checks(repo_a) == 1
        assert check_mod._live_concurrent_checks(repo_b) == 0

    def test_stale_marker_from_dead_pid_does_not_permanently_deflate_shared_budget(
        self, tmp_path: Path
    ) -> None:
        """THIRD FIXTURE: a marker left by a PID that died without
        cleanup (a killed `frob check`, the field history this repo has
        already paid for) is reaped, not permanently counted, in the
        SHARED (repository-wide) registry -- the same liveness/reaping
        path `_live_concurrent_checks` already ran per-worktree, now
        exercised against the wider shared anchor two worktrees write
        into."""
        import subprocess

        primary = tmp_path / "primary"
        primary.mkdir()
        self._init_repo(primary)
        wt_a = tmp_path / "wt-a"
        subprocess.run(
            ["git", "worktree", "add", "-b", "wt-a", str(wt_a)],
            cwd=primary,
            check=True,
            capture_output=True,
        )

        # A live registration from wt-a...
        check_mod._register_admission(wt_a)
        # ...plus a stale marker from a PID that no longer exists, written
        # directly into the SHARED registry (simulating a killed check
        # that never reached its own `finally: marker.unlink()`).
        shared_dir = check_mod._admission_dir(wt_a)
        (shared_dir / "999999999.json").write_text("{}", encoding="utf-8")

        # The stale marker is reaped, not counted -- a live check
        # elsewhere in the repo sees only the genuinely live one.
        assert check_mod._live_concurrent_checks(primary) == 1
        assert not (shared_dir / "999999999.json").exists()
