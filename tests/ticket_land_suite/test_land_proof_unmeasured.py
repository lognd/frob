"""T-5122: `land()` must refuse -- not just print a token -- when the
post-merge Done-report-claims re-verification (T-0754/T-2083) was
actually ATTEMPTED and PREVENTED by an infrastructure failure
(INFRA-UNMEASURED, T-4281), unless an explicit `--force --reason ...`
override is recorded via the T-1762 `force-overrides.jsonl` mechanism
`frob ticket archive --force` already uses. A DELIBERATE, never-attempted
skip (SKIPPED-UNMEASURED -- no capture callables supplied, `--rapid`'s
inline-skip, or a Done report with no captured-claims section) stays
non-gating by design (T-2083/T-4281's own docstrings), so an ordinary
land unrelated to this check is unaffected. Positive control for the
measured incident: `/tmp/land-T-4550.log` printed an unmeasurable claims
verdict next to `LAND-EXIT=0` -- exactly the shape this closes.
"""

# frob:ticket T-5122

from __future__ import annotations

import json
from pathlib import Path

from frob.tickets._land_finalize import _enforce_claims_reverify_verdict
from frob.tickets._land_verify import _ClaimsReverifyOutcome
from frob.tickets._models import LandError


class TestEnforceClaimsReverifyVerdict:
    """`_enforce_claims_reverify_verdict`'s own unit contract, isolated
    from the rest of the land pipeline -- a measured `PASSED` verdict, or
    a deliberate `SKIPPED_UNMEASURED` skip, is always a no-op; only a
    genuine `INFRA_UNMEASURED` measurement failure refuses, unless
    `force=True` records a real, non-blank reason."""

    # frob:tests src/frob/tickets/_land_finalize.py::_enforce_claims_reverify_verdict  # noqa: E501
    def test_passed_is_ok(self, tmp_path: Path) -> None:
        result = _enforce_claims_reverify_verdict(
            tmp_path, "T-0001", _ClaimsReverifyOutcome.PASSED
        )
        assert result.is_ok
        assert not (tmp_path / "force-overrides.jsonl").exists()
# frob:tests src/frob/tickets/_land_finalize.py::_enforce_claims_reverify_verdict  # noqa: E501

    def test_deliberate_skip_is_ok_not_gated(self, tmp_path: Path) -> None:
        result = _enforce_claims_reverify_verdict(
            tmp_path, "T-0001", _ClaimsReverifyOutcome.SKIPPED_UNMEASURED
        )
        assert result.is_ok
        # frob:tests src/frob/tickets/_land_finalize.py::_enforce_claims_reverify_verdict  # noqa: E501
        assert not (tmp_path / "force-overrides.jsonl").exists()

    def test_infra_unmeasured_refuses_without_force(self, tmp_path: Path) -> None:
        result = _enforce_claims_reverify_verdict(
            tmp_path, "T-0001", _ClaimsReverifyOutcome.INFRA_UNMEASURED
        )
        assert result.is_err
        assert result.danger_err is LandError.ClaimsReverifyUnmeasured

    def test_unmeasured_with_force_and_reason_records_override_and_proceeds(
        self, tmp_path: Path
    ) -> None:
        result = _enforce_claims_reverify_verdict(
            tmp_path,
            "T-0002",
            _ClaimsReverifyOutcome.INFRA_UNMEASURED,
            force=True,
            force_reason="independently confirmed clean via manual pytest run",
        )
        assert result.is_ok
        overrides_path = tmp_path / "force-overrides.jsonl"
        assert overrides_path.exists()
        row = json.loads(overrides_path.read_text().splitlines()[0])
        assert row["command"] == "ticket land"
        assert row["guard"] == "T-5122 claims-reverify-unmeasured refusal"
        assert row["target"] == "T-0002"
        assert "independently confirmed" in row["reason"]

    def test_unmeasured_with_force_but_no_reason_still_refuses(
        self, tmp_path: Path
    ) -> None:
        result = _enforce_claims_reverify_verdict(
            tmp_path,
            "T-0003",
            _ClaimsReverifyOutcome.INFRA_UNMEASURED,
            force=True,
            force_reason="   ",
        )
        assert result.is_err
        assert result.danger_err is LandError.ClaimsReverifyUnmeasured
        assert not (tmp_path / "force-overrides.jsonl").exists()

    def test_unmeasured_with_force_reason_file(self, tmp_path: Path) -> None:
        reason_file = tmp_path / "reason.txt"
        reason_file.write_text(
            "verified by hand against the merged tree", encoding="utf-8"
        )
        result = _enforce_claims_reverify_verdict(
            tmp_path,
            "T-0004",
            _ClaimsReverifyOutcome.INFRA_UNMEASURED,
            force=True,
            force_reason_file=reason_file,
        )
        assert result.is_ok
        row = json.loads(
            (tmp_path / "force-overrides.jsonl").read_text().splitlines()[0]
        )
        assert "verified by hand" in row["reason"]
