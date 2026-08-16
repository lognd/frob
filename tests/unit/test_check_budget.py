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


# frob:ticket T-2235
# frob:ticket T-2250
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

    # frob:ticket T-1703
    # frob:ticket T-2097
    def test_budget_json_stdout_is_pure_parsable_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        # frob:tests tests/unit/test_check_budget.py::TestRunBudgetedCheck.test_budget_json_stdout_is_pure_parsable_json  # noqa: E501
        """T-1703: `--budget SECONDS --json`'s stdout must be valid JSON
        end to end, no leading/trailing prose. Before this fix,
        `_run_budgeted_check`'s own progress `_log.info` lines (`"running
        N stage group(s)..."`, `"stage group %r done in %.1fs"`) printed
        UNCONDITIONALLY, ahead of the JSON payload `_report_check_result`
        emits -- `run`'s `quiet_stdout_logs` `--json` wrap only covers the
        setup calls AFTER `_handle_early_exit_modes` dispatches here, so
        those two lines corrupted every `--budget --json` caller's stdout
        (the live break: `_unscoped_error_findings`,
        `frob.app.ticket_runner._land_cmd`, spawns exactly this shape).
        A caller monkeypatching `--budget`'s own selection to defer one
        group proves the SAME contract holds even on a partial run.

        T-2097: asserted via `caplog`, not `capsys` -- T-1621 (landed after
        T-1703) makes `src/frob/logging/logger.py::_init` skip installing
        frob's own root stdout/stderr handlers under pytest entirely (to
        stop every record printing twice in pytest's own report), so a
        `--json` payload routed through `_log.info` (RENDER001) is only
        ever observable via `caplog` inside a test process -- the same
        `--json`-via-logger convention `TestGitlogRunner.
        test_json_mode_prints_json` and ~15 other tests already follow.
        Production is unaffected: outside pytest the payload still reaches
        real stdout (verified directly against this ticket's own repro,
        both via a real subprocess spawn and a bare in-process call)."""
        import json

        monkeypatch.setattr(check_mod, "available_stages", lambda: ["g1", "g2"])

        def _fake_run_all_stages(cfg, root, **kwargs):  # noqa: ANN001
            (group,) = cfg.check_only
            return self._fake_result(group)

        monkeypatch.setattr(check_runner_mod, "_run_all_stages", _fake_run_all_stages)
        check_chunking_mod._save_budget_timing(tmp_path, {"g1": 10.0})
        cfg = AppConfig(check_path=tmp_path, check_budget=15, check_json=True)
        caplog.set_level("INFO")
        check_run(cfg)
        data = next(
            json.loads(r.message)
            for r in caplog.records
            if r.message.strip().startswith("{")
        )
        assert data["results"][0]["tool"] == "g1"
        tool_names = [r["tool"] for r in data["results"]]
        assert "budget" in tool_names

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

    # frob:ticket T-2235
    def test_json_reports_universe_skip_despite_narrow_resume(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        """(MUST FAIL FIRST, T-2235 acceptance 1/2) Reproduces the measured
        incident: a resume file already trimmed to ONE stage group (from
        some earlier, unrelated invocation) means this run's own local
        `deferred` list is empty -- nothing left in `remaining` to defer --
        so the old code reported nothing skipped and exited clean, having
        silently never touched the other four groups. The `--json` payload
        must name every stage group `available_stages()` knows about that
        this call did not itself execute, not just `deferred`."""
        import json

        monkeypatch.setattr(
            check_mod, "available_stages", lambda: ["g1", "g2", "g3", "g4", "g5"]
        )

        def _fake_run_all_stages(cfg, root, **kwargs):  # noqa: ANN001
            (group,) = cfg.check_only
            return self._fake_result(group)

        monkeypatch.setattr(check_runner_mod, "_run_all_stages", _fake_run_all_stages)
        # Simulates a stale resume file left over from an unrelated earlier
        # invocation: only g5 is "remaining", even though the real universe
        # is 5 groups.
        check_chunking_mod._save_budget_remaining(tmp_path, ["g5"])
        cfg = AppConfig(check_path=tmp_path, check_budget=1000, check_json=True)
        caplog.set_level("INFO")
        check_run(cfg)

        data = next(
            json.loads(r.message)
            for r in caplog.records
            if r.message.strip().startswith("{")
        )
        assert data["budget"]["executed_groups"] == ["g5"]
        assert data["budget"]["skipped_groups"] == ["g1", "g2", "g3", "g4"]
        assert data["budget"]["complete"] is False
        # BUDGET001's own deferred-state note only fires for THIS call's
        # local deferred tail (empty here -- g5 fit the budget on its own)
        # -- the resume file is cleared, matching pre-existing behavior.
        assert not (tmp_path / ".frob" / "check-budget-state.json").exists()
        # And a human-readable WARNING is emitted regardless of --json.
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any("did NOT run this invocation" in r.message for r in warnings)
        assert any(
            all(g in r.message for g in ("g1", "g2", "g3", "g4")) for r in warnings
        )

    # frob:ticket T-2235
    def test_json_budget_key_absent_and_complete_when_everything_ran(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        """Acceptance 2: a run that DID execute everything reports that
        positively -- `skipped_groups` is an empty list (present, not
        absent) and `complete` is `True`."""
        import json

        monkeypatch.setattr(check_mod, "available_stages", lambda: ["g1", "g2"])
        monkeypatch.setattr(
            check_runner_mod,
            "_run_all_stages",
            lambda cfg, root, **kwargs: self._fake_result(cfg.check_only[0]),
        )
        cfg = AppConfig(check_path=tmp_path, check_budget=1000, check_json=True)
        caplog.set_level("INFO")
        check_run(cfg)

        data = next(
            json.loads(r.message)
            for r in caplog.records
            if r.message.strip().startswith("{")
        )
        assert data["budget"]["skipped_groups"] == []
        assert data["budget"]["complete"] is True

    # frob:ticket T-2235
    def test_unbudgeted_json_has_no_budget_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        """MUST-STILL-PASS control (acceptance 3): a plain, unbudgeted
        `frob check --json` never sees a `"budget"` key -- the field is
        strictly additive to the `--budget` path, never a reshape of the
        default JSON contract."""
        import json

        monkeypatch.setattr(
            check_runner_mod,
            "_run_all_stages",
            lambda cfg, root, **kwargs: self._fake_result("g1"),
        )
        cfg = AppConfig(check_path=tmp_path, check_json=True)
        caplog.set_level("INFO")
        check_run(cfg)

        data = next(
            json.loads(r.message)
            for r in caplog.records
            if r.message.strip().startswith("{")
        )
        assert "budget" not in data
        assert set(data.keys()) == {"path", "results"}

    # frob:ticket T-2250
    def test_only_scoped_budget_runs_exactly_the_named_group(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        """(MUST FAIL FIRST, T-2250 acceptance 1) `--only lint --budget N`
        must run `lint` and report it as executed, never silently run a
        DIFFERENT stage group and report `lint` as skipped. Reproduces the
        measured incident on `e02bf61b20be`: `--only lint --budget 120`
        used to execute `gates-fast` and report `lint` skipped."""
        import json

        monkeypatch.setattr(
            check_mod, "available_stages", lambda: ["gates-fast", "lint", "static"]
        )
        calls: list[str] = []

        def _fake_run_all_stages(cfg, root, **kwargs):  # noqa: ANN001
            (group,) = cfg.check_only
            calls.append(group)
            return self._fake_result(group)

        monkeypatch.setattr(check_runner_mod, "_run_all_stages", _fake_run_all_stages)
        cfg = AppConfig(
            check_path=tmp_path,
            check_budget=1000,
            check_json=True,
            check_only=["lint"],
        )
        caplog.set_level("INFO")
        check_run(cfg)

        assert calls == ["lint"]
        data = next(
            json.loads(r.message)
            for r in caplog.records
            if r.message.strip().startswith("{")
        )
        assert data["budget"]["executed_groups"] == ["lint"]
        assert data["budget"]["skipped_groups"] == []
        assert data["budget"]["complete"] is True
        tool_names = [r["tool"] for r in data["results"]]
        assert tool_names == ["lint"]

    # frob:ticket T-2250
    def test_only_scoped_budget_never_touches_shared_resume_state(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2250 acceptance 3: an `--only`-scoped budgeted run neither
        reads a pre-existing resume file nor writes one of its own -- a
        later UNRESTRICTED `--budget` call must never inherit an
        artificially narrow plan left behind by a scoped call."""
        monkeypatch.setattr(
            check_mod, "available_stages", lambda: ["gates-fast", "lint", "static"]
        )
        monkeypatch.setattr(
            check_runner_mod,
            "_run_all_stages",
            lambda cfg, root, **kwargs: self._fake_result(cfg.check_only[0]),
        )
        # Pre-seed timing so `lint` alone (budget too small for a second
        # group) genuinely defers something, exercising the persisted=False
        # path.
        check_chunking_mod._save_budget_timing(tmp_path, {"lint": 10.0})
        cfg = AppConfig(
            check_path=tmp_path,
            check_budget=1000,
            check_only=["lint"],
        )
        check_run(cfg)
        assert not (tmp_path / ".frob" / "check-budget-state.json").exists()

        # And a later unrestricted call is unaffected -- it still plans
        # over the full universe, not a scoped leftover.
        calls: list[str] = []

        def _fake_run_all_stages_2(cfg, root, **kwargs):  # noqa: ANN001
            (group,) = cfg.check_only
            calls.append(group)
            return self._fake_result(group)

        monkeypatch.setattr(check_runner_mod, "_run_all_stages", _fake_run_all_stages_2)
        cfg2 = AppConfig(check_path=tmp_path, check_budget=1000)
        check_run(cfg2)
        assert calls == ["gates-fast", "lint", "static"]

    # frob:ticket T-2250
    def test_only_budget_combo_refuses_a_bare_gate_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        """T-2250: `--only <bare-gate-name> --budget N` cannot be planned
        at stage-group granularity -- REFUSE loudly, naming the offending
        value, rather than silently discarding `--only` (the T-2235-class
        defect) or silently widening it to every group (the other
        forbidden fix)."""
        import json

        monkeypatch.setattr(
            check_mod, "available_stages", lambda: ["gates-fast", "lint", "static"]
        )
        called = []
        monkeypatch.setattr(
            check_runner_mod,
            "_run_all_stages",
            lambda cfg, root, **kwargs: (
                called.append(cfg.check_only) or self._fake_result("should-not-run")
            ),
        )
        cfg = AppConfig(
            check_path=tmp_path,
            check_budget=1000,
            check_json=True,
            check_only=["ruff"],
        )
        caplog.set_level("INFO")
        with pytest.raises(SystemExit) as excinfo:
            check_run(cfg)
        assert excinfo.value.code == 1

        assert called == []
        data = next(
            json.loads(r.message)
            for r in caplog.records
            if r.message.strip().startswith("{")
        )
        assert "budget" not in data
        messages = [d["message"] for r in data["results"] for d in r["diagnostics"]]
        assert any("ruff" in m and "stage-group" in m for m in messages)
        assert not (tmp_path / ".frob" / "check-budget-state.json").exists()


# frob:ticket T-2250
class TestResolveBudgetOnlyScope:
    """`_resolve_budget_only_scope`'s pure validation logic (T-2250)."""

    # frob:ticket T-2250
    def test_no_only_returns_none_unrestricted(self) -> None:
        """No `--only` given: `None` means "plan over the full universe",
        the unrestricted-run signal `_resolve_budget_remaining` checks."""
        result = check_chunking_mod._resolve_budget_only_scope(None, ["lint", "static"])
        assert result is None

    # frob:ticket T-2250
    def test_recognized_group_returns_it_verbatim(self) -> None:
        """A recognized stage-group alias round-trips as the exact
        ordered scope to plan over."""
        result = check_chunking_mod._resolve_budget_only_scope(
            ["lint"], ["lint", "static", "gates-fast"]
        )
        assert result == ["lint"]

    # frob:ticket T-2250
    def test_bare_gate_name_raises_unplannable(self) -> None:
        """A name that is not itself a whole stage-group alias (a bare
        gate/tool name) raises, naming the offending value -- the budget
        path cannot plan below stage-group granularity."""
        with pytest.raises(check_chunking_mod._BudgetOnlyUnplannable) as excinfo:
            check_chunking_mod._resolve_budget_only_scope(["ruff"], ["lint", "static"])
        assert excinfo.value.unknown == ["ruff"]


# frob:ticket T-2235
class TestBudgetCoverageReport:
    """`_budget_coverage_report`'s pure dict-building logic (T-2235)."""

    # frob:ticket T-2235
    def test_skipped_is_universe_minus_executed(self) -> None:
        """The reported `skipped_groups` reflects `all_groups - executed`,
        not any notion of a local `deferred` list -- this is what makes
        the report honest even when the caller's own `remaining`/`deferred`
        bookkeeping was already narrowed by stale resume state before this
        function ever sees it."""
        report = check_chunking_mod._budget_coverage_report(
            480, ["g1", "g2", "g3", "g4", "g5"], ["g5"]
        )
        assert report["requested_seconds"] == 480
        assert report["executed_groups"] == ["g5"]
        assert report["skipped_groups"] == ["g1", "g2", "g3", "g4"]
        assert report["complete"] is False

    # frob:ticket T-2235
    def test_empty_skipped_present_not_absent(self) -> None:
        """Executing every group in the universe yields an empty (but
        present) `skipped_groups` list and `complete=True`."""
        report = check_chunking_mod._budget_coverage_report(
            480, ["g1", "g2"], ["g1", "g2"]
        )
        assert report["skipped_groups"] == []
        assert report["complete"] is True
