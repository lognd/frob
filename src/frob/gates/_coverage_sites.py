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

FAMILIES INSTRUMENTED TODAY (T-1943): `"archgate"` (`frob.gates._arch.
arch_examined_sites`, keyed to the same name `--only archgate`/
`_build_process_jobs` already use for this gate), plus `"perf"`,
`"strata"`, `"graph"`, and `"vet"` (this module's own `_perf_examined_
sites`/`_strata_examined_sites`/`_graph_examined_sites`/`_vet_examined_
sites` -- T-1904's own investigation named these four as the families
the 55-waiver incident actually hit). Every OTHER family (the rest of
`frob.gates.__init__`'s ~40 gates) stays deliberately uninstrumented --
this substrate's honest "not instrumented" signal for anything not
listed here, per T-1921's original scope cut. `attach_examined_sites` is
written so adding one more family is a one-line addition to
`_FAMILY_REPORTERS`, not a redesign.

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
        # T-1943: extend coverage from archgate-only to the four families
        # T-1904's own investigation named as the ones the 55-waiver
        # incident actually hit (strata/perf/graph/vet). Each reporter
        # below is defined in THIS module rather than in its own family's
        # gate module, matching T-1943's own narrowed scope (this file
        # only) -- unlike arch_examined_sites (which lives beside arch_gate
        # in frob.gates._arch), these four re-derive their family's real
        # success/failure per-site outcome directly from that family's own
        # public/lazy-imported primitives, never from a raw walk's
        # candidate list.
        _FAMILY_REPORTERS["perf"] = _perf_examined_sites
        _FAMILY_REPORTERS["strata"] = _strata_examined_sites
        _FAMILY_REPORTERS["graph"] = _graph_examined_sites
        _FAMILY_REPORTERS["vet"] = _vet_examined_sites
    return _FAMILY_REPORTERS


# frob:ticket T-1943
# frob:waive WIRE001 reason="PERF reporter, substrate-only per T-1921's own \
# arch_examined_sites precedent -- shipping a coverage-substrate reporter and its \
# WAIVE004 consumer in the same diff is the exact shape the 55-waiver incident grew \
# from, per the coordinator's standing instruction. T-2011 tracks wiring \
# this (and its three siblings) into a real guard" follow_up="T-2011"
# frob:waive COV005 reason="T-1943: this is a brand-new private function, not a helper \
# extracted above attach_examined_sites/site_examined -- COV005's (kind, \
# target)=(waive, 'WIRE001') key is shared by every WIRE001 waiver in this file, so \
# adding a fourth, independent WIRE001 waiver on a genuinely new private symbol looks \
# identical to a rebind even though nothing moved"
def _perf_examined_sites(root: Path) -> frozenset[str]:
    """T-1943: the per-site analysis-coverage substrate's PERF-family
    reporter -- the repo-relative file paths this call's own
    `frob.lang.parse_file` attempt actually succeeded on, restricted to
    the same scannable-extension candidate set `frob.gates.__init__.
    perf_gate`'s own `_perf_gate_candidate_paths` computes (files with no
    registered tree-sitter grammar are unscannable by design and were
    never real candidates). A file that IS a candidate but fails to parse
    (`parse_file` returns `Err`, the same outcome `perf_gate`'s own
    `_perf_gate_parse_files` skips with a logged warning) is excluded here
    too -- "was in the walk" is never enough, only a real parse success
    counts, the same honesty bar `arch_examined_sites` holds itself to.

    Re-derives the candidate set from `frob.excludes.iter_files` rather
    than threading `perf_gate`'s own `GraphSnapshot` through, so this
    reporter stays a standalone `(root) -> frozenset[str]` call like every
    other family reporter here -- one real parse pass per file, not a
    cache hit off `perf_gate`'s own run, but the same cost profile
    `arch_examined_sites`'s own docstring already accepts for an
    out-of-band caller."""
    from frob import excludes as _excludes
    from frob.lang import parse_file, tree_sitter_extensions

    scannable = tree_sitter_extensions()
    examined: set[str] = set()
    for path in _excludes.iter_files(root):
        if path.suffix.lower() not in scannable:
            continue
        rel = path.relative_to(root).as_posix()
        result = parse_file(path)
        if result.is_err:
            _log.debug("_perf_examined_sites: skipping unparsed %s", rel)
            continue
        examined.add(rel)
    return frozenset(examined)


# frob:ticket T-1943
# frob:waive WIRE001 reason="STRATA reporter, same substrate-only posture as its three \
# siblings in this module -- no production caller wired here, deliberately, until \
# T-2011 (open) does the wiring the way T-1942 already did for archgate" \
# follow_up="T-2011"
# frob:waive COV005 reason="T-1943: brand-new private function, not a helper extracted \
# from a public def -- see _perf_examined_sites's own COV005 waiver above for the full \
# explanation of why this file's shared WIRE001 target triggers a false rebind read"
def _strata_examined_sites(root: Path) -> frozenset[str]:
    """T-1943: the per-site analysis-coverage substrate's STRATA-family
    reporter -- the repo-relative `.strata` file paths this call's own
    read+parse attempt actually succeeded on, out of the same candidate
    set `frob.strata.load_design_ids` itself walks
    (`frob.strata._design_load._strata_files`, `[graph].exclude`-filtered
    the same way `load_design_ids` filters it). A file that fails to read
    or parse (`_parse_one_design_file` returning a `DesignLoadError`, the
    exact outcome `load_design_ids`'s own `.errors` collects) is excluded
    -- being a candidate is not being examined, the same distinction every
    other reporter in this module holds to. Cross-file elaboration
    failures (`_load_all_design_files`'s `elaborate_merged` step) are
    deliberately NOT treated as un-examining every file: elaboration is a
    separate, whole-graph concern from "did this specific file's own text
    get read and parsed", the question this substrate exists to answer."""
    from frob.excludes import load_exclude_globs
    from frob.strata._design_load import (
        DEFAULT_DESIGN_DIR,
        _parse_one_design_file,
        _strata_files,
    )

    design_dir = root / DEFAULT_DESIGN_DIR
    exclude_globs = load_exclude_globs(root)
    paths = _strata_files(root, design_dir, exclude_globs)
    examined: set[str] = set()
    for path in paths:
        rel, module, error = _parse_one_design_file(root, path)
        if error is not None:
            _log.debug("_strata_examined_sites: skipping unparsed %s", rel)
            continue
        examined.add(rel)
    return frozenset(examined)


# frob:ticket T-1943
# frob:waive WIRE001 reason="GRAPH reporter, no production caller yet -- kept \
# substrate-only per T-1921's own precedent rather than wiring a consumer in this same \
# diff. Open follow-up T-2011 covers wiring this reporter (and its three \
# siblings) into WAIVE004" follow_up="T-2011"
# frob:waive COV005 reason="T-1943: brand-new private function, not a helper extracted \
# from a public def -- see _perf_examined_sites's own COV005 waiver above for the full \
# explanation of why this file's shared WIRE001 target triggers a false rebind read"
def _graph_examined_sites(root: Path) -> frozenset[str]:
    """T-1943: the per-site analysis-coverage substrate's GRAPH-family
    reporter -- `frob.graph.build_graph`'s own `GraphSnapshot.file_hashes`
    keys, the repo-relative paths the obligation-graph build actually
    parsed and hashed this run. `file_hashes` is populated only for a file
    that was successfully read/parsed/hashed (a read or parse failure is
    tracked separately in `GraphSnapshot.parse_failures` and never gains a
    `file_hashes` entry) -- the same real success/failure distinction
    every other reporter in this module holds to, here for free from
    `build_graph`'s own return shape rather than re-derived by hand.
    `build_graph` is memoized per `frob check` run (T-0423), so a call
    against the same `(root, cache)` `frob.gates.__init__`'s own `sys`/
    `refs`/`registry` dispatch already made this run is a cache hit, not a
    second graph build; a standalone caller pays one real build, the same
    cost profile `arch_examined_sites`'s own docstring accepts for an
    out-of-band caller. A build failure (`Result.is_err` -- unreadable or
    corrupt cache) reports the empty set, never a stale/partial claim."""
    from frob.graph import build_graph

    cache = root / ".frob" / "cache.db"
    result = build_graph(root, cache)
    if result.is_err:
        _log.warning(
            "_graph_examined_sites: build_graph failed: %s", result.danger_err
        )
        return frozenset()
    return frozenset(result.danger_ok.file_hashes)


# frob:ticket T-1943
# frob:waive WIRE001 reason="VET reporter -- last of the four T-1943 substrate-only \
# additions, no production caller wired in this diff. T-2011 is the open \
# ticket that wires this and its siblings into a real WAIVE004 guard" \
# follow_up="T-2011"
# frob:waive COV005 reason="T-1943: brand-new private function, not a helper extracted \
# from a public def -- see _perf_examined_sites's own COV005 waiver above for the full \
# explanation of why this file's shared WIRE001 target triggers a false rebind read"
def _vet_examined_sites(root: Path) -> frozenset[str]:
    """T-1943: the per-site analysis-coverage substrate's VET-family
    reporter -- the repo-relative file paths `frob.vet._capability.
    scan_file_capabilities` (the OPAQUE001/CVE-fingerprint gates' own
    per-file capability scanner) could actually scan this run: a real
    registered capability-pattern language (`frob.vet._capability.
    language_for(path) is not None`) that exists as an ordinary file this
    run. A file with no capability-pattern table for its language is
    excluded -- `scan_file_capabilities`'s own docstring notes it silently
    returns the empty token set for that case too, exactly the "was in
    the walk but never really examined" shape this substrate exists to
    distinguish; checking language support explicitly here rather than
    trusting an empty return from `scan_file_capabilities` itself keeps
    that distinction honest (an empty return is ALSO the correct, common
    outcome for a genuinely examined file with zero capability hits).
    Deliberately a metadata-only `is_file()` check, not a content read
    (`scan_file_capabilities` itself is the only real reader in this
    path) -- this reporter's job is choosing the candidate set, not
    duplicating the scan a real caller would perform."""
    from frob import excludes as _excludes
    from frob.vet._capability import language_for

    examined: set[str] = set()
    for path in _excludes.iter_files(root):
        if language_for(path) is None:
            continue
        if not path.is_file():
            _log.debug("_vet_examined_sites: not a regular file: %s", path)
            continue
        examined.add(path.relative_to(root).as_posix())
    return frozenset(examined)


# frob:doc docs/modules/gates.md#data-models
# frob:ticket T-1921
# frob:waive WIRE001 reason="T-1942 wired this as a real production caller \
# (frob.gates._fix_engine_sync._waive004_verified_candidates enriches its \
# self-manufactured run_gates() report via this function before deriving WAIVE004 \
# candidates) -- kept as an explicit waiver rather than removed because static \
# call-graph analysis of that dynamic-report-construction call site is fragile. \
# follow_up re-pointed to T-2011 (the open ticket wiring perf/strata/graph/ \
# vet examined-sites into WAIVE004) since WIRE002 requires a live open ticket \
# citation, not because that ticket is expected to remove this waiver itself" \
# follow_up="T-2011"
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
# frob:waive WIRE001 reason="still substrate-only -- unlike attach_examined_sites and \
# site_examined (both wired into frob.gates._fix_engine_sync by T-1942), no production \
# caller has been added for this specific diagnostic accessor yet. T-2011 \
# wires perf/strata/graph/vet examined-sites into WAIVE004 and is the most likely next \
# ticket to touch this module; follow_up points there to satisfy WIRE002's \
# live-open-ticket requirement, not because that ticket is expected to wire a caller \
# in" follow_up="T-2011"
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
# frob:waive WIRE001 reason="T-1942 wired this as a real production caller \
# (frob.gates._fix_engine_sync._drop_unexamined_archgate_candidates calls this \
# directly to decide whether a WAIVE004 candidate's site was actually examined this \
# run) -- kept as an explicit waiver rather than removed for the same fragile \
# dynamic-call-site reason as attach_examined_sites above. follow_up re-pointed to \
# T-2011 (the open ticket wiring perf/strata/graph/vet examined-sites into \
# WAIVE004) since WIRE002 requires a live open ticket citation, not because that \
# ticket is expected to remove this waiver itself" follow_up="T-2011"
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
