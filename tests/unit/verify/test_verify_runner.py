"""Unit tests for `frob.app.verify_runner` (T-1697)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typani import Ok

from frob.app.config import AppConfig
from frob.app.verify_runner import _run_dispose, _run_explain, build_status
from frob.graph import CallGraph, GraphSnapshot
from frob.verify._quarantine import (
    QuarantinedFinding,
    QuarantineRecord,
    clear_quarantine,
    load_quarantine,
    raise_quarantine,
)
from frob.verify._watermark import advance_watermark, record_intent
from tests.unit.verify.conftest import make_queue_entry, make_symbol


class TestBuildStatus:
    """`build_status`: the whole `frob verify status` payload."""

    def test_clean_when_nothing_queued_and_no_quarantine(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/verify_runner.py::build_status kind="unit"
        status = build_status(tmp_path)
        assert status is not None
        assert status.depth == 0
        assert status.watermark_commit is None
        assert status.quarantine_raised is False
        assert status.quarantine_findings == ()

    def test_reports_depth_age_and_quarantine(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/verify_runner.py::build_status kind="unit"
        record_intent(
            tmp_path,
            commit_sha="abc123",
            ticket_id="T-0001",
            touched_symbols=("src/frob/foo.py::bar",),
            profile="rapid",
        )
        raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(
                QuarantinedFinding(rule_id="unresolved-import", file="tests/x.py"),
            ),
        )
        status = build_status(tmp_path)
        assert status is not None
        assert status.depth == 1
        assert status.oldest_unverified_commit == "abc123"
        assert status.oldest_unverified_ticket == "T-0001"
        assert status.quarantine_raised is True
        assert len(status.quarantine_findings) == 1
        finding = status.quarantine_findings[0]
        assert finding.key == "unresolved-import:tests/x.py:"
        assert finding.disposition == ""

    def test_watermark_reported_when_present(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/verify_runner.py::build_status kind="unit"
        advance_watermark(
            tmp_path, commit_sha="deadbeef", run_id="r1", baseline_digest="d1"
        )
        status = build_status(tmp_path)
        assert status is not None
        assert status.watermark_commit == "deadbeef"
        assert status.watermark_age_s is not None


# frob:waive WIRE001 reason="test-only fixture helper, exercised by every test in TestDispose's retire-unidentifiable trio -- not production code to wire; follow_up points at T-2246 (WIRE002 requires a live open ticket, not because that ticket is expected to remove the waiver itself), same posture as tests/unit/verify/test_quarantine.py::_seed_stuck_store's own waiver" follow_up="T-2246"  # noqa: E501
def _seed_identity_less_store(tmp_path: Path, *, extra: tuple = ()) -> None:
    """T-2217: persist a quarantine record directly (bypassing
    `raise_quarantine`, which T-2207's producer-side fix now filters an
    identity-less finding out of before it ever reaches disk) -- mirrors
    an already-stuck store from before that fix landed, the same fixture
    shape `tests/unit/verify/test_quarantine.py::_seed_stuck_store` uses
    for `retire_unidentifiable_findings`'s own tests."""
    identity_less = QuarantinedFinding(rule_id="", file="")
    record = QuarantineRecord(
        raised_at="2026-01-01T00:00:00+00:00",
        batch_commit_shas=("deadbeef",),
        findings=(identity_less, *extra),
    )
    path = tmp_path / ".frob" / "quarantine.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")


