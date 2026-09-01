"""Deferred-sweep run/spawn and detached-env tests for `frob.app.ticket_runner._rapid_sweep`
(T-3595 split of the former tests/unit/test_rapid_sweep.py)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import cast

import pytest

from frob.app.ticket_runner import _rapid_sweep
from frob.app.ticket_runner._rapid_sweep import (
    RapidSweepError,
    _check_claim_divergence_post_land,
    _read_baseline,
    _write_baseline,
    run_deferred_post_land_sweep,
    spawn_deferred_post_land_sweep,
)


class TestDeferredSweepRun:
    """`run_deferred_post_land_sweep` files, never reverts."""

    @pytest.fixture
    def _no_debt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`record_rapid_debt` shells out to git; a tmp_path is not a repo."""
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt", lambda *a, **k: None
        )

    def test_unmeasurable_check_leaves_the_baseline_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_unmeasurable_check_leaves_the_baseline_untouched  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: None,
        )
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_err
        assert result.danger_err is RapidSweepError.Unmeasurable
        assert _read_baseline(tmp_path) == frozenset({("COV003", "a.py")})

    def test_first_sweep_records_a_baseline_and_files_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_first_sweep_records_a_baseline_and_files_nothing  # noqa: E501
        fresh = frozenset({("COV003", "a.py")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        filed: list[object] = []
        monkeypatch.setattr(
            _rapid_sweep, "_file_regression_ticket", lambda *a: filed.append(a)
        )
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        assert result.danger_ok is None
        assert filed == []
        assert _read_baseline(tmp_path) == fresh

    def test_no_new_findings_is_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_no_new_findings_is_clean  # noqa: E501
        existing = frozenset({("COV003", "a.py")})
        _write_baseline(tmp_path, existing, "old")
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: existing,
        )
        filed: list[object] = []
        monkeypatch.setattr(
            _rapid_sweep, "_file_regression_ticket", lambda *a: filed.append(a)
        )
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        assert result.danger_ok is None
        assert filed == []

    def test_new_findings_file_a_ticket_and_rebaseline(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_new_findings_file_a_ticket_and_rebaseline  # noqa: E501
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        fresh = frozenset({("COV003", "a.py"), ("DOC011", "b.md")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        seen: list[frozenset[tuple[str, str]]] = []

        def _fake_file(root, final_id, commit, new_findings):  # noqa: ANN001, ANN202
            seen.append(new_findings)
            return "T-9999"

        monkeypatch.setattr(_rapid_sweep, "_file_regression_ticket", _fake_file)
        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")
        assert result.is_ok
        assert result.danger_ok == "T-9999"
        assert seen == [frozenset({("DOC011", "b.md")})]
        # Rebaselined even though the sweep was red: an already-filed
        # error must not be re-filed by the next land.
        assert _read_baseline(tmp_path) == fresh

    # frob:ticket T-2929
    def test_stale_baseline_refuses_to_file_and_records_debt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2929 must-fire case: `frob.verify.rapid_soft_warning` firing
        (a stale verification-queue window) means a NEW finding is NOT
        filed as a confident regression ticket -- the sweep refuses and
        records the refusal as a distinct, durable debt kind instead."""
        # frob:tests \
        # tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_stale_baseline_refuses_to_file_and_records_debt  # noqa: E501
        # frob:waive FMT001 reason="single-line frob:tests directive naming a long \
        # test node id -- already at frob fmt's own canonical form (verified: `frob \
        # fmt` reports it unchanged), same unwrappable shape as \
        # src/frob/app/_json_guard.py's existing FMT001 waivers"
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        fresh = frozenset({("COV003", "a.py"), ("DOC006", "tickets/T-0002/ticket.md")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        monkeypatch.setattr(
            "frob.verify.rapid_soft_warning",
            lambda root: (
                "rapid profile verification debt is stale: 53 commits "
                "since watermark (warn threshold 5)"
            ),
        )
        filed: list[object] = []
        monkeypatch.setattr(
            _rapid_sweep, "_file_regression_ticket", lambda *a, **k: filed.append(a)
        )
        debts: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt",
            lambda root, tid, what: debts.append((tid, what)),
        )
        monkeypatch.setattr(_rapid_sweep, "_commit_rapid_debt", lambda root, tid: None)

        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")

        assert result.is_ok
        assert result.danger_ok is None
        assert filed == []
        # T-2938: the deferred claim-divergence check reuses this SAME
        # staleness policy (`frob.verify.rapid_soft_warning`) independently
        # of the new-findings filing path above, and records the SAME debt
        # reason when it refuses too -- two refusals, one shared reason,
        # not a second policy.
        assert debts == [
            ("T-0001", "post-land-sweep-attribution-skipped-stale-baseline"),
            ("T-0001", "post-land-sweep-attribution-skipped-stale-baseline"),
        ]
        # Rebaselined regardless -- the next sweep should start from a
        # fresh, current comparison point once the debt is drained.
        assert _read_baseline(tmp_path) == fresh

    # frob:ticket T-2929
    def test_fresh_baseline_files_normally_no_new_noise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2929 must-stay-quiet case: `rapid_soft_warning` returning
        `None` (a fresh, current verification window) means the sweep
        files exactly as it did before this change -- no new refusal, no
        new debt line, identical behavior to `test_new_findings_file_a_
        ticket_and_rebaseline`."""
        # frob:tests \
        # tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun.test_fresh_baseline_files_normally_no_new_noise  # noqa: E501
        # frob:waive FMT001 reason="single-line frob:tests directive naming a long \
        # test node id -- already at frob fmt's own canonical form (verified: `frob \
        # fmt` reports it unchanged), same unwrappable shape as \
        # src/frob/app/_json_guard.py's existing FMT001 waivers"
        _write_baseline(tmp_path, frozenset({("COV003", "a.py")}), "old")
        fresh = frozenset({("COV003", "a.py"), ("DOC011", "b.md")})
        monkeypatch.setattr(
            "frob.app.ticket_runner._land_cmd._unscoped_error_findings",
            lambda *a, **k: fresh,
        )
        monkeypatch.setattr("frob.verify.rapid_soft_warning", lambda root: None)
        seen: list[frozenset[tuple[str, str]]] = []

        def _fake_file(root, final_id, commit, new_findings):  # noqa: ANN001, ANN202
            seen.append(new_findings)
            return "T-9999"

        monkeypatch.setattr(_rapid_sweep, "_file_regression_ticket", _fake_file)
        debts: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt",
            lambda root, tid, what: debts.append((tid, what)),
        )

        result = run_deferred_post_land_sweep(tmp_path, "T-0001", "abc123")

        assert result.is_ok
        assert result.danger_ok == "T-9999"
        assert seen == [frozenset({("DOC011", "b.md")})]
        assert debts == []
        assert _read_baseline(tmp_path) == fresh



# frob:ticket T-2938
class TestClaimDivergencePostLand:
    """T-2938: `_check_claim_divergence_post_land` -- the deferred-queue
    replacement for the inline `ClaimDivergence` re-verification T-2913
    moved off the rapid land critical path. Reuses `frob.tickets.
    _land_verify._reverify_gate_state_claim` VERBATIM (via callables that
    hand back this sweep's own already-measured `fresh` set instead of
    spawning a second `frob check`) as the sole comparison DECISION, and
    `frob.verify.rapid_soft_warning` (T-2929's existing policy) as the
    sole staleness DECISION -- these tests exercise the wiring, not a
    second copy of either policy."""

    def _claims_ticket(
        self,
        *,
        gate_errors: int,
        error_findings: frozenset[tuple[str, str]] | None,
        scope: tuple[str, ...] = ("src/a.py",),
    ):
        from frob.tickets._models import (
            DoneReportClaims,
            Origin,
            Ticket,
            TicketKind,
            TicketState,
            render_claims_block,
        )

        claims = DoneReportClaims(
            test_count=1,
            evidence_count=1,
            gate_errors=gate_errors,
            gate_warnings=0,
            gate_waived=0,
            error_findings=error_findings,
        )
        body = "## Done report\n\nlanded cleanly.\n\n" + render_claims_block(claims)
        return Ticket(
            id="T-0001",
            title="a ticket with a captured claim",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date(2026, 1, 1),
            body=body,
            scope=scope,
        )

    def _patch_common(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ticket,
        *,
        stale_reason: str | None,
    ) -> tuple[list[dict[str, object]], list[tuple[str, str]]]:
        from typani.result import Ok

        monkeypatch.setattr("frob.tickets._load_one", lambda root, tid: Ok(ticket))
        monkeypatch.setattr("frob.verify.rapid_soft_warning", lambda root: stale_reason)
        raised: list[dict[str, object]] = []
        monkeypatch.setattr(
            "frob.verify._quarantine.raise_quarantine",
            lambda root, **kw: raised.append(kw) or Ok(object()),
        )
        debts: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt",
            lambda root, tid, what: debts.append((tid, what)),
        )
        monkeypatch.setattr(_rapid_sweep, "_commit_rapid_debt", lambda root, tid: None)
        monkeypatch.setattr(
            _rapid_sweep,
            "_file_claim_divergence_ticket",
            lambda root, final_id, actual_head, pairs: "T-9999",
        )
        return raised, debts

    def test_matching_claim_raises_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Must-stay-quiet: a Done report claim that still matches the
        fresh post-merge measurement raises no quarantine and records no
        new debt."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestClaimDivergencePostLand.test_matching_claim_raises_nothing  # noqa: E501
        ticket = self._claims_ticket(
            gate_errors=1, error_findings=frozenset({("COV003", "src/a.py")})
        )
        raised, debts = self._patch_common(monkeypatch, ticket, stale_reason=None)

        _check_claim_divergence_post_land(
            tmp_path, "T-0001", "deadbeef", frozenset({("COV003", "src/a.py")})
        )

        assert raised == []
        assert debts == []

    def test_divergent_claim_raises_quarantine_attributed_to_landing_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Must-fire: a Done report claiming 0 errors against a fresh
        measurement showing a NEW in-scope error raises quarantine, and
        every raised finding is attributed to the landing ticket id."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestClaimDivergencePostLand.test_divergent_claim_raises_quarantine_attributed_to_landing_ticket  # noqa: E501
        ticket = self._claims_ticket(gate_errors=0, error_findings=frozenset())
        raised, debts = self._patch_common(monkeypatch, ticket, stale_reason=None)

        _check_claim_divergence_post_land(
            tmp_path, "T-0001", "deadbeef", frozenset({("COV003", "src/a.py")})
        )

        from frob.verify._quarantine import QuarantinedFinding

        assert debts == []
        assert len(raised) == 1
        findings = cast("tuple[QuarantinedFinding, ...]", raised[0]["findings"])
        assert len(findings) == 1
        assert findings[0].rule_id == "COV003"
        assert findings[0].file == "src/a.py"
        assert findings[0].commit_sha == "deadbeef"
        assert findings[0].ticket_id == "T-9999"
        assert raised[0]["batch_commit_shas"] == ("deadbeef",)

    def test_stale_baseline_refuses_to_attribute(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A stale verification-queue window (T-2929's shared policy)
        refuses to attribute a claim divergence too, recording the SAME
        debt reason `_refuse_filing_for_stale_verification_queue` already
        uses -- never a second staleness policy."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestClaimDivergencePostLand.test_stale_baseline_refuses_to_attribute  # noqa: E501
        ticket = self._claims_ticket(gate_errors=0, error_findings=frozenset())
        raised, debts = self._patch_common(
            monkeypatch, ticket, stale_reason="rapid profile verification debt is stale"
        )

        _check_claim_divergence_post_land(
            tmp_path, "T-0001", "deadbeef", frozenset({("COV003", "src/a.py")})
        )

        assert raised == []
        assert debts == [
            ("T-0001", "post-land-sweep-attribution-skipped-stale-baseline")
        ]

    def test_no_captured_claims_section_is_a_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A Done report with no `### Captured claims` section (predates
        T-0754, or never captured one) has nothing to compare -- no
        quarantine, no debt, matching the inline land path's own
        permissive-by-default posture."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestClaimDivergencePostLand.test_no_captured_claims_section_is_a_noop  # noqa: E501
        from typani.result import Ok

        from frob.tickets._models import Origin, Ticket, TicketKind, TicketState

        ticket = Ticket(
            id="T-0001",
            title="a ticket with no captured claim",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date(2026, 1, 1),
            body="## Done report\n\nlanded cleanly, no claims captured.\n",
        )
        monkeypatch.setattr("frob.tickets._load_one", lambda root, tid: Ok(ticket))
        raised: list[dict[str, object]] = []
        monkeypatch.setattr(
            "frob.verify._quarantine.raise_quarantine",
            lambda root, **kw: raised.append(kw) or Ok(object()),
        )
        # rapid_soft_warning left un-mocked: a tmp_path with no watermark
        # returns None (no debt), same as the pre-existing tests above.

        _check_claim_divergence_post_land(
            tmp_path, "T-0001", "deadbeef", frozenset({("COV003", "src/a.py")})
        )

        assert raised == []



class TestDeferredSweepSpawn:
    """The spawn records debt BEFORE spawning and never blocks."""

    def test_exec_disabled_records_debt_and_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepSpawn.test_exec_disabled_records_debt_and_refuses  # noqa: E501
        debts: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt",
            lambda root, tid, what: debts.append((tid, what)),
        )
        monkeypatch.setattr("frob.process.exec_enabled", lambda: False)
        result = spawn_deferred_post_land_sweep(tmp_path, "T-0001", "T-0001", "abc123")
        assert result.is_err
        assert result.danger_err is RapidSweepError.SpawnRefused
        assert debts == [("T-0001", "post-land-unscoped-sweep-deferred")]

    # frob:ticket T-2030
    def test_spawn_pins_frob_root_env_not_bare_os_environ(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2030's own repro: watch this FAIL first against the unfixed
        code -- `Popen` used to be called with no `env=` kwarg at all
        (bare inherited `os.environ`), so an ambient stale `FROB_ROOT` in
        the landing process's own shell silently overrode the correctly
        resolved `cwd=root` in the detached child's OWN root resolution.
        This asserts the actual `Popen` call always pins `FROB_ROOT` to
        `root`, regardless of what `os.environ` already contains."""
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepSpawn.test_spawn_pins_frob_root_env_not_bare_os_environ  # noqa: E501
        import subprocess as subprocess_mod

        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod

        monkeypatch.setattr("frob.process.exec_enabled", lambda: True)
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt", lambda root, tid, what: None
        )
        monkeypatch.setattr(
            rapid_sweep_mod, "_commit_rapid_debt", lambda root, tid: None
        )
        # A STALE FROB_ROOT in the ambient environment, naming a
        # DIFFERENT tree than `root` -- exactly T-2030's measured shape.
        monkeypatch.setenv("FROB_ROOT", "/some/other/worktree")
        monkeypatch.setenv("FROB_WORKTREE", "/some/other/worktree")
        monkeypatch.setenv("FROB_AGENT", "1")

        captured: dict = {}

        class _FakeProc:
            pid = 4242

        def _fake_popen(argv, **kwargs):
            captured.update(kwargs)
            return _FakeProc()

        monkeypatch.setattr(subprocess_mod, "Popen", _fake_popen)

        result = spawn_deferred_post_land_sweep(tmp_path, "T-0001", "T-0001", "abc123")
        assert result.is_ok

        env = captured.get("env")
        assert env is not None, "Popen must be called with an explicit env= kwarg"
        assert env["FROB_ROOT"] == str(tmp_path)
        assert "FROB_WORKTREE" not in env
        assert "FROB_AGENT" not in env



# frob:ticket T-2450
class TestDetachedSweepEnvPublicSeam:
    """T-2450: `detached_sweep_env` is a thin public wrapper around
    `_detached_sweep_env` -- the cross-node seam `frob.verify._drain`
    imports instead of reaching across the node boundary to call the
    private name directly."""

    # frob:ticket T-2450
    # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDetachedSweepEnvPublicSeam.test_delegates_to_the_private_implementation  # noqa: E501
    def test_delegates_to_the_private_implementation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.app.ticket_runner._rapid_sweep import (
            _detached_sweep_env,
            detached_sweep_env,
        )

        monkeypatch.setenv("FROB_WORKTREE", "/some/worktree")
        assert detached_sweep_env(tmp_path) == _detached_sweep_env(tmp_path)



# frob:ticket T-2030
class TestDetachedSweepEnv:
    """T-2030: `_detached_sweep_env`'s own unit-level contract."""

    def test_pins_frob_root_to_the_correct_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDetachedSweepEnv.test_pins_frob_root_to_the_correct_root  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _detached_sweep_env

        monkeypatch.setenv("FROB_ROOT", "/stale/other/worktree")
        env = _detached_sweep_env(tmp_path)
        assert env["FROB_ROOT"] == str(tmp_path)

    def test_strips_worktree_lease_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDetachedSweepEnv.test_strips_worktree_lease_env  # noqa: E501
        from frob.app.ticket_runner._rapid_sweep import _detached_sweep_env

        monkeypatch.setenv("FROB_WORKTREE", "/some/worktree")
        monkeypatch.setenv("FROB_AGENT", "1")
        env = _detached_sweep_env(tmp_path)
        assert "FROB_WORKTREE" not in env
        assert "FROB_AGENT" not in env
