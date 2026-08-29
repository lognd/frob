"""T-3099: `apply_agent_env`/`warn_if_xdist_bound_missing` (T-3094) must
actually be wired into every pytest-spawn call site this ticket named --
`_run_pytest_directly` (frob.app.ticket_runner._verify),
`collect_python_tests` (frob.testing._collect),
`native_coverage_refresh` (frob.testing._coverage_refresh),
`mutate_runner.run` (frob.app.mutate_runner), and `perf_runner._profile`
(frob.app.perf_runner, `--tests` path only).

T-3094 measured the underlying defect precisely: `apply_agent_env`/
`warn_if_xdist_bound_missing` existed and worked correctly in isolation,
but nothing called them before a real pytest spawn, so the fleet-aware
xdist bound never reached a single one of 40 live workers. Each test
below is a MUST-FIRE check that the wiring at this call site actually
invokes both functions before the pytest-spawning call, using the module
each site imports its own bound name from (not a re-export) so a
site that quietly imports the wrong symbol still fails here."""

from __future__ import annotations

from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from typani.result import Ok

from frob.app import mutate_runner, perf_runner
from frob.app.config import AppConfig, Subcommand
from frob.app.ticket_runner import _verify
from frob.graph import GraphSnapshot
from frob.testing import _collect, _coverage_refresh


class TestVerifyRunPytestDirectlyWiring:
    """`_run_pytest_directly` (frob.app.ticket_runner._verify) must apply
    the bound and check for its absence before spawning verification
    pytest."""

    def test_must_fire_applies_and_warns_before_spawn(self, tmp_path: Path) -> None:
        """Both calls happen, in order, before the guarded subprocess
        spawn."""
        calls: list[str] = []

        def fake_apply(root):  # noqa: ANN001, ANN202
            calls.append("apply")
            return Ok({})

        def fake_warn(root):  # noqa: ANN001, ANN202
            calls.append("warn")

        def fake_guarded_subprocess_run(args, **kwargs):  # noqa: ANN001
            calls.append("spawn")
            import subprocess

            return Ok(
                subprocess.CompletedProcess(
                    args=args, returncode=0, stdout="", stderr=""
                )
            )

        with (
            patch.object(_verify, "apply_agent_env", fake_apply),
            patch.object(_verify, "warn_if_xdist_bound_missing", fake_warn),
        ):
            from frob.app import ticket_runner

            with patch.object(
                ticket_runner, "guarded_subprocess_run", fake_guarded_subprocess_run
            ):
                result = _verify._run_pytest_directly(
                    tmp_path, ["tests/test_x.py::test_y"]
                )

        assert result is True
        assert calls == ["apply", "warn", "spawn"]


class TestCollectPythonTestsWiring:
    """`collect_python_tests` (frob.testing._collect) must apply the
    bound and check for its absence before its own `--collect-only`
    spawn."""

    def test_must_fire_applies_and_warns_before_collection(
        self, tmp_path: Path
    ) -> None:
        """Both calls happen before `_run_collect_only`."""
        calls: list[str] = []

        def fake_apply(root):  # noqa: ANN001, ANN202
            calls.append("apply")
            return Ok({})

        def fake_warn(root):  # noqa: ANN001, ANN202
            calls.append("warn")

        def fake_run_collect_only(cwd):  # noqa: ANN001, ANN202
            calls.append("collect")
            return Ok(frozenset())

        with (
            patch.object(_collect, "apply_agent_env", fake_apply),
            patch.object(_collect, "warn_if_xdist_bound_missing", fake_warn),
            patch.object(_collect, "_load_natives_or_empty", lambda root: ()),
            patch.object(_collect, "_missing_natives", lambda natives: ()),
            patch.object(_collect, "_load_cache", lambda cache_path, key: None),
            patch.object(_collect, "_run_collect_only", fake_run_collect_only),
            patch.object(_collect, "_python_runner_cwds", lambda root: ()),
            patch.object(_collect, "_store_cache", lambda *a, **k: None),
        ):
            result = _collect.collect_python_tests(tmp_path)

        assert result.is_ok
        assert calls == ["apply", "warn", "collect"]


