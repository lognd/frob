"""`frob.perf._ratchet` -- hot-graph perf regression ratchet (T-0712, EPIC
T-0709, child of T-0711's sketch store).

Compares a section's freshly-built current-run `QuantileSketch` against
the sketch already stored for it (its "prior", pre-merge) and fires a
finding when the shift is large enough to be a real regression rather
than run-to-run noise. Deliberately NOT the `frob.gates._ratchet`
baseline-pool mechanism (that pool tracks pre-existing VIOLATION COUNTS a
rule may not silently regress on; this ticket ratchets a MEASURED
QUANTILE, a different shape of "don't get worse than before" contract) --
"ratchet-pool style ... baseline-old error-new" in docs/modules/perf.md
names the naming convention this borrows, not the mechanism itself.

Findings are persisted to `.frob/perf/ratchet_findings.json` by whichever
CLI actually has both a current run's samples and the store's prior
(`frob perf collect`, today's only producer) so `frob check`'s perf gate
(`frob.gates.__init__.perf_gate`, PERF009) can surface them without
itself re-running a live profiling collection -- gates stay pure static
analysis over already-recorded artifacts, matching every other PERF rule's
posture.
"""
# frob:waive INV006 reason="T-0712: this module's 'only' usage ('today's only \
# producer') is source-level design-rationale prose describing already-implemented \
# internal behavior (verifiable by reading frob.app.perf_runner's _persist_run, the \
# sole current caller), not a separate cross-module contract needing its own tracked \
# invariant; same calibration-batch disposition as the T-0585/T-0711 INV006 pool"

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.gates._models import Severity, Violation
from frob.logging import get_logger
from frob.stats._sketch import QuantileSketch, quantile

_log = get_logger(__name__)

__all__ = [
    "RATCHET_FINDINGS_REL",
    "RatchetFinding",
    "check_ratchet",
    "load_ratchet_findings",
    "ratchet_violations",
    "save_ratchet_findings",
]

# frob:doc docs/modules/perf.md#regression-ratchet-t-0712
#: `.frob/perf/ratchet_findings.json`'s path, relative to a project root --
#: written by `frob perf collect`, read by `frob.gates.__init__.perf_gate`.
RATCHET_FINDINGS_REL = Path("perf") / "ratchet_findings.json"

#: Quantiles compared: p50 (typical case) and p90 (tail, the acceptance
#: text's own wording -- "both decile sets").
_RATCHET_QUANTILES = (0.5, 0.9)


# frob:doc docs/modules/perf.md#regression-ratchet-t-0712
class RatchetFinding(BaseModel):
    """One section whose current-run sketch regressed beyond
    `SketchStoreConfig.ratchet_tolerance` relative to its stored prior, at
    either quantile in `_RATCHET_QUANTILES`. `prior_deciles`/
    `current_deciles` are `{"p50": ..., "p90": ...}` -- both decile sets,
    per the acceptance text -- so a consumer never has to re-derive them
    from a raw sketch."""

    model_config = ConfigDict(frozen=True)

    section_key: str
    label: str
    prior_deciles: dict[str, float]
    current_deciles: dict[str, float]
    worst_relative_shift: float


def _deciles(sketch: QuantileSketch) -> dict[str, float]:
    """`{"p50": ..., "p90": ...}` read from `sketch` at
    `_RATCHET_QUANTILES`."""
    return {f"p{int(q * 100)}": quantile(sketch, q) for q in _RATCHET_QUANTILES}


# frob:doc docs/modules/perf.md#regression-ratchet-t-0712
# frob:tests tests/unit/perf/test_ratchet.py::TestCheckRatchet.test_no_prior_never_fires  # noqa: E501
# frob:tests tests/unit/perf/test_ratchet.py::TestCheckRatchet.test_regression_beyond_tolerance_fires  # noqa: E501
# frob:tests tests/unit/perf/test_ratchet.py::TestCheckRatchet.test_within_tolerance_does_not_fire  # noqa: E501
def check_ratchet(
    section_key: str,
    label: str,
    prior: QuantileSketch | None,
    current: QuantileSketch,
    tolerance: float,
) -> RatchetFinding | None:
    """`None` when `prior` is absent (a section's first-ever run has
    nothing to regress against -- never a finding) or every quantile in
    `_RATCHET_QUANTILES` shifted by at most `tolerance` (relative,
    `(current - prior) / prior`; a prior of exactly `0.0` is treated as
    "any positive current value is infinite relative shift" rather than a
    `ZeroDivisionError`) -- a `RatchetFinding` naming both decile sets and
    the worst (largest) relative shift observed otherwise."""
    if prior is None:
        return None
    prior_deciles = _deciles(prior)
    current_deciles = _deciles(current)
    worst = 0.0
    regressed = False
    for key, prior_value in prior_deciles.items():
        current_value = current_deciles[key]
        if prior_value <= 0.0:
            shift = float("inf") if current_value > 0.0 else 0.0
        else:
            shift = (current_value - prior_value) / prior_value
        worst = max(worst, shift)
        if shift > tolerance:
            regressed = True
    if not regressed:
        return None
    _log.warning(
        "perf ratchet: %s (%s) regressed %.1f%% beyond tolerance %.1f%%",
        label or section_key,
        section_key,
        worst * 100,
        tolerance * 100,
    )
    return RatchetFinding(
        section_key=section_key,
        label=label,
        prior_deciles=prior_deciles,
        current_deciles=current_deciles,
        worst_relative_shift=worst,
    )


