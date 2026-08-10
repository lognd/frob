"""frob.gates._coverage_sites -- per-site analysis-coverage substrate (T-1921).

T-1904 (successor of the falsified T-1579 WAIVE004 escape) established
that "the rule fired somewhere in this run" is unsound proof that a
SPECIFIC waived site was re-analyzed -- `_rule_has_live_finding` shipped
on exactly that reasoning once and deleted 55 live waivers, because a
partially-degraded run can satisfy "the rule fired somewhere" while
missing the exact sites its waivers cover. `GateReport`/`GateStats`
(`frob.gates._models`) carried no notion of "which sites did gate X
actually examine this run" at all; this module is the substrate that
adds one, honestly.

THE ONE PROPERTY THAT MATTERS: it must be impossible for a site the
analysis did not cover to be reported as covered. Two distinct ways a
site can fail to be "examined", both of which `site_examined` below
must report as NOT examined:

  1. The site's gate FAMILY is not instrumented at all (no key in
     `GateStats.examined_sites`) -- this substrate makes no claim.
  2. The family IS instrumented, but this particular file was not a
     member of the examined set this run (skipped, unreadable, failed
     to parse, outside the scoped root, ...).

Querying `GateStats.examined_sites` directly with a plain `.get(family,
frozenset())` membership test CANNOT be trusted to preserve this,
because a caller doing so has no way to tell case (1) from "instrumented
and empty" without also separately checking `is_family_instrumented` --
an easy mistake to make once, with the exact same blast radius as the
original incident. `site_examined` is the one sanctioned way to ask the
question; every consumer should call it, never inline the dict lookup.

FAMILIES INSTRUMENTED TODAY: `"archgate"` only (`frob.gates._arch.
arch_examined_sites`, keyed to the same name `--only archgate`/
`_build_process_jobs` already use for this gate). Every other family
(strata/perf/graph/vet and the rest of `frob.gates.__init__`'s ~40
gates) is deliberately left uninstrumented -- T-1921's own scope cut,
matching the coordinator's explicit instruction not to claim broader
coverage than what is real. `attach_examined_sites` is written so adding
a second family later is a one-line addition to `_FAMILY_REPORTERS`,
not a redesign.

NOT WIRED INTO WAIVE004 (or any other auto-fix/waiver-retirement path)
by this ticket. T-1921's brief is explicit that shipping a consumer in
the same change that builds the substrate is how the 55-waiver incident
happened the first time -- `frob.gates._fix_engine_sync.
_drop_untrustworthy_mass_stale_candidates` is UNCHANGED by this module;
wiring a third, additive per-site check there is deliberately left as
later, separately reviewed work (see this module's own residue ticket
citation in `tickets.md`'s T-1921 Done report).

WHY THIS IS A POST-`run_gates` ENRICHMENT STEP, NOT BAKED INTO
`_assemble_gate_report`: threading a new output channel through every
gate family's own `Callable[[], tuple[Violation, ...]]` / `_ProcessJob`
dispatch shape in `frob.gates.__init__` would touch that module's core
job-assembly machinery -- exactly the "substrate change spanning dozens
of independent gate modules" T-1904's own investigation found
disproportionate for one ticket, and (concretely, this session) a file
under a live cross-worktree lease this ticket could not touch anyway.
`attach_examined_sites` instead re-derives coverage for each
instrumented family by calling that family's own reporter function
directly against the same `root` `run_gates` used -- for `archgate`,
`analyze_project` is memoized per run (T-0423), so this is a cache hit
when called against the same process/run, not a second tree walk; a
caller invoking it against a report built by SOME OTHER process (no
warm per-run memo) pays one real walk, same cost profile any other
on-demand `frob.gates._arch.arch_examined_sites` call already carries.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from frob.logging import get_logger

if TYPE_CHECKING:
    from frob.gates._models import GateReport, GateStats

_log = get_logger(__name__)

# frob:ticket T-1921
#: family name (matches the `--only <name>`/`_build_process_jobs`/
#: `_build_thread_jobs` key the gate is dispatched under in
#: `frob.gates.__init__`) -> a one-arg reporter returning the frozenset of
#: repo-relative paths that family examined against `root` this call. Add
#: a new family here, and ONLY here, to extend coverage --
#: `attach_examined_sites` itself needs no change.
_FAMILY_REPORTERS: dict[str, Callable[[Path], frozenset[str]]] = {}


# frob:ticket T-1921
def _load_family_reporters() -> dict[str, Callable[[Path], frozenset[str]]]:
    """Lazily builds `_FAMILY_REPORTERS`'s real contents on first use --
    a plain module-level import of `frob.gates._arch` at this module's
    top level would risk a cycle (`frob.gates.__init__` imports this
    module's sibling gate modules, which is exactly the import graph
    `frob.gates._arch` itself sits in); deferring the import to first
    call keeps this module importable standalone, matching every other
    lazy-import gate helper in this package."""
    if not _FAMILY_REPORTERS:
        from frob.gates._arch import arch_examined_sites

        _FAMILY_REPORTERS["archgate"] = arch_examined_sites
    return _FAMILY_REPORTERS


# frob:doc docs/modules/gates.md#data-models
# frob:ticket T-1921
# frob:waive WIRE001 reason="T-1921 is deliberately substrate-only -- no production \
# caller yet, per the coordinator's explicit instruction not to wire a consumer in the \
# same change that built the coverage substrate (the 55-waiver incident happened from \
# doing exactly that once). The follow-up ticket that wires a real WAIVE004 consumer \
# is the one that will call this from production code" follow_up="T-1942"
def attach_examined_sites(report: "GateReport", root: Path) -> "GateReport":
    """T-1921: returns a COPY of `report` whose `stats.examined_sites` is
    populated for every family `_load_family_reporters` knows how to
    report on (today: `archgate` only) -- every other family's key stays
    absent, the honest "not instrumented" signal `site_examined` depends
    on. Never mutates `report` in place (`GateStats`/`GateReport` are
    frozen pydantic models, `model_copy` is the only way to extend one).
    Safe to call more than once on the same report (each call recomputes
    from `root`, overwriting any keys it owns; keys some OTHER caller
    already attached for a family this module does not know about are
    preserved via the dict-merge below, never dropped)."""
    reporters = _load_family_reporters()
    merged = dict(report.stats.examined_sites)
    for family, reporter in reporters.items():
        try:
            merged[family] = reporter(root)
        except Exception:
            # T-1921: a reporter that raises is exactly the same shape as
            # "not instrumented" from this substrate's own soundness
            # contract -- never claim a family examined anything on the
            # strength of a call that itself failed. Logged, not raised:
            # `attach_examined_sites` is enrichment, and a broken
            # reporter must never take down the `frob check` run whose
            # report it was asked to enrich.
            _log.warning(
                "attach_examined_sites: %s reporter raised, treating as "
                "not-instrumented for this run",
                family,
                exc_info=True,
            )
            merged.pop(family, None)
    new_stats = report.stats.model_copy(update={"examined_sites": merged})
    return report.model_copy(update={"stats": new_stats})


# frob:doc docs/modules/gates.md#data-models
# frob:ticket T-1921
# frob:waive WIRE001 reason="T-1921 is deliberately substrate-only -- no production \
# caller yet, same reasoning as attach_examined_sites above; the follow-up \
# WAIVE004-wiring ticket is the first production consumer" follow_up="T-1942"
def is_family_instrumented(stats: "GateStats", family: str) -> bool:
    """T-1921: True iff `family` carries a real (possibly empty)
    examined-sites entry in `stats` -- distinguishes "this family reports
    honestly and found nothing" from "this substrate makes no claim about
    this family at all". Callers that only want the site-level yes/no
    answer should call `site_examined` instead; this exists for a caller
    that wants to distinguish the two NO cases explicitly (a diagnostic,
    or `attach_examined_sites`'s own merge logic)."""
    return family in stats.examined_sites


# frob:doc docs/modules/gates.md#data-models
# frob:ticket T-1921
# frob:waive WIRE001 reason="T-1921 is deliberately substrate-only -- no production \
# caller yet, same reasoning as attach_examined_sites above; the follow-up \
# WAIVE004-wiring ticket is the first production consumer" follow_up="T-1942"
def site_examined(stats: "GateStats", family: str, file: str) -> bool:
    """T-1921: THE single sanctioned way to ask "did this run's gate
    FAMILY actually examine FILE" -- returns False whenever either half
    of the soundness contract this module's docstring names is not met:
    `family` absent from `stats.examined_sites` (not instrumented at
    all), or `family` present but `file` not a member of its set
    (instrumented, and this run did not reach that file). Only ever
    returns True when a family's reporter positively recorded `file`
    this run. Never inline `file in stats.examined_sites.get(family,
    frozenset())` at a call site instead of this function -- it computes
    the identical value for the two failure cases above, but naming it
    here is what keeps the "absent means not-instrumented, never
    silently examined" contract auditable at one place instead of
    reimplemented (and potentially gotten wrong) at every consumer."""
    return file in stats.examined_sites.get(family, frozenset())


__all__ = ["attach_examined_sites", "is_family_instrumented", "site_examined"]
