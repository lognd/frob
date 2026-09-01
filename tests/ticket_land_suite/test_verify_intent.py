import json
from pathlib import Path
from typing import Any

import pytest
from typani.result import Err, Ok, Result

import frob.tickets._land as _land_mod
from frob.gitio import GitError, ProcResult

pytestmark = pytest.mark.heavy_subprocess

# frob:ticket T-2450
class TestUnscopedErrorFindingsPublicSeam:
    """T-2450: `unscoped_error_findings` is a thin public wrapper around
    `_unscoped_error_findings` -- the cross-node seam `frob.verify.
    _worker`'s `_default_verify_fn` imports instead of reaching across
    the node boundary to call the private name directly."""

    # frob:ticket T-2450
    # frob:tests tests/ticket_land_suite/test_verify_intent.py::TestUnscopedErrorFindingsPublicSeam.test_delegates_with_the_same_arguments  # noqa: E501
    def test_delegates_with_the_same_arguments(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.app.ticket_runner import _land_cmd

        seen: dict[str, Any] = {}

        def _fake(
            root: Path,
            ticket_id: str,
            *,
            budget: int | None = None,
            env: dict[str, str] | None = None,
            full: bool = False,
        ) -> frozenset[tuple[str, str]] | None:
            seen["args"] = (root, ticket_id, budget, env, full)
            return frozenset()

        monkeypatch.setattr(_land_cmd, "_unscoped_error_findings", _fake)
        result = _land_cmd.unscoped_error_findings(tmp_path, "T-0001", full=True)

        assert result == frozenset()
        assert seen["args"] == (tmp_path, "T-0001", None, None, True)




class TestUnscopedErrorFindingsExcludesNoTicketNoise:
    """T-1804: `_unscoped_error_findings` -- the shared spawn both
    the deferred post-land sweep and `--land-parity` use -- must exclude
    PRE001/SCOPE001 from its returned finding-identity set. Both rules
    fire unconditionally under `_no_active_ticket_violation` (B9,
    `frob.gates.__init__`) whenever this deliberately-no-`--ticket` spawn
    sees ANY non-empty diff with no derivable ticket -- a hygiene signal
    about root's git state at measurement time (commonly a concurrent
    land's transient dirt on the shared checkout), never a code
    regression either caller exists to catch. Measured 2026-08-07: five
    sweep-filed regression tickets in one hour whose only findings were
    these two."""

    @staticmethod
    def _json_payload(findings: list[tuple[str, str]]) -> str:
        """A minimal `frob check --json` payload shape
        (`_parse_check_json`/`_parse_error_findings_from_json`'s own
        contract: a `"results"` list of `{"tool", "diagnostics"}` dicts,
        each diagnostic an error-severity `{"code", "file", "severity"}`)
        with one ToolResult carrying exactly `findings`."""
        return json.dumps(
            {
                "results": [
                    {
                        "tool": "gate-summary",
                        "diagnostics": [
                            {"code": rule, "file": file, "severity": "error"}
                            for rule, file in findings
                        ],
                    }
                ]
            }
        )

    def test_pre001_and_scope001_are_excluded_but_real_findings_survive(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_verify_intent.py::TestUnscopedErrorFindingsExclu\
        # desNoTicketNoise.test_pre001_and_scope001_are_excluded_but_real_findings_surv\
        # ive
        from frob.app import ticket_runner

        payload = self._json_payload(
            [
                ("PRE001", "tickets/T-0001"),
                ("SCOPE001", "some/file.py"),
                ("DEAD001", "src/frob/real_module.py"),
            ]
        )

        def _fake(argv: list[str], **k: Any) -> Result[ProcResult, Any]:
            return Ok(
                ProcResult(argv=tuple(argv), returncode=1, stdout=payload, stderr="")
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        from frob.app.ticket_runner._land_cmd import _unscoped_error_findings

        result = _unscoped_error_findings(tmp_path, "T-0001")

        assert result == frozenset({("DEAD001", "src/frob/real_module.py")})

    def test_only_no_ticket_noise_present_returns_empty_not_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_verify_intent.py::TestUnscopedErrorFindingsExclu\
        # desNoTicketNoise.test_only_no_ticket_noise_present_returns_empty_not_none
        """A run whose ONLY findings are PRE001/SCOPE001 -- exactly the
        five-tickets-in-an-hour incident -- must read as a real, measured
        EMPTY set (clean), never `None` (unmeasurable): the whole point is
        that the sweep stops comparing this noise against its baseline at
        all, not that it falls back to skipping the comparison."""
        from frob.app import ticket_runner

        payload = self._json_payload(
            [("PRE001", "tickets/T-0001"), ("SCOPE001", "some/file.py")]
        )

        def _fake(argv: list[str], **k: Any) -> Result[ProcResult, Any]:
            return Ok(
                ProcResult(argv=tuple(argv), returncode=1, stdout=payload, stderr="")
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        from frob.app.ticket_runner._land_cmd import _unscoped_error_findings

        result = _unscoped_error_findings(tmp_path, "T-0001")

        assert result == frozenset()



class TestUnscopedErrorFindingsFullMode:
    """T-3001: `full=True` drops `--budget` entirely and sets
    `FROB_ALLOW_FULL_CHECK=1` -- the fix for the vicious cycle where a
    `--budget` ceiling derived from a contention-inflated sample window
    truncated the verify drain's own check, which is `Unmeasurable`
    (T-1703) and can never advance the watermark."""

    def test_full_mode_omits_budget_flag_and_sets_allow_full_check_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_verify_intent.py::TestUnscopedErrorFindingsFullM\
        # ode.test_full_mode_omits_budget_flag_and_sets_allow_full_check_env
        from frob.app import ticket_runner

        captured: dict[str, Any] = {}

        def _fake(argv: list[str], **k: Any) -> Result[ProcResult, Any]:
            captured["argv"] = list(argv)
            captured["env"] = k.get("env")
            captured["timeout"] = k.get("timeout")
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=0,
                    stdout=self._json_payload_ok(),
                    stderr="",
                )
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        from frob.app.ticket_runner._land_cmd import (
            _FULL_CHECK_TIMEOUT_S,
            _unscoped_error_findings,
        )

        result = _unscoped_error_findings(tmp_path, "T-0001", full=True)

        assert result == frozenset()
        assert "--budget" not in captured["argv"]
        assert captured["env"]["FROB_ALLOW_FULL_CHECK"] == "1"
        assert captured["timeout"] == _FULL_CHECK_TIMEOUT_S

    @staticmethod
    def _json_payload_ok() -> str:
        """An empty-but-measured `frob check --json` payload -- no
        findings, no `BUDGET001` deferral marker."""
        return json.dumps({"results": [{"tool": "gate-summary", "diagnostics": []}]})

    def test_full_mode_default_is_false_preserves_prior_budgeted_behavior(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_verify_intent.py::TestUnscopedErrorFindingsFullM\
        # ode.test_full_mode_default_is_false_preserves_prior_budgeted_behavior
        from frob.app import ticket_runner

        captured: dict[str, Any] = {}

        def _fake(argv: list[str], **k: Any) -> Result[ProcResult, Any]:
            captured["argv"] = list(argv)
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=0,
                    stdout=self._json_payload_ok(),
                    stderr="",
                )
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        from frob.app.ticket_runner._land_cmd import _unscoped_error_findings

        _unscoped_error_findings(tmp_path, "T-0001")

        assert "--budget" in captured["argv"]



class TestUnscopedErrorFindingsRecordsBudgetDeferral:
    """T-2456: a `--budget`-truncated `_unscoped_error_findings` call must
    not just return `None` (T-1703's existing unmeasurable contract,
    unchanged) -- it must ALSO record which stage group(s) were deferred
    into `_LAST_BUDGET_DEFERRALS` so `_print_land_proof` can name them on
    the `LAND-PROOF:` line instead of the fact being reachable only via a
    `_log.warning` line a human has to already be tailing to see."""

    @staticmethod
    def _budget_truncated_payload(deferred: str) -> str:
        """A minimal `frob check --json --budget` payload carrying one
        `BUDGET001` diagnostic naming `deferred` -- the exact shape
        `_budget_deferred_stage_groups`/`_budget_deferred_groups_from_
        stdout` parse."""
        return json.dumps(
            {
                "results": [
                    {
                        "tool": "budget",
                        "diagnostics": [
                            {
                                "file": None,
                                "line": None,
                                "col": None,
                                "severity": "warning",
                                "code": "BUDGET001",
                                "message": (
                                    f"BUDGET001: --budget 480 deferred 1 stage "
                                    f"group(s) to a later run: {deferred}. "
                                    "Resume state persisted -- run `frob check "
                                    "--budget <seconds>` again to continue."
                                ),
                            }
                        ],
                    }
                ]
            }
        )

    # frob:ticket T-2456
    def test_budget_truncated_run_records_deferred_groups(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_verify_intent.py::TestUnscopedErrorFindingsRecor\
        # dsBudgetDeferral.test_budget_truncated_run_records_deferred_groups
        from frob.app import ticket_runner
        from frob.app.ticket_runner import _land_cmd

        payload = self._budget_truncated_payload("static")

        def _fake(argv: list[str], **k: Any) -> Result[ProcResult, Any]:
            return Ok(
                ProcResult(argv=tuple(argv), returncode=0, stdout=payload, stderr="")
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        _land_cmd._LAST_BUDGET_DEFERRALS.pop("T-9999", None)

        result = _land_cmd._unscoped_error_findings(tmp_path, "T-9999")

        assert result is None
        assert _land_cmd._LAST_BUDGET_DEFERRALS.get("T-9999") == ("static",)

    # frob:ticket T-2456
    def test_clean_run_records_no_deferral(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_verify_intent.py::TestUnscopedErrorFindingsRecor\
        # dsBudgetDeferral.test_clean_run_records_no_deferral
        """The must-still-land positive control at this layer: a run with
        no `BUDGET001` deferral at all leaves `_LAST_BUDGET_DEFERRALS`
        untouched for this ticket id."""
        from frob.app import ticket_runner
        from frob.app.ticket_runner import _land_cmd

        payload = json.dumps({"results": [{"tool": "gate-summary", "diagnostics": []}]})

        def _fake(argv: list[str], **k: Any) -> Result[ProcResult, Any]:
            return Ok(
                ProcResult(argv=tuple(argv), returncode=0, stdout=payload, stderr="")
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        _land_cmd._LAST_BUDGET_DEFERRALS.pop("T-9998", None)

        result = _land_cmd._unscoped_error_findings(tmp_path, "T-9998")

        assert result == frozenset()
        assert "T-9998" not in _land_cmd._LAST_BUDGET_DEFERRALS



class TestPrintLandProofSurfacesBudgetDeferred:
    """T-2456: `_print_land_proof`'s `budget_deferred=` field is the
    minimum-bar fix this ticket exists for -- a land whose post-land
    sweep was budget-truncated must not present as indistinguishable
    from a land whose sweep ran clean. `verified=` itself is UNCHANGED
    (must-still-land: this is surfacing, never a new refusal)."""

    @staticmethod
    def _stub_land_proof_checks(monkeypatch: pytest.MonkeyPatch) -> None:
        from frob.app.ticket_runner import _land_cmd

        monkeypatch.setattr(
            _land_cmd,
            "_land_proof_checks",
            lambda root, final_id, commit_sha: (True, "done", True),
        )

    # frob:ticket T-2456
    def test_deferred_groups_named_on_the_land_proof_line(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_verify_intent.py::TestPrintLandProofSurfacesBudg\
        # etDeferred.test_deferred_groups_named_on_the_land_proof_line
        import logging

        from frob.app.ticket_runner import _land_cmd
        from frob.tickets._models import LandReport

        self._stub_land_proof_checks(monkeypatch)
        _land_cmd._LAST_BUDGET_DEFERRALS["T-9997"] = ("static", "lint")
        report = LandReport(
            ticket_id="T-9997",
            final_id="T-9997",
            dry_run=False,
            wip_committed=True,
            merged_main_into_worktree=True,
            ledger_spliced=False,
            commit_sha="deadbeef",
        )

        with caplog.at_level(logging.INFO):
            verified = _land_cmd._print_land_proof(tmp_path, report)

        assert verified is True
        assert "T-9997" not in _land_cmd._LAST_BUDGET_DEFERRALS
        [line] = [r.message for r in caplog.records if "LAND-PROOF:" in r.message]
        assert "budget_deferred=static,lint" in line
        assert "verified=True" in line

    # frob:ticket T-2456
    def test_no_deferral_reports_none_not_absent(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_verify_intent.py::TestPrintLandProofSurfacesBudg\
        # etDeferred.test_no_deferral_reports_none_not_absent
        """The must-still-land positive control: a land whose sweep ran
        clean prints `budget_deferred=none` -- present and explicit,
        never a silently-omitted field a human could mistake for
        unmeasured."""
        import logging

        from frob.app.ticket_runner import _land_cmd
        from frob.tickets._models import LandReport

        self._stub_land_proof_checks(monkeypatch)
        _land_cmd._LAST_BUDGET_DEFERRALS.pop("T-9996", None)
        report = LandReport(
            ticket_id="T-9996",
            final_id="T-9996",
            dry_run=False,
            wip_committed=True,
            merged_main_into_worktree=True,
            ledger_spliced=False,
            commit_sha="deadbeef",
        )

        with caplog.at_level(logging.INFO):
            _land_cmd._print_land_proof(tmp_path, report)

        [line] = [r.message for r in caplog.records if "LAND-PROOF:" in r.message]
        assert "budget_deferred=none" in line


# frob:ticket T-1736
class TestTouchedSymrefsForIntent:
    """`_touched_symrefs_for_intent`'s own span-overlap contract, tested
    directly -- the pure-function half of `_record_verify_intent_for_
    landed_commit`."""

    # frob:ticket T-1736
    def test_overlapping_hunk_matches_the_symbol(self) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_intent.py::TestTouchedSymrefsForIntent.test_overlapping_hunk_matches_the_symbol  # noqa: E501
        from frob.gitio import Diff, Hunk
        from frob.graph import Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind

        diff = Diff(base="deadbeef", hunks=(Hunk(file="a.py", span=(3, 5)),))
        snapshot = GraphSnapshot(
            root="/repo",
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 10),
                )
            },
            edges=(),
        )
        touched = _land_mod._touched_symrefs_for_intent(diff, snapshot)
        assert touched == {"a.py::fn"}

    # frob:ticket T-1736
    def test_non_overlapping_hunk_matches_nothing(self) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_intent.py::TestTouchedSymrefsForIntent.test_non_overlapping_hunk_matches_nothing  # noqa: E501
        from frob.gitio import Diff, Hunk
        from frob.graph import Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind

        diff = Diff(base="deadbeef", hunks=(Hunk(file="a.py", span=(50, 55)),))
        snapshot = GraphSnapshot(
            root="/repo",
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 10),
                )
            },
            edges=(),
        )
        touched = _land_mod._touched_symrefs_for_intent(diff, snapshot)
        assert touched == set()

    # frob:ticket T-1736
    def test_different_file_matches_nothing(self) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_intent.py::TestTouchedSymrefsForIntent.test_different_file_matches_nothing  # noqa: E501
        from frob.gitio import Diff, Hunk
        from frob.graph import Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind

        diff = Diff(base="deadbeef", hunks=(Hunk(file="b.py", span=(1, 10)),))
        snapshot = GraphSnapshot(
            root="/repo",
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 10),
                )
            },
            edges=(),
        )
        touched = _land_mod._touched_symrefs_for_intent(diff, snapshot)
        assert touched == set()



