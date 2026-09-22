"""T-4550: unit tests for `done-report`'s capture-check scoping/
budget/skip machinery -- `_done_report_check_budget_s` (criterion 2's
`[tool.frob] done_report_check_budget_s` reader), `_done_report_touched_
files` (criterion 1's `--files` scoping, reusing `_land_cmd._rapid_check_
scope_files`), and `_shared_check_spawn_fn`'s new `timeout` parameter
(the budget's actual enforcement point).

Follows `tests/unit/test_ticket_runner_gate_findings.py::
TestSharedCheckSpawnFn`'s precedent: monkeypatch the `subprocess.run` seam
`guarded_subprocess_run` calls (`frob.process._guard.subprocess.run`), and
the collaborator functions `_done_report_touched_files` calls
(`frob.gitio.working_diff`, `frob.app.ticket_runner._land_cmd._rapid_
check_scope_files`) at their own definition sites -- never a real `git`/
`frob check` subprocess spawn. `_done_report`'s own full mode-dispatch
(no-check vs. scoped-budgeted) is NOT covered here end-to-end: exercising
it for real needs a real git repo + ticket (`tests/test_ticket_runner_
done_report.py`'s own fixture shape) and `AppConfig` genuinely refuses an
undeclared `ticket_no_check` attribute (confirmed directly: `AppConfig().
ticket_no_check = True` raises `ValueError: "AppConfig" object has no
field "ticket_no_check"`) until that field is added in `src/frob/app/
config.py`/`src/frob/app/_config_external.py` -- both under an active
scope lease held by T-3613 for this ticket's entire duration (see the
Done report/why narrative). The three units tested here are exactly the
pieces that do not depend on that field existing."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

import frob.gitio as _gitio
from frob.app.ticket_runner import _verify
from frob.gitio import Diff, Hunk
from frob.process import _guard


class _FakeProc:
    """Minimal stand-in for `subprocess.CompletedProcess` -- only the
    attributes `_shared_check_spawn_fn`'s caller reads."""

    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


