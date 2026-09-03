import json
from pathlib import Path

import pytest

from tests.conftest import (
    PACKAGE_LOCK_JSON_V3,
    UV_LOCK,
)


class TestScanTreeLockArg:
    def test_scan_tree_lockfile_arg(self, tmp_path: Path) -> None:
        """T-0221 regression: `scan_tree(<path to a lockfile file>)` must vet
        that lockfile, not treat it as a directory root and fail to find
        anything under it."""
        from frob.vet._scan import scan_tree

        lockfile = tmp_path / "uv.lock"
        lockfile.write_text(UV_LOCK)

        result = scan_tree(lockfile, fetch=False)
        assert result.is_ok
        report = result.danger_ok
        assert len(report.verdicts) == 2

    def test_scan_tree_unsupp_err(self, tmp_path: Path) -> None:
        """T-0221 regression: an unresolvable lockfile is a typed Err, not a
        silent empty-ok report -- callers (the CLI) rely on this to exit
        nonzero rather than gate-poisoning with a vacuous pass."""
        from frob.vet._models import VetError
        from frob.vet._scan import scan_tree

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = scan_tree(empty_dir, fetch=False)
        assert result.is_err
        assert result.danger_err is VetError.LockfileUnsupported


class TestVetRunnerLockArg:
    def test_run_lockfile_arg(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-0221 regression: `frob vet <path/to/uv.lock>` (CLI entry point)
        vets that lockfile rather than misreading the path as a directory
        root and reporting no supported lockfile."""
        from frob.app.config import AppConfig
        from frob.app.vet_runner import run

        lockfile = tmp_path / "uv.lock"
        lockfile.write_text(UV_LOCK)

        cfg = AppConfig(vet_path=lockfile)
        with pytest.raises(SystemExit) as exc_info:
            run(cfg)
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "requests" in out

    def test_run_unsupp_nonzero(self, tmp_path: Path) -> None:
        """T-0221 regression: a LockfileUnsupported Err must not be a silent
        exit-0 -- that is the same vacuous-pass class as T-0184 and poisons
        any gate relying on `frob vet`'s exit code."""
        from frob.app.config import AppConfig
        from frob.app.vet_runner import run

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        cfg = AppConfig(vet_path=empty_dir)
        with pytest.raises(SystemExit) as exc_info:
            run(cfg)
        assert exc_info.value.code != 0


class TestScanTreeWithLocalSource:
    def test_scan_tree_detects_capabilities_from_node_modules(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End-to-end: a lockfile dep whose node_modules source uses net/exec
        surfaces those capabilities in the report's verdict."""
        from frob.vet._scan import scan_tree

        (tmp_path / "package-lock.json").write_text(
            json.dumps(
                {
                    "name": "app",
                    "lockfileVersion": 3,
                    "packages": {
                        "": {"name": "app", "version": "1.0.0"},
                        "node_modules/sketchy-pkg": {"version": "1.0.0"},
                    },
                }
            )
        )
        pkg_dir = tmp_path / "node_modules" / "sketchy-pkg"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "index.js").write_text(
            "const cp = require('child_process');\ncp.execSync('ls');\n"
        )
        (tmp_path / "frob.toml").write_text(
            "[vet]\nenforce = true\n\n[vet.allow]\nsketchy-pkg = true\n"
        )

        result = scan_tree(tmp_path, fetch=False)
        assert result.is_ok
        report = result.danger_ok
        verdict = next(v for v in report.verdicts if v.name == "sketchy-pkg")
        assert "exec" in verdict.capabilities

    def test_scan_tree_flags_undeclared_capability(self, tmp_path: Path) -> None:
        """VET002: a declared capability list narrower than what's observed fires."""
        from frob.vet._scan import scan_tree

        (tmp_path / "package-lock.json").write_text(
            json.dumps(
                {
                    "name": "app",
                    "lockfileVersion": 3,
                    "packages": {
                        "": {"name": "app", "version": "1.0.0"},
                        "node_modules/sketchy-pkg": {"version": "1.0.0"},
                    },
                }
            )
        )
        pkg_dir = tmp_path / "node_modules" / "sketchy-pkg"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "index.js").write_text(
            "const cp = require('child_process');\ncp.execSync('ls');\n"
        )
        (tmp_path / "frob.toml").write_text(
            '[vet]\nenforce = true\n\n[vet.allow]\nsketchy-pkg = ["net"]\n'
        )

        result = scan_tree(tmp_path, fetch=False)
        assert result.is_ok
        report = result.danger_ok
        assert any(v.rule == "VET002" for v in report.violations)

    def test_scan_tree_surfaces_a_cve_fingerprint_finding(self, tmp_path: Path) -> None:
        # T-0153: a dependency whose source contains a fingerprinted
        # vulnerable-usage pattern (here, FP-DESERIALIZE-YAML-001's
        # yaml.load() needle) must surface a VET006 finding through the
        # REAL `frob vet` pipeline (scan_tree), not just via a direct
        # _scan_file_fingerprints import -- proving the wiring, not just
        # the detector.
        # frob:tests src/frob/vet/_scan.py::_scan_source kind="unit"
        from frob.vet._scan import scan_tree

        (tmp_path / "uv.lock").write_text(
            '[[package]]\nname = "sketchy-pkg"\nversion = "1.0.0"\n'
        )
        pkg_dir = (
            tmp_path / ".venv" / "lib" / "python3.11" / "site-packages" / "sketchy_pkg"
        )
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text(
            "import yaml\n\ndef load_config(raw):\n    return yaml.load(raw)\n"
        )
        (tmp_path / "frob.toml").write_text(
            "[vet]\nenforce = true\n\n[vet.allow]\nsketchy-pkg = true\n"
        )

        result = scan_tree(tmp_path, fetch=False)
        assert result.is_ok
        report = result.danger_ok
        fp_violations = [v for v in report.violations if v.rule == "VET006"]
        assert fp_violations
        assert "FP-DESERIALIZE-YAML-001" in fp_violations[0].message
        verdict = next(v for v in report.verdicts if v.name == "sketchy-pkg")
        assert "cve-fingerprint" in verdict.signals