# frob:ticket T-1736
class TestRecordVerifyIntentForLandedCommit:
    """T-1736: the T-1686 epic's missing enqueue side -- `_land_locked`
    calls this once, after a real squash-apply success, so the coalescing
    verify worker (T-1688) ever has anything to drain."""

    # frob:ticket T-1736
    def _report(self, *, dry_run: bool = False, commit_sha: str | None = "c1"):
        from frob.tickets._models import LandReport

        return LandReport(
            ticket_id="T-9000",
            final_id="T-9000",
            dry_run=dry_run,
            wip_committed=True,
            merged_main_into_worktree=False,
            ledger_spliced=False,
            commit_sha=commit_sha,
        )

    # frob:ticket T-1736
    def test_dry_run_is_a_noop(self, tmp_path: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_intent.py::TestRecordVerifyIntentForLandedCommit.test_dry_run_is_a_noop  # noqa: E501
        from frob.verify import queue_status

        _land_mod._record_verify_intent_for_landed_commit(
            tmp_path, "T-9000", self._report(dry_run=True), "deadbeef"
        )
        assert queue_status(tmp_path).danger_ok == ()

    # frob:ticket T-1736
    def test_real_land_records_an_intent_entry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_intent.py::TestRecordVerifyIntentForLandedCommit.test_real_land_records_an_intent_entry  # noqa: E501
        from frob.gitio import Diff, Hunk
        from frob.graph import Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import queue_status

        diff = Diff(base="deadbeef", hunks=(Hunk(file="a.py", span=(1, 3)),))
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        monkeypatch.setattr("frob.gitio.working_diff", lambda root, base: Ok(diff))
        monkeypatch.setattr("frob.graph.load_graph", lambda cache: Ok(snapshot))

        _land_mod._record_verify_intent_for_landed_commit(
            tmp_path, "T-9000", self._report(commit_sha="c1"), "deadbeef"
        )

        queue = queue_status(tmp_path)
        assert queue.is_ok
        assert len(queue.danger_ok) == 1
        entry = queue.danger_ok[0]
        assert entry.commit_sha == "c1"
        assert entry.ticket_id == "T-9000"
        assert entry.touched_symbols == ("a.py::fn",)

    # frob:ticket T-1736
    def test_no_resolvable_symbols_records_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_intent.py::TestRecordVerifyIntentForLandedCommit.test_no_resolvable_symbols_records_nothing  # noqa: E501
        from frob.gitio import Diff
        from frob.graph import GraphSnapshot
        from frob.verify import queue_status

        diff = Diff(base="deadbeef", hunks=())
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        monkeypatch.setattr("frob.gitio.working_diff", lambda root, base: Ok(diff))
        monkeypatch.setattr("frob.graph.load_graph", lambda cache: Ok(snapshot))

        _land_mod._record_verify_intent_for_landed_commit(
            tmp_path, "T-9000", self._report(commit_sha="c1"), "deadbeef"
        )
        assert queue_status(tmp_path).danger_ok == ()

    # frob:ticket T-1736
    def test_diff_failure_is_logged_not_raised(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_intent.py::TestRecordVerifyIntentForLandedCommit.test_diff_failure_is_logged_not_raised  # noqa: E501
        from frob.verify import queue_status

        monkeypatch.setattr(
            "frob.gitio.working_diff", lambda root, base: Err(GitError.GitFailed)
        )

        # Must not raise -- a land that already succeeded is never failed
        # by this best-effort bookkeeping step.
        _land_mod._record_verify_intent_for_landed_commit(
            tmp_path, "T-9000", self._report(commit_sha="c1"), "deadbeef"
        )
        assert queue_status(tmp_path).danger_ok == ()
