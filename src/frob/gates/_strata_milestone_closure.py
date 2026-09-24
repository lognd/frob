"""frob.gates._strata_milestone_closure -- MSCLOSE001, milestone-scoped
V-model closure over a configuration binding (T-3010, T-3004 section 6).

`frob.gates._vmodel.vmodel_gate` (T-3042) already checks whether the WHOLE
V-model graph is structurally closed. T-3004 section 6's incremental-
release model needs a weaker, opt-in question over the SAME graph: for
one named milestone, is every `artifact` obligation either covered (has
an incoming `verifies` edge, same test `check_no_untested_artifact`
already runs) or DECLARED as a known gap -- never merely silent about it?

This module generalises `frob.lang._support`'s `FacetState.KNOWN_GAP`
registry pattern (a `(language, facet)` cell is `IMPLEMENTED`/
`NOT_APPLICABLE`/`KNOWN_GAP`, never silently absent) from language-
conformance facets to V-model artifact obligations: `MilestoneGap` is the
`FacetStatus` analog (a `reason` is required, mirroring `FacetStatus.
detail`'s non-empty rule), and `MILESTONE_GAP_REGISTRY` is the
`(milestone, node_id) -> MilestoneGap` accounting table a caller edits by
hand -- the same shape `KNOWN_GAP_TRACKING_TICKETS` gives language
facets, just keyed on a milestone name and a vmodel artifact id instead
of a language and a capability.

The actual closure computation happens in Rust
(`strata_core.milestone_closure_check`, T-3010's PyO3 export mirroring
`vmodel_check`'s existing shape) over the same aggregated
`vmodel_node`/`vmodel_edge` graph `vmodel_gate` builds --
`_collect_milestone_graph` below reuses `frob.gates._vmodel`'s own
collector rather than re-parsing every `.strata` file a second time.

SEVERITY: WARN, matching VMOD001's own severity rationale (T-3042's
ticket body) -- frob has no real milestone-scoped V-model graph of its
own yet, so an ERROR-severity rule here would just get waived away
wholesale before any real milestone binding exists to check.
"""

