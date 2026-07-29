"""`frob check --budget SECONDS` (T-1004): budget selection math, resume
continuation, and defer reporting.

Mirrors the mocking style `tests/unit/test_app_runners_batch6.py`'s
`TestCheckRunner` already uses for `--stamp-baseline`'s T-0751 chunk
machinery -- `_run_budgeted_check` is this ticket's sibling mechanism (same
chunk-state-on-disk pattern, generalized from gate-only chunks to whole
`--only` stage groups and a time budget instead of an explicit `--only`
value).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import frob.app._check_chunking as check_chunking_mod
import frob.app.check_runner as check_runner_mod
import frob.check as check_mod
from frob.app.check_runner import run as check_run
from frob.app.config import AppConfig
from frob.check import CheckResult
from frob.process.parsers.common import Diagnostic, ToolResult


class TestSelectBudgetChunks:
    """`_select_budget_chunks`'s pure greedy-packing math."""

    def test_greedy_pack_fits_under_budget(self) -> None:
        """Groups are added while the running total (with the next group
        included) still fits the budget; the first group that would push
        the total over is deferred instead."""
        remaining = ["a", "b", "c"]
        timing = {"a": 30.0, "b": 40.0, "c": 50.0}
        selected, deferred = check_chunking_mod._select_budget_chunks(
            remaining, timing, 80
        )
        assert selected == ["a", "b"]
        assert deferred == ["c"]

    def test_first_stage_always_selected_even_if_over_budget(self) -> None:
        """A budget too small for even the first group's estimate still
        selects that one group -- forward progress beats a zero-work run."""
        remaining = ["a", "b"]
        timing = {"a": 200.0}
        selected, deferred = check_chunking_mod._select_budget_chunks(
            remaining, timing, 10
        )
        assert selected == ["a"]
        assert deferred == ["b"]

    def test_unmeasured_group_uses_default_estimate(self) -> None:
        """A group with no timing history yet falls back to
        `_BUDGET_DEFAULT_ESTIMATE_S`, not zero (which would silently
        over-pack an unmeasured group as free)."""
        remaining = ["unmeasured"]
        selected, deferred = check_chunking_mod._select_budget_chunks(
            remaining, {}, int(check_chunking_mod._BUDGET_DEFAULT_ESTIMATE_S) + 10
        )
        assert selected == ["unmeasured"]
        assert deferred == []

    def test_empty_remaining_selects_nothing(self) -> None:
        """No stage groups left to consider -- selects and defers nothing."""
        selected, deferred = check_chunking_mod._select_budget_chunks([], {}, 100)
        assert selected == []
        assert deferred == []


class TestUpdateBudgetTiming:
    """`_update_budget_timing`'s rolling EMA."""

    def test_first_measurement_seeds_estimate_directly(self) -> None:
        """No prior estimate: the fresh measurement becomes the estimate
        outright (no averaging against nothing)."""
        updated = check_chunking_mod._update_budget_timing({}, "g", 42.0)
        assert updated["g"] == 42.0

    def test_later_measurement_blends_with_prior(self) -> None:
        """A second measurement blends with the prior estimate via the EMA
        weight, landing strictly between the two raw values."""
        updated = check_chunking_mod._update_budget_timing({"g": 100.0}, "g", 50.0)
        assert 50.0 < updated["g"] < 100.0

    def test_does_not_mutate_input_dict(self) -> None:
        """Returns a new dict -- the caller's own accumulator stays valid
        for comparison/logging against the pre-update state."""
        original = {"g": 10.0}
        check_chunking_mod._update_budget_timing(original, "g", 20.0)
        assert original == {"g": 10.0}


