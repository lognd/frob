"""Tests for frob.ghio -- the one gh (GitHub CLI) subprocess seam
(docs/modules/ghio.md). Every test fakes the subprocess boundary by
monkeypatching `run_argv` (mirrors tests/test_gitio.py's own discipline)
so this file never depends on `gh` being installed, authenticated, or
pointed at a GitHub remote."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typani import Err, Ok
from typani.result import Result

import frob.ghio as ghio_mod
from frob.ghio import (
    GhError,
    JobLog,
    job_log,
    list_runs,
    preflight,
    view_run,
)
from frob.gitio import GitError, ProcResult


def _ok(
    stdout: str = "", *, argv: tuple[str, ...] = ()
) -> Result[ProcResult, GitError]:
    return Ok(ProcResult(argv=argv, returncode=0, stdout=stdout, stderr=""))


def _fail(stderr: str, *, returncode: int = 1) -> Result[ProcResult, GitError]:
    return Ok(ProcResult(argv=(), returncode=returncode, stdout="", stderr=stderr))


def _scripted(monkeypatch: pytest.MonkeyPatch, responses: dict[str, object]) -> None:
    """Monkeypatch `run_argv` to dispatch on the first two argv tokens
    after `gh` (e.g. "auth status", "run list") to a scripted Result."""

    def fake_run_argv(argv, *, cwd=None, timeout_s=30.0, env=None):  # noqa: ANN001, ANN201
        key = " ".join(argv[1:3])
        for prefix, response in responses.items():
            if key.startswith(prefix):
                return response
        raise AssertionError(f"unscripted gh invocation: {argv}")

    monkeypatch.setattr(ghio_mod, "run_argv", fake_run_argv)


class TestPreflight:
    def test_not_installed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ghio.py::preflight
        monkeypatch.setattr(
            ghio_mod, "run_argv", lambda *a, **k: Err(GitError.GitFailed)
        )
        result = preflight(tmp_path)
        assert result.is_err
        assert result.danger_err == GhError.NotInstalled

    def test_not_authenticated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ghio.py::preflight
        _scripted(
            monkeypatch,
            {
                "--version": _ok("gh version 2.40.0\n"),
                "auth status": _fail(
                    "gh: To use GitHub CLI in a codespace, you must "
                    "authenticate. gh auth status: not logged in to any "
                    "hosts"
                ),
            },
        )
        result = preflight(tmp_path)
        assert result.is_err
        assert result.danger_err == GhError.NotAuthenticated

    def test_credentials_expired(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ghio.py::preflight
        _scripted(
            monkeypatch,
            {
                "--version": _ok("gh version 2.40.0\n"),
                "auth status": _fail(
                    "X github.com token expired\nTo re-authenticate, run: "
                    "gh auth login --hostname github.com"
                ),
            },
        )
        result = preflight(tmp_path)
        assert result.is_err
        assert result.danger_err == GhError.CredentialsExpired

    def test_no_remote(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # frob:tests src/frob/ghio.py::preflight
        _scripted(
            monkeypatch,
            {
                "--version": _ok("gh version 2.40.0\n"),
                "auth status": _ok("Logged in to github.com\n"),
                "repo view": _fail(
                    "no default remote repository has been set for this directory"
                ),
            },
        )
        result = preflight(tmp_path)
        assert result.is_err
        assert result.danger_err == GhError.NoRemote

    def test_rate_limited(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ghio.py::preflight
        _scripted(
            monkeypatch,
            {
                "--version": _ok("gh version 2.40.0\n"),
                "auth status": _ok("Logged in to github.com\n"),
                "repo view": _fail("HTTP 403: API rate limit exceeded for user ID."),
            },
        )
        result = preflight(tmp_path)
        assert result.is_err
        assert result.danger_err == GhError.RateLimited

    def test_network_unreachable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ghio.py::preflight
        _scripted(
            monkeypatch,
            {
                "--version": _ok("gh version 2.40.0\n"),
                "auth status": _ok("Logged in to github.com\n"),
                "repo view": _fail(
                    "dial tcp: lookup api.github.com: could not resolve host"
                ),
            },
        )
        result = preflight(tmp_path)
        assert result.is_err
        assert result.danger_err == GhError.NetworkUnreachable

    def test_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # frob:tests src/frob/ghio.py::preflight
        _scripted(
            monkeypatch,
            {
                "--version": _ok("gh version 2.40.0\n"),
                "auth status": _ok("Logged in to github.com\n"),
                "repo view": _ok(json.dumps({"nameWithOwner": "acme/frob"})),
            },
        )
        result = preflight(tmp_path)
        assert result.is_ok
        env = result.danger_ok
        assert env.account == "acme/frob"
        assert "2.40.0" in env.gh_version

    def test_no_gh_no_auth_no_remote_never_crashes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Must-not-crash proof: an environment with none of gh/auth/
        remote available still returns a typed Err, never raises -- frob
        stays useful off-GitHub."""
        monkeypatch.setattr(
            ghio_mod, "run_argv", lambda *a, **k: Err(GitError.GitFailed)
        )
        result = preflight(tmp_path)
        assert result.is_err
        assert isinstance(result.danger_err, GhError)