class TestNativeCoverageRefreshWiring:
    """`native_coverage_refresh` (frob.testing._coverage_refresh) must
    apply the bound and check for its absence before dispatching to the
    pytest pass."""

    def test_must_fire_applies_and_warns_before_pytest_pass(
        self, tmp_path: Path
    ) -> None:
        """Both calls happen before `_run_pytest_pass`."""
        calls: list[str] = []

        def fake_apply(root):  # noqa: ANN001, ANN202
            calls.append("apply")
            return Ok({})

        def fake_warn(root):  # noqa: ANN001, ANN202
            calls.append("warn")

        def fake_run_pytest_pass(root, snapshot, **kwargs):  # noqa: ANN001, ANN202
            calls.append("pytest_pass")
            from typani.result import Err

            from frob.testing._coverage_refresh import CoverageRefreshError

            return Err(CoverageRefreshError.PytestRefused)

        with (
            patch.object(_coverage_refresh, "apply_agent_env", fake_apply),
            patch.object(_coverage_refresh, "warn_if_xdist_bound_missing", fake_warn),
            patch("frob.gates._coverage.load_stamp", lambda root: None),
            patch.object(_coverage_refresh, "_run_pytest_pass", fake_run_pytest_pass),
        ):
            _coverage_refresh.native_coverage_refresh(
                tmp_path, snapshot=cast(GraphSnapshot, object())
            )

        assert calls[:2] == ["apply", "warn"]
        assert "pytest_pass" in calls


class TestMutateRunnerWiring:
    """`mutate_runner.run` must apply the bound and check for its
    absence before `run_mutations` spawns the mutant test command."""

    def test_must_fire_applies_and_warns_before_run_mutations(
        self, tmp_path: Path
    ) -> None:
        """Both calls happen before `run_mutations`."""
        calls: list[str] = []

        def fake_apply(root):  # noqa: ANN001, ANN202
            calls.append("apply")
            return Ok({})

        def fake_warn(root):  # noqa: ANN001, ANN202
            calls.append("warn")

        def fake_run_mutations(root, file, argv):  # noqa: ANN001, ANN202
            calls.append("mutate")
            from typani.result import Err

            from frob.mutate import MutateError

            return Err(MutateError.ParseFailed)

        cfg = AppConfig(
            subcommand=Subcommand.mutate,
            mutate_file=tmp_path / "x.py",
            mutate_path=tmp_path,
        )

        with (
            patch.object(mutate_runner, "apply_agent_env", fake_apply),
            patch.object(mutate_runner, "warn_if_xdist_bound_missing", fake_warn),
            patch("frob.mutate.run_mutations", fake_run_mutations),
            pytest.raises(SystemExit),
        ):
            mutate_runner.run(cfg)

        assert calls[:2] == ["apply", "warn"]
        assert "mutate" in calls


class TestPerfRunnerProfileWiring:
    """`perf_runner._profile` must apply the bound and check for its
    absence before `profile_command` spawns pytest -- but ONLY on the
    `--tests` path (a raw `-- <argv>` profile target may not be pytest at
    all)."""

    def test_must_fire_applies_and_warns_for_tests_path(self, tmp_path: Path) -> None:
        """`--tests` triggers both calls before `profile_command`."""
        calls: list[str] = []

        def fake_apply(root):  # noqa: ANN001, ANN202
            calls.append("apply")
            return Ok({})

        def fake_warn(root):  # noqa: ANN001, ANN202
            calls.append("warn")

        def fake_profile_command(argv, root):  # noqa: ANN001, ANN202
            calls.append("profile")
            from types import SimpleNamespace

            return Ok(SimpleNamespace(sha="deadbeef", total_s=0.1, exit_code=0))

        cfg = AppConfig(
            subcommand=Subcommand.perf,
            perf_command="profile",
            perf_path=tmp_path,
            perf_tests=True,
        )

        with (
            patch.object(perf_runner, "apply_agent_env", fake_apply),
            patch.object(perf_runner, "warn_if_xdist_bound_missing", fake_warn),
            patch("frob.perf.profile_command", fake_profile_command),
        ):
            perf_runner._profile(cfg)

        assert calls == ["apply", "warn", "profile"]

    def test_must_stay_quiet_raw_argv_path_does_not_wire(self, tmp_path: Path) -> None:
        """A raw `-- <argv>` profile target (no `--tests`) is NOT
        necessarily pytest -- neither function must fire on that path."""
        calls: list[str] = []

        def fake_apply(root):  # noqa: ANN001, ANN202
            calls.append("apply")
            return Ok({})

        def fake_warn(root):  # noqa: ANN001, ANN202
            calls.append("warn")

        def fake_profile_command(argv, root):  # noqa: ANN001, ANN202
            from types import SimpleNamespace

            return Ok(SimpleNamespace(sha="deadbeef", total_s=0.1, exit_code=0))

        cfg = AppConfig(
            subcommand=Subcommand.perf,
            perf_command="profile",
            perf_path=tmp_path,
            perf_tests=False,
            perf_argv=["--", "echo", "hi"],
        )

        with (
            patch.object(perf_runner, "apply_agent_env", fake_apply),
            patch.object(perf_runner, "warn_if_xdist_bound_missing", fake_warn),
            patch("frob.perf.profile_command", fake_profile_command),
        ):
            perf_runner._profile(cfg)

        assert calls == []