class TestScanTreeSourceUnavailableFailClosed:
    """T-0400 audit finding #1: a dependency whose source is not present
    locally used to be silently APPROVED (empty capability set, zero
    violations) -- indistinguishable from "checked and clean". This is now
    a fail-closed VET-SOURCE-UNAVAILABLE ERROR finding."""

    def test_missing_source_surfaces_error_violation(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_scan.py::_scan_located_source kind="unit"
        from frob.findings import Severity
        from frob.vet._scan import scan_tree

        (tmp_path / "uv.lock").write_text(
            '[[package]]\nname = "unfetched-pkg"\nversion = "1.0.0"\n'
        )
        # No .venv/site-packages entry for unfetched-pkg -- source is
        # genuinely not present locally.
        (tmp_path / "frob.toml").write_text(
            "[vet]\nenforce = true\n\n[vet.allow]\nunfetched-pkg = true\n"
        )

        result = scan_tree(tmp_path, fetch=False)
        assert result.is_ok
        report = result.danger_ok
        source_violations = [
            v for v in report.violations if v.rule == "VET-SOURCE-UNAVAILABLE"
        ]
        assert len(source_violations) == 1
        assert source_violations[0].severity is Severity.ERROR
        assert "unfetched-pkg" in source_violations[0].message
        verdict = next(v for v in report.verdicts if v.name == "unfetched-pkg")
        assert "source-unavailable" in verdict.signals
        assert verdict.capabilities == frozenset()

    def test_enforced_missing_source_fails_the_gate(self, tmp_path: Path) -> None:
        # The whole point of fail-closed: `enforce = true` + an
        # ERROR-severity VET-SOURCE-UNAVAILABLE must make the report
        # non-passing via the same enforce/ERROR contract every other
        # vet rule uses.
        from frob.findings import Severity
        from frob.vet._scan import scan_tree

        (tmp_path / "uv.lock").write_text(
            '[[package]]\nname = "unfetched-pkg"\nversion = "1.0.0"\n'
        )
        (tmp_path / "frob.toml").write_text(
            "[vet]\nenforce = true\n\n[vet.allow]\nunfetched-pkg = true\n"
        )

        result = scan_tree(tmp_path, fetch=False)
        assert result.is_ok
        report = result.danger_ok
        assert report.enforce is True
        assert any(v.severity is Severity.ERROR for v in report.violations)


class TestScanTreeMultipleLockfiles:
    """T-0400 audit finding #2: a repo with more than one supported
    lockfile used to have every lockfile after the first silently
    unscanned."""

    def test_scan_tree_scans_every_lockfile(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_scan.py::scan_tree kind="unit"
        from frob.vet._scan import scan_tree

        (tmp_path / "uv.lock").write_text(UV_LOCK)
        (tmp_path / "package-lock.json").write_text(PACKAGE_LOCK_JSON_V3)

        result = scan_tree(tmp_path, fetch=False)
        assert result.is_ok
        report = result.danger_ok
        names = {v.name for v in report.verdicts}
        # uv.lock's pypi deps (requests + one other) AND package-lock.json's
        # npm deps (lodash, chalk) must all be represented -- the old
        # first-lockfile-only search would have dropped lodash/chalk
        # entirely.
        assert "requests" in names
        assert "lodash" in names
        assert "chalk" in names


class TestScanTreeTimeout:
    # frob:tests src/frob/vet/_scan.py::_run_with_timeout kind="unit"
    def test_slow_package_returns_within_timeout_not_task_duration(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0208 review round 1: a naive `with ThreadPoolExecutor(...)`
        around the timeout-bound call blocks in `__exit__` (shutdown(wait=
        True)) until the abandoned task finishes, silently defeating the
        timeout -- only the verdict label would change, wall time would
        not. Assert an upper bound on wall time (a few multiples of the
        configured timeout, well under the task's real 3s duration) so a
        regression back to that shape is caught by a measurement, not an
        inspection."""
        import time

        from frob.vet import _scan

        (tmp_path / "uv.lock").write_text(
            '[[package]]\nname = "slow-pkg"\nversion = "1.0.0"\n'
        )
        (tmp_path / "frob.toml").write_text(
            "[vet]\nenforce = true\n\n[vet.allow]\nslow-pkg = true\n"
        )

        def _slow_process_dependency(*args, **kwargs):
            time.sleep(3.0)
            raise AssertionError("should have been abandoned at the timeout")

        monkeypatch.setattr(_scan, "_process_dependency", _slow_process_dependency)

        t0 = time.monotonic()
        result = _scan.scan_tree(tmp_path, fetch=False, timeout=0.2)
        elapsed = time.monotonic() - t0

        assert result.is_ok
        assert elapsed < 1.5, (
            f"scan_tree took {elapsed:.2f}s with timeout=0.2 -- "
            f"the timeout is not actually bounding wall time"
        )
        report = result.danger_ok
        assert any(v.rule == "VET-TIMEOUT" for v in report.violations)
        verdict = next(v for v in report.verdicts if v.name == "slow-pkg")
        assert "timeout" in verdict.signals

    # frob:tests tests/vet_suite/test_scan_tree.py::TestScanTreeTimeout.test_timed_out_worker_is_daemon_not_registered  # noqa: E501
    def test_timed_out_worker_is_daemon_not_registered(self, tmp_path: Path) -> None:
        """T-3708 regression: an abandoned-on-timeout `_process_dependency`
        worker must not be able to block interpreter shutdown.

        `concurrent.futures.thread` keeps a process-global registry
        (`_threads_queues`) of every `ThreadPoolExecutor` worker thread and
        its `atexit`-registered `_python_exit()` unconditionally joins
        every thread still alive in that registry at interpreter shutdown
        -- this is what hung win32 CI's `frob check` teardown for ~120s
        (T-3707/T-3708) once `_bounded_process_dependency` abandoned a
        still-blocked worker via `shutdown(wait=False)`. Prove the fix
        directly: after a timeout, the abandoned worker thread is a daemon
        thread NOT present in `concurrent.futures.thread`'s global join
        registry, so `_python_exit()` cannot hang on it.
        """
        import concurrent.futures.thread as cf_thread
        import threading
        from concurrent.futures import TimeoutError as FutureTimeoutError

        # `_bounded_process_dependency` delegates its timeout-bounding
        # directly to `frob._daemon_timeout._run_bounded` (T-3708) -- that
        # delegation is exercised end-to-end by
        # `test_slow_package_returns_within_timeout_not_task_duration`
        # above via `scan_tree`. This test targets the atexit-join hazard
        # itself, which lives entirely in `_run_bounded`'s daemon-thread
        # shape, so it drives `_run_bounded` the same way
        # `_bounded_process_dependency` does rather than re-satisfying
        # `_process_dependency`'s full argument contract.
        from frob._daemon_timeout import _run_bounded

        release = threading.Event()

        def _hang_until_released() -> None:
            release.wait(timeout=30)

        before = set(threading.enumerate())
        try:
            _run_bounded(_hang_until_released, timeout=0.1)
        except FutureTimeoutError:
            pass

        new_threads = set(threading.enumerate()) - before
        bounded_workers = [t for t in new_threads if t.name.startswith("frob-bounded-")]
        assert bounded_workers, "expected the abandoned worker thread to be visible"
        worker = bounded_workers[0]

        try:
            # (a) it is a daemon thread -- never joined by the interpreter
            # at exit, unlike a ThreadPoolExecutor worker.
            assert worker.daemon is True

            # (b) it was never registered with concurrent.futures.thread's
            # process-global join registry -- the exact registry
            # `_python_exit()` iterates at atexit. A ThreadPoolExecutor-
            # backed worker would appear here; a plain daemon thread never
            # does.
            registered_threads = set(cf_thread._threads_queues.keys())
            assert worker not in registered_threads
        finally:
            release.set()
            worker.join(timeout=5)