# frob:ticket T-3010

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.gates._models import Severity, Violation
from frob.gates._vmodel import _collect_vmodel_graph, _design_dir, _strata_files
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/strata/vmodel.md#incremental-releases-milestone-scoped-closure-t-3010
def _repo_milestone(root: Path) -> str:
    """`[tickets].default_milestone` from `frob.toml`, or `""` when
    unset/unreadable -- the milestone name `milestone_closure_gate`'s
    `frob check` call site checks gaps against when no explicit milestone
    is given. Deliberately re-derived here rather than importing
    `frob.tickets._doable._default_milestone` (a private symbol in a
    different subsystem this gate has no other reason to depend on) --
    the same narrow-duplication call `_vmodel.py`'s own `_design_dir`
    docstring already makes for `frob.strata._design_load`'s identical
    constant."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return ""
    try:
        with toml_path.open("rb") as handle:
            value = tomllib.load(handle).get("tickets", {}).get("default_milestone", "")
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("milestone_closure_gate: default_milestone unreadable: %s", exc)
        return ""
    return value if isinstance(value, str) else ""


# frob:doc docs/strata/vmodel.md#incremental-releases-milestone-scoped-closure-t-3010
class MilestoneGap(BaseModel):
    """One `(milestone, artifact node id)` known-gap cell: the reason this
    obligation is deliberately uncovered for this milestone, generalising
    `frob.lang._support.FacetStatus`'s non-empty-`detail` discipline to
    V-model artifacts -- a `MilestoneGap` with a blank `reason` is refused
    by `_milestone_gap_node_ids` below, the same way a blank `FacetStatus.
    detail` is flagged by `conformance_violations`."""

    model_config = ConfigDict(frozen=True)

    #: Free-text justification naming the tracking ticket, e.g. "T-1234:
    #: cheap storage architecture defers durability until the fast tier
    #: milestone." Required non-empty -- a gap with no reason is exactly
    #: as unaccountable as silent omission.
    reason: str


#: `(milestone name) -> {artifact node id: MilestoneGap}` -- the hand-
#: edited accounting table this gate checks every uncovered obligation
#: against, generalising `frob.lang._support.KNOWN_GAP_TRACKING_TICKETS`'s
#: per-language registry to per-milestone V-model obligations. Empty by
#: default: frob declares no milestone-scoped vmodel graph of its own
#: yet (same posture `vmodel_gate`'s zero-nodes early-return documents).
# frob:doc docs/strata/vmodel.md#incremental-releases-milestone-scoped-closure-t-3010
MILESTONE_GAP_REGISTRY: dict[str, dict[str, MilestoneGap]] = {}


# frob:doc docs/strata/vmodel.md#incremental-releases-milestone-scoped-closure-t-3010
# tests/gates/test_milestone_closure.py::TestMilestoneGapNodeIds:: \
# test_refuses_a_blank_reason
def _milestone_gap_node_ids(milestone: str) -> frozenset[str]:
    """Every artifact node id `MILESTONE_GAP_REGISTRY[milestone]` names,
    once every entry's `reason` is confirmed non-blank -- a blank reason
    is treated as NOT a declared gap (falls through to MSCLOSE001 firing
    on that node), the same "unreasoned cell is unaccounted for" rule
    `frob.lang._support._unreasoned_names` already enforces for language
    facets."""
    gaps = MILESTONE_GAP_REGISTRY.get(milestone, {})
    accounted = frozenset(
        node_id for node_id, gap in gaps.items() if gap.reason.strip()
    )
    unreasoned = frozenset(gaps) - accounted
    if unreasoned:
        _log.warning(
            "milestone_closure_gate: milestone %r declares blank-reason gap(s) %s -- "
            "treated as NOT gapped (MSCLOSE001 will fire on them)",
            milestone,
            sorted(unreasoned),
        )
    return accounted


# frob:doc docs/strata/vmodel.md#incremental-releases-milestone-scoped-closure-t-3010
# tests/gates/test_milestone_closure.py::TestMilestoneClosureGate:: \
# test_fires_msclose001_on_an_ungapped_uncovered_obligation
# frob:enforces CHK-GATE-MSCLOSE001
def milestone_closure_gate(
    root: Path, milestone: str | None = None
) -> tuple[Violation, ...]:
    """MSCLOSE001 (WARN): every `artifact` node in the V-model graph
    aggregated from every `.strata` file under the repo's design dir that
    has neither a `verifies` edge nor a declared `MILESTONE_GAP_REGISTRY`
    entry for `milestone`.

    Opt-in the same two ways `vmodel_gate` is (T-0135 posture): no design
    dir, or a design dir with zero `vmodel_node` declarations, produces
    nothing. `milestone` selects which `MILESTONE_GAP_REGISTRY` row this
    run's gaps come from -- an empty/unknown milestone name is legal and
    simply means no gaps are declared, so every uncovered artifact fires.
    Defaults to `_repo_milestone(root)` (`[tickets].default_milestone`)
    when not given, so `frob check`'s own call site never has to resolve
    it itself.
    """
    if milestone is None:
        milestone = _repo_milestone(root)
    design_dir = root / _design_dir(root)
    paths = _strata_files(root, design_dir)
    if not paths:
        _log.debug(
            "milestone_closure_gate: no .strata files under %s, skipping", design_dir
        )
        return ()

    nodes, edges, node_file = _collect_vmodel_graph(paths)
    if not nodes:
        _log.debug(
            "milestone_closure_gate: no vmodel_node declarations found, skipping"
        )
        return ()

    import strata_core

    known_gaps = sorted(_milestone_gap_node_ids(milestone))
    errors, uncovered = strata_core.milestone_closure_check(nodes, edges, known_gaps)
    _log.info(
        "milestone_closure_gate: milestone=%r checked %d node(s), %d edge(s) -- "
        "%d construction error(s), %d uncovered obligation(s), %d declared gap(s)",
        milestone,
        len(nodes),
        len(edges),
        len(errors),
        len(uncovered),
        len(known_gaps),
    )

    violations: list[Violation] = []
    for detail in errors:
        violations.append(
            Violation(
                rule="MSCLOSE001",
                severity=Severity.WARN,
                file=str(design_dir),
                line=0,
                message=(
                    f"MSCLOSE001: milestone {milestone!r} V-model graph "
                    f"construction error: {detail} -- fix the offending "
                    f"vmodel_node/vmodel_edge statement"
                ),
            )
        )
    for node_id in uncovered:
        violations.append(
            Violation(
                rule="MSCLOSE001",
                severity=Severity.WARN,
                file=node_file.get(node_id, str(design_dir)),
                line=0,
                message=(
                    f"MSCLOSE001: milestone {milestone!r} obligation "
                    f"{node_id!r} is neither covered by a verifying test nor "
                    f"declared in MILESTONE_GAP_REGISTRY -- either add coverage "
                    f"or a reasoned MilestoneGap entry naming the tracking "
                    f"ticket, see docs/strata/vmodel.md#incremental-releases-"
                    f"milestone-scoped-closure-t-3010"
                ),
            )
        )
    return tuple(violations)


__all__ = ["MilestoneGap", "MILESTONE_GAP_REGISTRY", "milestone_closure_gate"]
