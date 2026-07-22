"""Native `frob sys audit` invocation for the touched-set test runner
(T-0242, docs/modules/testing.md#strata-runner-native-t-0242).

Malmberg pilot P3 (2026-07-18) hit a hard wall: touching a `.strata`
design file breaks `frob test` with `NoRunner` (language `strata` has
selected tests but no `[[test.runner]]`), and the only documented
workaround -- registering `frob sys audit` as a `[[test.runner]]` entry
(T-0149) -- demands a dummy `{ids}` placeholder in the command because
`frob.testing._runners._validate_placeholder` requires exactly one, even
though `frob sys audit` takes no per-item ids at all; it audits the whole
merged design model.

This module gives `frob.testing._runners.run_selected` a placeholder-free,
zero-config path for the `strata` language: run the SAME exhaustiveness +
self-conformance evaluation `frob sys audit` runs, in-process, directly
against the repo's design dir, no `frob.toml` entry required. Zero new
detection -- this composes only the already-shipped `load_design_ids` /
`merge_models` / `evaluate_exhaustiveness` / `check_self_conformance`
(matching `frob.app.sys_runner`'s `_load_audit_model`/`_evaluate_audit`,
duplicated here in miniature rather than imported because `frob.app`
sits above `frob.strata` in the layering -- `frob.strata` must not import
back up into it, and `frob.testing` must not import `frob.app` either,
matching this module's own layering: `frob.testing` -> `frob.strata`,
never the reverse)."""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/strata/_native_test.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._audit import DEFAULT_BENIGN_CAPABILITIES, AuditReport, evaluate_exhaustiveness
from ._design_load import DEFAULT_DESIGN_DIR, load_design_ids
from ._errors import StrataError
from ._selfconform import SelfConformReport, check_self_conformance
from ._sysdoc import merge_models
from ._threat import load_repo_benign_capabilities

_log = get_logger(__name__)


# frob:doc docs/modules/testing.md#strata-runner-native-t-0242
# frob:tests tests/test_testing.py::TestNativeStrataAudit.test_no_runner_config_needed
class NativeAuditOutcome(BaseModel):
    """The pass/fail verdict plus a printable summary from one native
    `run_native_sys_audit` call -- what `frob.testing._runners` needs to
    fold into a `RunnerOutcome` without reaching back into `AuditReport`/
    `SelfConformReport` internals itself."""

    model_config = ConfigDict(frozen=True)

    proved: bool
    summary: str


def _format_gaps(report: AuditReport) -> list[str]:
    """One line per unwaived exhaustiveness gap, CI-parseable like `frob
    sys audit`'s own `_print_audit_report` (not reused directly: that
    helper prints via the module logger with `frob.app`-only styling
    helpers, out of this module's layering)."""
    return [
        f"GAP family={gap.family} view={gap.view} rule={gap.rule} "
        f"target={gap.target} detail={gap.detail}"
        for gap in report.gaps
    ]


def _format_selfconform(report: SelfConformReport) -> list[str]:
    """One line per unwaived self-conformance violation (SYS100-102)."""
    return [
        f"GAP family=sys rule={v.rule} node={v.node} detail={v.detail}"
        for v in report.violations
    ]


def _summarize(report: AuditReport, selfconform: SelfConformReport) -> str:
    """A deterministic, multi-line printable summary of both reports:
    checked views first, then every unwaived gap, else a PROVED line."""
    lines = [
        f"checked {len(report.views_checked)} view(s): "
        f"{', '.join(report.views_checked)}",
    ]
    gap_lines = _format_gaps(report) + _format_selfconform(selfconform)
    if gap_lines:
        lines.extend(gap_lines)
    else:
        lines.append("PROVED -- zero unwaived gaps")
    return "\n".join(lines)


# frob:doc docs/modules/testing.md#strata-runner-native-t-0242
# frob:tests tests/test_testing.py::TestNativeStrataAudit.test_no_runner_config_needed
# frob:tests tests/test_testing.py::TestNativeStrataAudit.test_no_models_is_neutral_pass
# frob:tests tests/test_testing.py::TestNativeStrataAudit.test_bad_design_file_fails
def run_native_sys_audit(
    root: Path, design_dir: str = DEFAULT_DESIGN_DIR
) -> Result[NativeAuditOutcome, StrataError]:
    """Load every `.strata` file under `root/design_dir`, merge them, and
    run the exhaustiveness (THREAT001-003/COMPLIANCE001-002) plus
    self-conformance (SYS100-102) checks `frob sys audit` runs -- in
    process, no subprocess, no `[[test.runner]]` entry required. `Ok` with
    `proved=True` and no models is the same vacuous-but-honest "nothing to
    check yet" posture `frob sys audit` itself takes (T-0163's doctrine:
    never a fabricated failure, but also never silently skipped -- the
    summary says so explicitly)."""
    ids = load_design_ids(root, design_dir)
    if ids.errors:
        detail = "; ".join(f"{e.path}: {e.error}" for e in ids.errors)
        _log.error(
            "native sys audit: %d design file(s) failed to load: %s",
            len(ids.errors),
            detail,
        )
        return Err(StrataError.ParseFailed)
    if not ids.models:
        _log.info(
            "native sys audit: no design models under %s/%s -- nothing to audit",
            root,
            design_dir,
        )
        return Ok(
            NativeAuditOutcome(proved=True, summary="no .strata design models found")
        )

    model = merge_models(ids.models)

    repo_benign = load_repo_benign_capabilities(root)
    if repo_benign.is_err:
        _log.error("native sys audit: %s", repo_benign.danger_err)
        return Err(repo_benign.danger_err)
    benign = DEFAULT_BENIGN_CAPABILITIES + repo_benign.danger_ok

    audited = evaluate_exhaustiveness(model, benign=benign)
    if audited.is_err:
        _log.error("native sys audit: %s", audited.danger_err)
        return Err(audited.danger_err)

    selfconform = check_self_conformance(model, root)
    if selfconform.is_err:
        _log.error("native sys audit: self-conformance: %s", selfconform.danger_err)
        return Err(selfconform.danger_err)

    report = audited.danger_ok
    conform = selfconform.danger_ok
    proved = report.proved and not conform.violations
    summary = _summarize(report, conform)
    _log.info(
        "native sys audit: proved=%s gaps=%d selfconform_gaps=%d",
        proved,
        len(report.gaps),
        len(conform.violations),
    )
    return Ok(NativeAuditOutcome(proved=proved, summary=summary))


__all__ = ["NativeAuditOutcome", "run_native_sys_audit"]
