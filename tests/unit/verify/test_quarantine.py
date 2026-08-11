"""Unit tests for `frob.verify._quarantine` (T-1693)."""

from __future__ import annotations

from pathlib import Path

from frob.verify._quarantine import (
    QuarantinedFinding,
    QuarantineError,
    clear_quarantine,
    is_quarantined,
    load_quarantine,
    raise_quarantine,
)


# frob:ticket T-1693
class TestLoadQuarantine:
    # frob:ticket T-1693
    def test_missing_file_is_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::load_quarantine kind="unit"
        result = load_quarantine(tmp_path)
        assert result.is_ok
        assert result.danger_ok is None

    # frob:ticket T-1693
    def test_corrupt_file_errors(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::load_quarantine kind="unit"
        path = tmp_path / ".frob" / "quarantine.json"
        path.parent.mkdir(parents=True)
        path.write_text("not json{{{", encoding="utf-8")
        result = load_quarantine(tmp_path)
        assert result.is_err
        assert result.danger_err is QuarantineError.StoreCorrupt


# frob:ticket T-1693
class TestIsQuarantined:
    # frob:ticket T-1693
    def test_false_when_never_raised(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::is_quarantined kind="unit"
        result = is_quarantined(tmp_path)
        assert result.is_ok
        assert result.danger_ok is False

    # frob:ticket T-1693
    def test_true_while_raised(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::is_quarantined kind="unit"
        raised = raise_quarantine(
            tmp_path, batch_commit_shas=("deadbeef",), findings=(QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),)
        )
        assert raised.is_ok
        result = is_quarantined(tmp_path)
        assert result.is_ok
        assert result.danger_ok is True

    # frob:ticket T-1693
    def test_false_after_clear(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::is_quarantined kind="unit"
        finding = QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1)
        assert raise_quarantine(
            tmp_path, batch_commit_shas=("deadbeef",), findings=(finding,)
        ).is_ok
        cleared = clear_quarantine(
            tmp_path,
            dispositions={
                (finding.rule_id, finding.file, finding.line): ("filed", "T-9999")
            },
            reason="filed as T-9999",
            actor="test",
        )
        assert cleared.is_ok
        result = is_quarantined(tmp_path)
        assert result.is_ok
        assert result.danger_ok is False


# frob:ticket T-1693
class TestRaiseQuarantine:
    # frob:ticket T-1693
    def test_raises_and_persists(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        result = raise_quarantine(
            tmp_path, batch_commit_shas=("abc123",), findings=(QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),)
        )
        assert result.is_ok
        record = result.danger_ok
        assert record.batch_commit_shas == ("abc123",)
        assert len(record.findings) == 1
        assert record.cleared_at is None

    # frob:ticket T-1693
    def test_empty_findings_refused(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        result = raise_quarantine(tmp_path, batch_commit_shas=("abc123",), findings=())
        assert result.is_err
        assert result.danger_err is QuarantineError.EmptyFindings

    # frob:ticket T-1693
    def test_survives_a_fresh_load_reflecting_a_restart(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # Durability across a worker restart: a fresh `load_quarantine`
        # call (simulating a brand-new process) must see the same raised
        # state, never an in-memory-only flag.
        assert raise_quarantine(
            tmp_path, batch_commit_shas=("abc123",), findings=(QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),)
        ).is_ok
        reloaded = load_quarantine(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok is not None
        assert reloaded.danger_ok.cleared_at is None

    # frob:ticket T-2132
    def test_a_naturally_unattributable_finding_alone_does_not_raise(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # TICK004 (ticket-rot: "T-#### has sat queued for Nd") is a
        # statement about ELAPSED TIME, not about any commit's diff --
        # commit=None here is the truth, not a failed attribution. A
        # batch whose only finding is TICK004 must not switch deferred
        # landing off repo-wide (T-2132): no land can ever "fix" a clock.
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=(),
            findings=(
                QuarantinedFinding(rule_id="TICK004", file="tickets.md", line=0),
            ),
        )
        assert result.is_err
        assert result.danger_err is QuarantineError.EmptyFindings
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-2132
    def test_an_unattributed_code_finding_still_raises(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # Contrast case: a real code finding that attribution genuinely
        # FAILED to pin to a commit (`commit_sha=None` because the
        # reachability walk found zero or >1 candidates, not because the
        # rule is inherently clock-driven) must still raise -- T-1686's
        # prior-art incident was a sweep that treated UNATTRIBUTED code
        # findings as non-regressions, which is the opposite mistake.
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(
                QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),
            ),
        )
        assert result.is_ok
        assert is_quarantined(tmp_path).danger_ok is True

    # frob:ticket T-2132
    def test_a_mixed_batch_raises_with_only_the_attributable_finding_kept(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_quarantine.py::raise_quarantine kind="unit"
        # A batch with BOTH a naturally-unattributable finding and a real
        # code finding still raises (the code finding is real), but the
        # persisted record drops the naturally-unattributable one -- it
        # was never something a filed ticket against a commit could fix.
        result = raise_quarantine(
            tmp_path,
            batch_commit_shas=("abc123",),
            findings=(
                QuarantinedFinding(rule_id="TICK004", file="tickets.md", line=0),
                QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),
            ),
        )
        assert result.is_ok
        record = result.danger_ok
        assert len(record.findings) == 1
        assert record.findings[0].rule_id == "TEST001"


# frob:ticket T-1693
class TestClearQuarantine:
    # frob:ticket T-1693
    def test_refuses_when_not_raised(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::clear_quarantine kind="unit"
        result = clear_quarantine(
            tmp_path, dispositions={}, reason="nothing to clear", actor="test"
        )
        assert result.is_err
        assert result.danger_err is QuarantineError.NotQuarantined

    # frob:ticket T-1693
    def test_refuses_when_a_finding_is_undisposed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::clear_quarantine kind="unit"
        assert raise_quarantine(
            tmp_path, batch_commit_shas=("abc123",), findings=(QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),)
        ).is_ok
        result = clear_quarantine(
            tmp_path, dispositions={}, reason="tried anyway", actor="test"
        )
        assert result.is_err
        assert result.danger_err is QuarantineError.FindingsNotDisposed
        # A refused clear must NOT have silently cleared it.
        assert is_quarantined(tmp_path).danger_ok is True

    # frob:ticket T-1693
    def test_clears_when_every_finding_disposed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::clear_quarantine kind="unit"
        a = QuarantinedFinding(rule_id="TEST001", file="src/a.py", line=1)
        b = QuarantinedFinding(rule_id="TEST002", file="src/b.py", line=2)
        assert raise_quarantine(
            tmp_path, batch_commit_shas=("abc123",), findings=(a, b)
        ).is_ok
        result = clear_quarantine(
            tmp_path,
            dispositions={
                (a.rule_id, a.file, a.line): ("filed", "T-1000"),
                (b.rule_id, b.file, b.line): ("dismissed", "false positive"),
            },
            reason="both disposed",
            actor="test",
        )
        assert result.is_ok
        record = result.danger_ok
        assert record.cleared_at is not None
        assert record.cleared_reason == "both disposed"
        by_rule = {f.rule_id: f for f in record.findings}
        assert by_rule["TEST001"].disposition == "filed"
        assert by_rule["TEST001"].disposition_ref == "T-1000"
        assert by_rule["TEST002"].disposition == "dismissed"
        assert by_rule["TEST002"].disposition_reason == "false positive"

    # frob:ticket T-1693
    def test_green_verification_alone_never_clears(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_quarantine.py::clear_quarantine kind="unit"
        # The single most important property: `is_quarantined` staying
        # True is not affected by anything OTHER than an explicit
        # `clear_quarantine` call disposing every finding -- there is no
        # "record a green run" entrypoint in this module at all, so a
        # green verification structurally cannot clear it. This test
        # documents that absence by re-checking `is_quarantined` after
        # simply re-loading the store repeatedly (simulating however many
        # subsequent green batch runs happened) with no clear call.
        assert raise_quarantine(
            tmp_path, batch_commit_shas=("abc123",), findings=(QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),)
        ).is_ok
        for _ in range(5):
            assert is_quarantined(tmp_path).danger_ok is True