class TestListRuns:
    def test_not_found_run_list_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ghio.py::list_runs
        _scripted(
            monkeypatch,
            {"run list": _fail("HTTP 404: Not Found")},
        )
        result = list_runs(tmp_path)
        assert result.is_err
        assert result.danger_err == GhError.NotFound

    def test_success_parses_rows(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ghio.py::list_runs
        rows = [
            {
                "databaseId": 123,
                "name": "CI",
                "status": "completed",
                "conclusion": "failure",
                "headSha": "deadbeef",
                "url": "https://github.com/acme/frob/actions/runs/123",
            }
        ]
        _scripted(monkeypatch, {"run list": _ok(json.dumps(rows))})
        result = list_runs(tmp_path)
        assert result.is_ok
        runs = result.danger_ok
        assert len(runs) == 1
        assert runs[0].run_id == "123"
        assert runs[0].conclusion == "failure"


class TestViewRun:
    def test_run_not_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ghio.py::view_run
        _scripted(
            monkeypatch,
            {"run view": _fail("could not find any workflows named 999")},
        )
        result = view_run(tmp_path, "999")
        assert result.is_err
        assert result.danger_err == GhError.NotFound

    def test_success_parses_jobs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ghio.py::view_run
        payload = {
            "status": "completed",
            "conclusion": "failure",
            "jobs": [
                {
                    "databaseId": 1,
                    "name": "ubuntu",
                    "status": "completed",
                    "conclusion": "failure",
                },
                {
                    "databaseId": 2,
                    "name": "macos",
                    "status": "completed",
                    "conclusion": "success",
                },
            ],
        }
        _scripted(monkeypatch, {"run view": _ok(json.dumps(payload))})
        result = view_run(tmp_path, "42")
        assert result.is_ok
        detail = result.danger_ok
        assert detail.run_id == "42"
        assert len(detail.jobs) == 2
        assert detail.jobs[0].job_id == "1"
        assert detail.jobs[0].conclusion == "failure"


class TestPreflightIntegration:
    def test_real_subprocess_seam_against_a_fake_gh_binary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Integration coverage (frob:tests kind="integration" below):
        exercises `preflight`'s REAL subprocess path end to end -- no
        `run_argv` monkeypatch here, `frob.gitio.run_argv` really spawns
        a process -- by putting a small scripted `gh` executable first on
        PATH rather than relying on the actual `gh` binary being present
        or authenticated in this test environment."""
        # frob:tests src/frob/ghio.py::preflight
        # frob:tests src/frob/ghio.py kind="integration"
        fake_gh = tmp_path / "gh"
        fake_gh.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "--version" ]; then echo "gh version 2.40.0"; exit 0; fi\n'
            'if [ "$1" = "auth" ]; then echo "Logged in to github.com"; exit 0; fi\n'
            'if [ "$1" = "repo" ]; then echo \'{"nameWithOwner": "acme/frob"}\'; '
            "exit 0; fi\n"
            "exit 1\n"
        )
        fake_gh.chmod(0o755)
        monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")

        result = preflight(tmp_path)
        assert result.is_ok
        assert result.danger_ok.account == "acme/frob"


class TestJobLog:
    def _scripted_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        api_response: Result[ProcResult, GitError],
        run_status: str = "completed",
        run_conclusion: str = "failure",
        job_conclusion: str = "failure",
    ) -> None:
        run_payload = {
            "status": run_status,
            "conclusion": run_conclusion,
            "jobs": [
                {
                    "databaseId": 7,
                    "name": "windows",
                    "status": "completed",
                    "conclusion": job_conclusion,
                }
            ],
        }
        _scripted(
            monkeypatch,
            {
                "repo view": _ok(json.dumps({"nameWithOwner": "acme/frob"})),
                "api repos/acme/frob/actions/jobs/7/logs": api_response,
                "run view": _ok(json.dumps(run_payload)),
            },
        )

    def test_empty_log_for_a_failed_job_is_named(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The measured T-2982 incident: --log-failed returned nothing for
        a job that genuinely failed. That MUST be a distinguishable, named
        outcome -- never an Ok("") handed back as if it were clean."""
        # frob:tests src/frob/ghio.py::job_log
        self._scripted_env(
            monkeypatch,
            api_response=_ok(""),
            run_conclusion="failure",
            job_conclusion="failure",
        )
        result = job_log(tmp_path, "100", "7")
        assert result.is_err
        assert result.danger_err == GhError.EmptyLog

    def test_empty_log_for_a_job_with_no_failure_evidence_is_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ghio.py::job_log
        self._scripted_env(
            monkeypatch,
            api_response=_ok(""),
            run_conclusion="success",
            job_conclusion="success",
        )
        result = job_log(tmp_path, "100", "7")
        assert result.is_ok
        log = result.danger_ok
        assert log.empty is True
        assert log.text == ""

    def test_job_in_progress_is_not_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ghio.py::job_log
        _scripted(
            monkeypatch,
            {
                "repo view": _ok(json.dumps({"nameWithOwner": "acme/frob"})),
                "api repos/acme/frob/actions/jobs/7/logs": _fail("HTTP 404: Not Found"),
            },
        )
        result = job_log(tmp_path, "100", "7")
        assert result.is_err
        assert result.danger_err == GhError.NotFound

    def test_run_still_in_progress_when_falling_back_to_run_view_log(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Direct measurement of gh's own stderr classification for the
        run-view --log refusal path, independent of job_log's own
        job-scoped route (which is what job_log uses to AVOID this)."""
        # frob:tests src/frob/ghio.py::GhError
        from frob.ghio import _classify_gh_failure  # noqa: PLC0415

        result = ProcResult(
            argv=("gh", "run", "view", "--log"),
            returncode=1,
            stdout="",
            stderr="run 100 is still in progress; logs will be available "
            "when it is complete",
        )
        assert _classify_gh_failure(result) == GhError.RunInProgress

    def test_truncated_log_for_cancelled_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Measured: a cancelled run's log is retrievable but may end
        before a failure summary was ever written -- callers must be told
        this explicitly via `truncated`, never left to infer it."""
        # frob:tests src/frob/ghio.py::job_log
        self._scripted_env(
            monkeypatch,
            api_response=_ok("partial log output, no summary line\n"),
            run_conclusion="cancelled",
            job_conclusion="cancelled",
        )
        result = job_log(tmp_path, "100", "7")
        assert result.is_ok
        log = result.danger_ok
        assert isinstance(log, JobLog)
        assert log.truncated is True
        assert log.empty is False

    def test_normal_log_is_not_truncated_not_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ghio.py::job_log
        self._scripted_env(
            monkeypatch,
            api_response=_ok("FAILED tests/test_x.py::test_y\n"),
            run_conclusion="failure",
            job_conclusion="failure",
        )
        result = job_log(tmp_path, "100", "7")
        assert result.is_ok
        log = result.danger_ok
        assert log.truncated is False
        assert log.empty is False
        assert "FAILED" in log.text

    def test_no_remote_short_circuits_before_api_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ghio.py::job_log
        _scripted(
            monkeypatch,
            {
                "repo view": _fail(
                    "no default remote repository has been set for this directory"
                )
            },
        )
        result = job_log(tmp_path, "100", "7")
        assert result.is_err
        assert result.danger_err == GhError.NoRemote
