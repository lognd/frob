"""Unit tests for `scripts/verify_release_ci_status.py` (T-3251) --
`release.yml`'s fail-closed CI-status gate ahead of the `upload` job.

Loaded by path via `tests/unit/conftest.py::_load_script` (scripts/ has
no `__init__.py`), matching `test_coordinator_scripts.py`'s own
convention for this repo's other `scripts/*.py` modules. Every `gh api`
call is substituted via the `run_gh` seam -- no real `gh` binary, no
network access, deterministic."""

from __future__ import annotations

import json

from tests.unit.conftest import _load_script as _load

verify_release_ci_status = _load("verify_release_ci_status")

_REPO = "logan/frob"
_SHA = "a" * 40


def _fake_gh(returncode: int, stdout: str, stderr: str = ""):
    """A `run_gh` stand-in that ignores its argv and always returns the
    given fixed response -- the seam `determine_ci_status` calls through."""

    def _run(argv: tuple[str, ...]) -> tuple[int, str, str]:
        return returncode, stdout, stderr

    return _run


def _runs_payload(*, status: str, conclusion: str | None, run_id: int = 1) -> str:
    return json.dumps(
        {
            "total_count": 1,
            "workflow_runs": [
                {"id": run_id, "status": status, "conclusion": conclusion}
            ],
        }
    )


class TestDetermineCiStatus:
    def test_green_on_success_conclusion(self) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_green_on_success_conclusion  # noqa: E501
        payload = _runs_payload(status="completed", conclusion="success")
        result = verify_release_ci_status.determine_ci_status(
            _REPO, _SHA, run_gh=_fake_gh(0, payload)
        )
        assert result.status == "green"
        assert _SHA in result.detail

    def test_red_on_failure_conclusion(self) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_red_on_failure_conclusion  # noqa: E501
        payload = _runs_payload(status="completed", conclusion="failure")
        result = verify_release_ci_status.determine_ci_status(
            _REPO, _SHA, run_gh=_fake_gh(0, payload)
        )
        assert result.status == "red"
        assert "failure" in result.detail

    def test_undetermined_on_api_error(self) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_undetermined_on_api_error  # noqa: E501
        result = verify_release_ci_status.determine_ci_status(
            _REPO, _SHA, run_gh=_fake_gh(1, "", "HTTP 503")
        )
        assert result.status == "undetermined"
        assert "503" in result.detail

    def test_undetermined_on_no_matching_run(self) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_undetermined_on_no_matching_run  # noqa: E501
        payload = json.dumps({"total_count": 0, "workflow_runs": []})
        result = verify_release_ci_status.determine_ci_status(
            _REPO, _SHA, run_gh=_fake_gh(0, payload)
        )
        assert result.status == "undetermined"
        assert "no ci.yml run found" in result.detail

    def test_undetermined_on_unparseable_json(self) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_undetermined_on_unparseable_json  # noqa: E501
        result = verify_release_ci_status.determine_ci_status(
            _REPO, _SHA, run_gh=_fake_gh(0, "not json{{{")
        )
        assert result.status == "undetermined"
        assert "unparseable JSON" in result.detail

    def test_undetermined_on_run_still_in_progress(self) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_undetermined_on_run_still_in_progress  # noqa: E501
        payload = _runs_payload(status="in_progress", conclusion=None)
        result = verify_release_ci_status.determine_ci_status(
            _REPO, _SHA, run_gh=_fake_gh(0, payload)
        )
        assert result.status == "undetermined"
        assert "in_progress" in result.detail

    def test_resolves_by_exact_sha_not_branch_or_latest(self) -> None:
        """The `head_sha=<sha>` query param, not branch name and not an
        unfiltered "latest run" -- confirmed by checking the argv `gh` is
        actually invoked with."""
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestDetermineCiStatus.test_resolves_by_exact_sha_not_branch_or_latest  # noqa: E501
        captured: list[tuple[str, ...]] = []

        def _run(argv: tuple[str, ...]) -> tuple[int, str, str]:
            captured.append(argv)
            return 0, _runs_payload(status="completed", conclusion="success"), ""

        verify_release_ci_status.determine_ci_status(_REPO, _SHA, run_gh=_run)
        assert len(captured) == 1
        joined = " ".join(captured[0])
        assert f"head_sha={_SHA}" in joined
        assert "main" not in joined  # no branch-name fallback anywhere


