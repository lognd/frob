"""T-2091: `_print_land_proof` must surface a SKIPPED_UNMEASURED claims
re-verification as its own distinct state, never as `verified=True`
(the overclaim T-2091 fixes) and never as `verified=False` either (the
ticket's own DO-NOT-FIX-IT-THIS-WAY section: a skip is a third state, not
a negative verification result). Isolated from a real `land()` call --
`_land_proof_checks` is monkeypatched so this exercises only
`_print_land_proof`'s own decision logic plus the
`frob.tickets._land._LAST_CLAIMS_OUTCOME` side channel T-2091 added,
matching the "first test MUST fail against current main" acceptance
criterion without needing a full fixture-repo land.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from frob.app.ticket_runner import _land_cmd
from frob.tickets._land import _LAST_CLAIMS_OUTCOME
from frob.tickets._land_verify import _ClaimsReverifyOutcome


# frob:ticket T-2091
# frob:waive WIRE001 reason="private test-fixture helper used only by this file's own \
# tests -- no production caller to wire it to by design" permanent="true"
def _fake_report(ticket_id: str = "T-9001") -> SimpleNamespace:
    """A minimal stand-in for `LandReport` carrying only the fields
    `_print_land_proof` reads."""
    return SimpleNamespace(
        ticket_id=ticket_id, final_id=ticket_id, commit_sha="deadbeef"
    )


# frob:ticket T-2091
class TestLandProofClaimsOutcome:
    """`_print_land_proof` consulting `_LAST_CLAIMS_OUTCOME` (T-2091)."""

    # frob:tests tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome.test_skipped_unmeasured_is_not_printed_as_verified_true  # noqa: E501
    def test_skipped_unmeasured_is_not_printed_as_verified_true(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        tmp_path,
    ) -> None:
        # This MUST fail against current main: pre-T-2091, `_print_land_
        # proof` never consults the claims-reverify outcome at all, so it
        # prints `verified=True` regardless.
        monkeypatch.setattr(
            _land_cmd,
            "_land_proof_checks",
            lambda root, fid, sha: (True, "done", False),
        )
        report = _fake_report("T-9001")
        _LAST_CLAIMS_OUTCOME["T-9001"] = _ClaimsReverifyOutcome.SKIPPED_UNMEASURED
        try:
            with caplog.at_level(logging.INFO):
                verified = _land_cmd._print_land_proof(tmp_path, report)
        finally:
            _LAST_CLAIMS_OUTCOME.pop("T-9001", None)

        proof_lines = [r.message for r in caplog.records if "LAND-PROOF:" in r.message]
        assert proof_lines, "expected a LAND-PROOF line to be logged"
        line = proof_lines[-1]
        assert "verified=True" not in line
        assert "SKIPPED-UNMEASURED" in line
        assert "claims_reverify=skipped-unmeasured" in line
        # T-2091's DO-NOT section: a skip must not become a hard refusal
        # either -- the ancestor+state checks alone still gate `--finish`/
        # the nonzero-exit check, unaffected by the skip.
        assert verified is True

    # frob:tests tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome.test_passed_healthy_path_is_unchanged  # noqa: E501
    def test_passed_healthy_path_is_unchanged(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        tmp_path,
    ) -> None:
        monkeypatch.setattr(
            _land_cmd,
            "_land_proof_checks",
            lambda root, fid, sha: (True, "done", False),
        )
        report = _fake_report("T-9002")
        _LAST_CLAIMS_OUTCOME["T-9002"] = _ClaimsReverifyOutcome.PASSED
        try:
            with caplog.at_level(logging.INFO):
                verified = _land_cmd._print_land_proof(tmp_path, report)
        finally:
            _LAST_CLAIMS_OUTCOME.pop("T-9002", None)

        proof_lines = [r.message for r in caplog.records if "LAND-PROOF:" in r.message]
        assert proof_lines
        line = proof_lines[-1]
        assert "verified=True" in line
        assert "claims_reverify=passed" in line
        assert verified is True

    # frob:tests tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome.test_no_recorded_outcome_leaves_verified_unaffected  # noqa: E501
    def test_no_recorded_outcome_leaves_verified_unaffected(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        tmp_path,
    ) -> None:
        # No entry in `_LAST_CLAIMS_OUTCOME` at all (a dry run / recovered
        # marker path that never went through `land()`'s own claims-check
        # step in this process) -- must not change the pre-T-2091 shape.
        monkeypatch.setattr(
            _land_cmd,
            "_land_proof_checks",
            lambda root, fid, sha: (True, "done", False),
        )
        report = _fake_report("T-9003")
        _LAST_CLAIMS_OUTCOME.pop("T-9003", None)

        with caplog.at_level(logging.INFO):
            verified = _land_cmd._print_land_proof(tmp_path, report)

        proof_lines = [r.message for r in caplog.records if "LAND-PROOF:" in r.message]
        assert proof_lines
        line = proof_lines[-1]
        assert "verified=True" in line
        assert "claims_reverify=unknown" in line
        assert verified is True
