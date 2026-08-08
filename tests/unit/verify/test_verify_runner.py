"""Unit tests for `frob.app.verify_runner` (T-1697)."""

from __future__ import annotations

from pathlib import Path

from frob.app.verify_runner import build_status
from frob.verify._quarantine import (
    QuarantinedFinding,
    clear_quarantine,
    raise_quarantine,
)
from frob.verify._watermark import advance_watermark, record_intent


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