class TestDecide:
    def test_green_always_proceeds(self) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestDecide.test_green_always_proceeds  # noqa: E501
        result = verify_release_ci_status.CiStatusResult(status="green", detail="ok")
        code, msg = verify_release_ci_status.decide(
            result, override=False, override_reason=""
        )
        assert code == 0
        assert "GREEN" in msg

    def test_red_without_override_refuses(self) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestDecide.test_red_without_override_refuses  # noqa: E501
        result = verify_release_ci_status.CiStatusResult(status="red", detail="boom")
        code, msg = verify_release_ci_status.decide(
            result, override=False, override_reason=""
        )
        assert code == 1
        assert "RED" in msg

    def test_undetermined_without_override_refuses(self) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestDecide.test_undetermined_without_override_refuses  # noqa: E501
        result = verify_release_ci_status.CiStatusResult(
            status="undetermined", detail="no run"
        )
        code, msg = verify_release_ci_status.decide(
            result, override=False, override_reason=""
        )
        assert code == 1
        assert "UNDETERMINED" in msg

    def test_red_with_override_and_reason_proceeds(self) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestDecide.test_red_with_override_and_reason_proceeds  # noqa: E501
        result = verify_release_ci_status.CiStatusResult(status="red", detail="boom")
        code, msg = verify_release_ci_status.decide(
            result,
            override=True,
            override_reason="hotfix for a CI infra outage, verified manually",
        )
        assert code == 0
        assert "OVERRIDDEN" in msg
        assert "hotfix for a CI infra outage" in msg

    def test_override_without_reason_is_refused_even_when_requested(self) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestDecide.test_override_without_reason_is_refused_even_when_requested  # noqa: E501
        result = verify_release_ci_status.CiStatusResult(status="red", detail="boom")
        code, msg = verify_release_ci_status.decide(
            result, override=True, override_reason="   "
        )
        assert code == 1
        assert "no override_reason" in msg


class TestRunGh:
    def test_spawn_failure_reports_as_nonzero_with_stderr(self) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestRunGh.test_spawn_failure_reports_as_nonzero_with_stderr  # noqa: E501
        code, out, err = verify_release_ci_status._run_gh(("__not_a_real_binary__",))
        assert code != 0
        assert out == ""
        assert err


class TestCiStatusResultInvariant:
    def test_valid_status_literal_constructs(self) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestCiStatusResultInvariant.test_valid_status_literal_constructs  # noqa: E501
        result = verify_release_ci_status.CiStatusResult(status="green", detail="ok")
        assert result.status == "green"

    def test_invalid_status_literal_raises(self) -> None:
        """pydantic wraps `model_post_init`'s `AssertionError` into its own
        `ValidationError` -- the underlying assertion message still names
        the bad value, which is what this test actually checks for."""
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestCiStatusResultInvariant.test_invalid_status_literal_raises  # noqa: E501
        import pydantic

        try:
            verify_release_ci_status.CiStatusResult(status="banana", detail="x")
        except pydantic.ValidationError as exc:
            assert "banana" in str(exc)
        else:
            raise AssertionError("expected a ValidationError for an invalid status")


class TestMain:
    """End-to-end through `main()`'s own CLI parsing, still with `gh`
    substituted -- `determine_ci_status`'s `run_gh=` seam is module-
    private, so this patches the module-level `_run_gh` the un-parameterised
    call path resolves through, matching how `release.yml`'s own step
    actually invokes this script."""

    def test_green_path_prints_green_and_exits_zero(self, monkeypatch) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestMain.test_green_path_prints_green_and_exits_zero  # noqa: E501
        payload = _runs_payload(status="completed", conclusion="success")
        monkeypatch.setattr(verify_release_ci_status, "_run_gh", _fake_gh(0, payload))
        code = verify_release_ci_status.main(
            ["--repo", _REPO, "--sha", _SHA, "--override", "false"]
        )
        assert code == 0

    def test_red_path_without_override_exits_nonzero(self, monkeypatch) -> None:
        # frob:tests tests/unit/test_verify_release_ci_status.py::TestMain.test_red_path_without_override_exits_nonzero  # noqa: E501
        payload = _runs_payload(status="completed", conclusion="failure")
        monkeypatch.setattr(verify_release_ci_status, "_run_gh", _fake_gh(0, payload))
        code = verify_release_ci_status.main(
            ["--repo", _REPO, "--sha", _SHA, "--override", "false"]
        )
        assert code == 1