class TestRunBudgetedCheck:
    """`run(cfg)` with `check_budget` set -- the full self-select/run/
    persist/report loop, with `available_stages`/`_run_all_stages` faked so
    the test controls exactly what a "stage group" costs and produces."""

    def _fake_result(self, group: str) -> CheckResult:
        return CheckResult(
            path=".",
            results=[ToolResult(tool=group, exit_code=0, summary=f"{group} ok")],
        )

    def test_runs_selected_chunks_and_reports_result(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        """Both groups fit the budget: both run, both tool results show up
        in the final report, and no BUDGET001 deferral note is emitted."""
        monkeypatch.setattr(check_mod, "available_stages", lambda: ["g1", "g2"])
        calls: list[str] = []

        def _fake_run_all_stages(cfg, root, **kwargs):  # noqa: ANN001
            (group,) = cfg.check_only
            calls.append(group)
            return self._fake_result(group)

        monkeypatch.setattr(check_runner_mod, "_run_all_stages", _fake_run_all_stages)
        cfg = AppConfig(check_path=tmp_path, check_budget=1000)
        with caplog.at_level("INFO"):
            check_run(cfg)
        assert calls == ["g1", "g2"]
        assert "BUDGET001" not in caplog.text
        assert not (tmp_path / ".frob" / "check-budget-state.json").exists()

    def test_persists_resume_state_for_deferred_groups(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog, capsys
    ) -> None:
        """A budget that only fits the first group defers the second one,
        reports it LOUDLY (BUDGET001, never a silent drop), and persists it
        to the resume-state file."""
        monkeypatch.setattr(check_mod, "available_stages", lambda: ["g1", "g2"])
        calls: list[str] = []

        def _fake_run_all_stages(cfg, root, **kwargs):  # noqa: ANN001
            (group,) = cfg.check_only
            calls.append(group)
            return self._fake_result(group)

        monkeypatch.setattr(check_runner_mod, "_run_all_stages", _fake_run_all_stages)
        # Pre-seed timing so selection math is deterministic: g1 costs 10s,
        # a 15s budget cannot also fit g2's unmeasured 90s default.
        check_chunking_mod._save_budget_timing(tmp_path, {"g1": 10.0})
        cfg = AppConfig(check_path=tmp_path, check_budget=15)
        with caplog.at_level("INFO"):
            check_run(cfg)
        assert calls == ["g1"]
        report_text = capsys.readouterr().out
        assert "BUDGET001" in report_text
        assert "g2" in report_text
        state_path = tmp_path / ".frob" / "check-budget-state.json"
        assert state_path.exists()
        import json

        assert json.loads(state_path.read_text()) == ["g2"]

    def test_resumes_from_prior_remaining_state(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A prior run's resume state (only `g2` left) means THIS run only
        runs `g2`, not `g1` again -- continuation, not a restart."""
        monkeypatch.setattr(check_mod, "available_stages", lambda: ["g1", "g2"])
        calls: list[str] = []

        def _fake_run_all_stages(cfg, root, **kwargs):  # noqa: ANN001
            (group,) = cfg.check_only
            calls.append(group)
            return self._fake_result(group)

        monkeypatch.setattr(check_runner_mod, "_run_all_stages", _fake_run_all_stages)
        check_chunking_mod._save_budget_remaining(tmp_path, ["g2"])
        cfg = AppConfig(check_path=tmp_path, check_budget=1000)
        check_run(cfg)
        assert calls == ["g2"]

    def test_clears_resume_state_once_every_group_has_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Once a budgeted run's selection covers every remaining group
        (nothing deferred), the resume-state file is removed -- a
        subsequent `--budget` run starts a fresh full pass, not an empty
        continuation."""
        monkeypatch.setattr(check_mod, "available_stages", lambda: ["g1", "g2"])
        monkeypatch.setattr(
            check_runner_mod,
            "_run_all_stages",
            lambda cfg, root, **kwargs: self._fake_result(cfg.check_only[0]),
        )
        check_chunking_mod._save_budget_remaining(tmp_path, ["g2"])
        cfg = AppConfig(check_path=tmp_path, check_budget=1000)
        check_run(cfg)
        assert not (tmp_path / ".frob" / "check-budget-state.json").exists()

    def test_stale_remaining_group_is_dropped_and_falls_back_to_full_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A resume file naming a group `available_stages()` no longer
        recognizes (renamed/removed) is not run as-is; every stage group
        gets reconsidered from scratch instead of erroring or hanging on
        a dead name."""
        monkeypatch.setattr(check_mod, "available_stages", lambda: ["g1", "g2"])
        calls: list[str] = []

        def _fake_run_all_stages(cfg, root, **kwargs):  # noqa: ANN001
            (group,) = cfg.check_only
            calls.append(group)
            return self._fake_result(group)

        monkeypatch.setattr(check_runner_mod, "_run_all_stages", _fake_run_all_stages)
        check_chunking_mod._save_budget_remaining(tmp_path, ["stale-group"])
        cfg = AppConfig(check_path=tmp_path, check_budget=1000)
        check_run(cfg)
        assert calls == ["g1", "g2"]

    def test_budget_deferred_result_names_every_deferred_group(self) -> None:
        """`_budget_deferred_result`'s diagnostic message names every
        deferred group verbatim -- a coordinator reading it can tell
        exactly what's outstanding without cross-referencing state files."""
        result = check_chunking_mod._budget_deferred_result(
            ["gates-native", "static"], 60
        )
        assert result.tool == "budget"
        assert result.exit_code == 0
        diag: Diagnostic = result.diagnostics[0]
        assert diag.severity == "warning"
        assert diag.code == "BUDGET001"
        assert "gates-native" in diag.message
        assert "static" in diag.message