# frob:doc docs/modules/perf.md#regression-ratchet-t-0712
# frob:tests tests/unit/perf/test_ratchet.py::TestPersistRoundTrip.test_save_then_load_round_trips  # noqa: E501
def save_ratchet_findings(root: Path, findings: list[RatchetFinding]) -> None:
    """Overwrite `root/.frob/perf/ratchet_findings.json` with `findings`
    (empty list clears it) -- one run's full set, never appended-to,
    since each `frob perf collect` invocation supersedes the last run's
    regression picture entirely."""
    path = root / ".frob" / RATCHET_FINDINGS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [f.model_dump() for f in findings]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# frob:doc docs/modules/perf.md#regression-ratchet-t-0712
# frob:tests tests/unit/perf/test_ratchet.py::TestPersistRoundTrip.test_save_then_load_round_trips  # noqa: E501
# frob:tests tests/unit/perf/test_ratchet.py::TestPersistRoundTrip.test_missing_file_is_empty  # noqa: E501
# frob:tests tests/unit/perf/test_ratchet.py::TestPersistRoundTrip.test_malformed_json_is_empty_not_a_crash  # noqa: E501
# frob:tests tests/unit/perf/test_ratchet.py::TestPersistRoundTrip.test_wrong_schema_json_is_empty_not_a_crash  # noqa: E501
def load_ratchet_findings(root: Path) -> list[RatchetFinding]:
    """`root/.frob/perf/ratchet_findings.json`'s findings, or `[]` when the
    file is missing/malformed (fail-open -- no `frob perf collect` run yet
    means zero PERF009 findings, never a gate crash)."""
    path = root / ".frob" / RATCHET_FINDINGS_REL
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _log.warning("ratchet findings at %s unreadable: %s", path, exc)
        return []
    try:
        return [RatchetFinding.model_validate(entry) for entry in payload]
    except (TypeError, ValueError) as exc:
        _log.warning("ratchet findings at %s malformed: %s", path, exc)
        return []


# frob:doc docs/modules/perf.md#regression-ratchet-t-0712
# frob:tests tests/unit/perf/test_ratchet.py::TestRatchetViolations.test_findings_become_perf009_violations  # noqa: E501
# frob:tests tests/unit/perf/test_ratchet.py::TestRatchetViolations.test_no_findings_file_is_zero_violations  # noqa: E501
# frob:enforces CHK-GATE-PERF009
# frob:enforces CHK-SUBSYS-PERF
def ratchet_violations(root: Path) -> list[Violation]:
    """PERF009: one WARN-tier `Violation` per `load_ratchet_findings(root)`
    entry, named at `.frob/perf/ratchet_findings.json` itself (the finding
    has no source file/line of its own -- it names a `Section`, which is
    an ephemeral per-run construct, not a stable source anchor a
    `frob:waive` comment could sit above). `frob.gates.__init__.perf_gate`
    calls this alongside `frob.perf.perf_rules` -- static analysis over an
    already-recorded artifact, same posture as every other PERF rule,
    never a live re-collection at gate time."""
    findings = load_ratchet_findings(root)
    findings_path = str(root / ".frob" / RATCHET_FINDINGS_REL)
    return [
        Violation(
            rule="PERF009",
            severity=Severity.WARN,
            file=findings_path,
            line=1,
            message=(
                f"{finding.label or finding.section_key} regressed "
                f"{finding.worst_relative_shift * 100:.0f}% beyond tolerance: "
                f"prior deciles {finding.prior_deciles} vs current "
                f"{finding.current_deciles}"
            ),
        )
        for finding in findings
    ]