class TestDispose:
    """`clear_quarantine`, exercised the same way `frob verify dispose`
    drives it -- disposing the live unattributed finding this ticket's
    Done report cites as its end-to-end proof."""

    def test_dismiss_disposes_the_live_unattributed_finding(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::clear_quarantine kind="unit"
        raise_quarantine(
            tmp_path,
            batch_commit_shas=("c1", "c2"),
            findings=(
                QuarantinedFinding(
                    rule_id="unresolved-import",
                    file="tests/unit/strata/test_capacity.py",
                    line=None,
                    commit_sha=None,
                    ticket_id=None,
                ),
            ),
        )
        key = ("unresolved-import", "tests/unit/strata/test_capacity.py", None)
        result = clear_quarantine(
            tmp_path,
            dispositions={
                key: (
                    "dismissed",
                    "environment artifact: unattributed cold-worktree "
                    "native-ext noise, not a real import break",
                )
            },
            reason="dismiss unattributed finding as cold-worktree noise",
            actor="T-1697 agent",
        )
        assert result.is_ok
        cleared = result.danger_ok
        assert cleared.cleared_at is not None
        assert cleared.findings[0].disposition == "dismissed"

        status = build_status(tmp_path)
        assert status is not None
        assert status.quarantine_raised is False

    def test_retire_unidentifiable_flag_retires_and_clears(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/app/verify_runner.py::_run_dispose kind="unit"
        """T-2217: `--retire-unidentifiable` reaches
        `retire_unidentifiable_findings` -- the only path that can dispose
        an identity-less finding at all, since `RULE:FILE:LINE` addressing
        can never key `("", "", None)`."""
        _seed_identity_less_store(tmp_path)
        cfg = AppConfig(
            verify_command="dispose",
            verify_path=tmp_path,
            verify_dispose_retire_unidentifiable=True,
            verify_dispose_reason="T-2207 recovery: identity-less record",
            verify_dispose_actor="T-2217 agent",
        )
        _run_dispose(cfg)  # returns normally -- no sys.exit on success

        loaded = load_quarantine(tmp_path)
        assert loaded.is_ok
        record = loaded.danger_ok
        assert record is not None
        assert record.cleared_at is not None
        assert record.findings[0].disposition == "dismissed"

    def test_retire_unidentifiable_flag_rejects_combination_with_dismiss(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/app/verify_runner.py::_run_dispose kind="unit"
        """T-2217: `--retire-unidentifiable` combined with `--dismiss`
        refuses outright rather than silently ignoring one -- combining
        the identity-less recovery path with a caller-supplied key is
        never a valid request."""
        _seed_identity_less_store(tmp_path)
        cfg = AppConfig(
            verify_command="dispose",
            verify_path=tmp_path,
            verify_dispose_retire_unidentifiable=True,
            verify_dispose_dismissed=["unresolved-import:tests/x.py:=noise"],
            verify_dispose_reason="attempted combination",
            verify_dispose_actor="T-2217 agent",
        )
        with pytest.raises(SystemExit) as exc:
            _run_dispose(cfg)
        assert exc.value.code == 1

        loaded = load_quarantine(tmp_path)
        assert loaded.is_ok
        record = loaded.danger_ok
        assert record is not None
        assert record.cleared_at is None

    def test_retire_unidentifiable_flag_still_blocks_on_a_well_formed_sibling(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/app/verify_runner.py::_run_dispose kind="unit"
        """T-2217 must-still-pass control (mirrors T-2207's own `test_
        retire_unidentifiable_findings_still_blocks_on_a_well_formed_
        sibling`): a well-formed, undisposed finding alongside the
        identity-less one still blocks the actual clear -- the CLI wiring
        must not create a bypass around that guard."""
        _seed_identity_less_store(
            tmp_path,
            extra=(QuarantinedFinding(rule_id="unresolved-import", file="tests/x.py"),),
        )
        cfg = AppConfig(
            verify_command="dispose",
            verify_path=tmp_path,
            verify_dispose_retire_unidentifiable=True,
            verify_dispose_reason="T-2207 recovery: identity-less record",
            verify_dispose_actor="T-2217 agent",
        )
        with pytest.raises(SystemExit) as exc:
            _run_dispose(cfg)
        assert exc.value.code == 1

        loaded = load_quarantine(tmp_path)
        assert loaded.is_ok
        record = loaded.danger_ok
        assert record is not None
        assert record.cleared_at is None
        by_rule = {f.rule_id: f for f in record.findings}
        assert by_rule[""].disposition == "dismissed"
        assert by_rule["unresolved-import"].disposition == ""


# frob:ticket T-2018
class TestRunExplainAdHocFallback:
    """T-2018: `frob verify explain` no longer refuses just because the
    persisted verify queue is empty -- reproduces the exact T-0907
    measurement (`frob verify status` -> `watermark: (none yet)`,
    `depth: 0`; `frob verify explain` -> "queue is empty, nothing to
    attribute against") and asserts the FIX: `_run_explain` now reaches a
    real attribution outcome (attributed, naming the causing commit in
    the output an operator already reads) via `build_ad_hoc_batch`'s
    git-history fallback, with no new verb and no sweep having enqueued
    anything first."""

    def test_empty_persisted_queue_still_attributes_via_ad_hoc_history(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        # frob:tests src/frob/app/verify_runner.py::_run_explain kind="unit"
        import frob.app.verify_runner as verify_runner_mod

        # Reproduces the measured T-0907 precondition exactly: queue_status
        # returns the empty tuple (the OLD code's refusal trigger).
        monkeypatch.setattr(verify_runner_mod, "_resolve_root", lambda cfg: tmp_path)

        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={"a.py::fn": make_symbol("a.py", "fn", 1, 5)},
            edges=(),
        )
        call_graph = CallGraph(calls={})

        import frob.verify as verify_pkg

        monkeypatch.setattr(
            verify_pkg,
            "load_attribution_context",
            lambda root: Ok((snapshot, call_graph)),
        )
        monkeypatch.setattr(verify_pkg, "queue_status", lambda root: Ok(()))
        monkeypatch.setattr(verify_pkg, "load_watermark", lambda root: Ok(None))
        monkeypatch.setattr(
            verify_pkg,
            "build_ad_hoc_batch",
            lambda root, *, snapshot, since=None, limit=50: (
                make_queue_entry("adhocsha123", "T-9999", ("a.py::fn",)),
            ),
        )

        cfg = AppConfig(
            verify_command="explain",
            verify_finding="RULE1:a.py:2",
            verify_path=tmp_path,
        )
        # An ATTRIBUTED result never calls sys.exit -- a stray SystemExit
        # here would mean the OLD "queue is empty" refusal (or a
        # regression to it) fired instead of a real attribution.
        _run_explain(cfg)
        out = capsys.readouterr().out
        assert "queue is empty" not in out
        assert "adhocsha123" in out