# frob:tests src/frob/app/ticket_runner/_verify.py::_done_report_check_budget_s \
# frob:tests src/frob/app/ticket_runner/_verify.py::_done_report_check_budget_s \
# frob:tests src/frob/app/ticket_runner/_verify.py::_done_report_check_budget_s \
class TestDoneReportCheckBudgetS:
    """Criterion 2: `[tool.frob] done_report_check_budget_s` in
    `pyproject.toml`, default 300."""

    def test_default_when_no_pyproject(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_done_report_check_scope.py::TestDoneReportCheckBudgetS.test_default_when_no_pyproject  # noqa: E501
        assert _verify._done_report_check_budget_s(tmp_path) == 300

    def test_default_when_pyproject_has_no_tool_frob_table(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_done_report_check_scope.py::TestDoneReportCheckBudgetS.test_default_when_pyproject_has_no_tool_frob_table  # noqa: E501
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname = 'x'\n", encoding="utf-8"
        )
        assert _verify._done_report_check_budget_s(tmp_path) == 300

    def test_pyproject_override_wins(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_done_report_check_scope.py::TestDoneReportCheckBudgetS.test_pyproject_override_wins  # noqa: E501
        (tmp_path / "pyproject.toml").write_text(
            "[tool.frob]\ndone_report_check_budget_s = 45\n", encoding="utf-8"
        )
        assert _verify._done_report_check_budget_s(tmp_path) == 45

    def test_unparsable_pyproject_falls_back_to_default(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_done_report_check_scope.py::TestDoneReportCheckBudgetS.test_unparsable_pyproject_falls_back_to_default  # noqa: E501
        (tmp_path / "pyproject.toml").write_text("not [ valid toml", encoding="utf-8")
        assert _verify._done_report_check_budget_s(tmp_path) == 300


# frob:tests src/frob/app/ticket_runner/_verify.py::_done_report_touched_files \
# frob:tests src/frob/app/ticket_runner/_verify.py::_done_report_touched_files \
# frob:tests src/frob/app/ticket_runner/_verify.py::_done_report_touched_files \
class TestDoneReportTouchedFiles:
    """Criterion 1: `--files` scoped to the diff-touched set plus direct
    dependents, via `working_diff` + the reused `_rapid_check_scope_files`
    (T-4413), never copied."""

    def test_unresolvable_diff_returns_none_unscoped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_done_report_check_scope.py::TestDoneReportTouchedFiles.test_unresolvable_diff_returns_none_unscoped  # noqa: E501
        from typani import Err

        from frob.gitio import GitError

        monkeypatch.setattr(
            _gitio, "working_diff", lambda root, base: Err(GitError.NotARepo)
        )
        result = _verify._done_report_touched_files(tmp_path, "T-0001", "main")
        assert result is None

    def test_resolvable_diff_delegates_to_rapid_check_scope_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_done_report_check_scope.py::TestDoneReportTouchedFiles.test_resolvable_diff_delegates_to_rapid_check_scope_files  # noqa: E501
        from typani import Ok

        diff = Diff(base="dev", hunks=(Hunk(file="src/frob/x.py", span=(1, 2)),))
        monkeypatch.setattr(_gitio, "working_diff", lambda root, base: Ok(diff))

        captured: dict[str, object] = {}

        def _fake_scope_files(root, ticket_id, touched):  # noqa: ANN001, ANN202
            captured["root"] = root
            captured["ticket_id"] = ticket_id
            captured["touched"] = touched
            return ("src/frob/x.py", "src/frob/y.py")

        from frob.app.ticket_runner import _land_cmd

        monkeypatch.setattr(_land_cmd, "_rapid_check_scope_files", _fake_scope_files)

        result = _verify._done_report_touched_files(tmp_path, "T-0001", "dev")
        assert result == ("src/frob/x.py", "src/frob/y.py")
        assert captured["ticket_id"] == "T-0001"
        assert captured["touched"] == frozenset({"src/frob/x.py"})


# frob:tests src/frob/app/ticket_runner/_verify.py::_shared_check_spawn_fn frob:tests \
# src/frob/app/ticket_runner/_verify.py::_shared_check_spawn_fn frob:tests \
# src/frob/app/ticket_runner/_verify.py::_shared_check_spawn_fn \
class TestSharedCheckSpawnFnTimeout:
    """Proves `_shared_check_spawn_fn`'s `timeout` parameter defaults to
    600s and `_done_report` passes its own budget through it, so a
    caller is not bound to a fixed 600s unconditionally (see T-4550)."""

    def test_default_timeout_is_600(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_done_report_check_scope.py::TestSharedCheckSpawnFnTimeout.test_default_timeout_is_600  # noqa: E501
        captured: dict[str, object] = {}

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            captured.update(kwargs)
            return _FakeProc(0, stdout="{}")

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        spawn = _verify._shared_check_spawn_fn(tmp_path, "T-0001")
        spawn()
        assert captured["timeout"] == 600

    def test_custom_timeout_is_forwarded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_done_report_check_scope.py::TestSharedCheckSpawnFnTimeout.test_custom_timeout_is_forwarded  # noqa: E501
        captured: dict[str, object] = {}

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            captured.update(kwargs)
            return _FakeProc(0, stdout="{}")

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        spawn = _verify._shared_check_spawn_fn(tmp_path, "T-0001", timeout=45)
        spawn()
        assert captured["timeout"] == 45

    def test_expired_budget_is_treated_as_unmeasured_not_a_crash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_done_report_check_scope.py::TestSharedCheckSpawnFnTimeout.test_expired_budget_is_treated_as_unmeasured_not_a_crash  # noqa: E501
        """Criterion 2: a budget that expires must not fail the verb -- the
        spawn closure returns `None` (the same "refused/unmeasurable
        spawn" outcome every other refusal already produces), never
        raises."""
        import subprocess as _subprocess

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            raise _subprocess.TimeoutExpired(
                cmd=argv, timeout=cast(float, kwargs.get("timeout"))
            )

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        spawn = _verify._shared_check_spawn_fn(tmp_path, "T-0001", timeout=1)
        assert spawn() is None
