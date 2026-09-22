"""frob.gates._inv -- INV00x invariant-coverage gate family (T-1188).

Split out of `frob.gates.__init__` (T-1072/T-1140/T-1159/T-1170/T-1174/
T-1183/T-1187/T-1188 one-family-per-land discipline, `_sys.py`'s T-1187
precedent) so the parent module can keep dropping toward the large-file
threshold without changing any public behavior. `invariant_gate`,
`inv003_gate`, and `inv004_gate` are re-exported from `frob.gates`
unchanged -- the names this family is externally imported by
(`run_gates`'s job table, `tests/test_gates.py`); every other symbol here
stays private to this module.

One cohesive family: INV001/INV002/INV005 (`invariant_gate`, declared-
invariant evidence/anchor/reachability checks) and INV003/INV004
(`inv003_gate`/`inv004_gate`, doc-side exclusivity/normative-claim
coverage) -- both share the same "does a `frob:invariant` claim have
standing evidence/anchor" shape, just applied to different claim sources
(declared invariants, spec docs).

T-1763: INV006 (the source-side sibling of INV003/INV004, `inv006_gate`)
was DELETED, not recalibrated -- measured against frob's own 349-file
corpus, it had produced 338 waiver directives and ZERO unwaived findings
across its entire lifetime (T-0408 onward). It was a purely LEXICAL
keyword scan (`find_exclusivity_claims` against "never"/"only"/"always"
prose) with no notion of symbol/cross-module scope, unlike INV003/INV004
(which stay doc-scoped and unaffected) -- it fired on ordinary descriptive
docstring prose about a module's OWN internals as readily as on a real
undeclared cross-module contract, and could not tell the two apart. It
had already fired on a waiver reason EXPLAINING a previous INV006 misfire
(T-1640) -- the rule consuming its own output as input. `frob:invariant`/
INV001/INV002 already bind real invariants to real evidence; INV006 added
338 hand-written waiver justifications on top for a detector that never
once produced a genuine unwaived finding. See docs/modules/gates.md's
T-1763 note for the full before/after measurement.

`_evidence_collected`/`_node_id_matches_symref` are generic evidence-
matching helpers that predate this split and stay defined in
`frob.gates.__init__` (shared with the TEST00x family there too) --
imported here lazily, inside the functions that need them, rather than
at module import time, since `frob.gates.__init__` itself imports this
module and a top-level import would be circular.
"""
# frob:ticket T-1188

from __future__ import annotations

import ast
import os
import re
from pathlib import Path

from frob.excludes import iter_files
from frob.gates._models import Severity, Violation
from frob.gates.invariants import (
    Invariant,
    find_exclusivity_claims,
    find_normative_claims,
)
from frob.graph import EdgeKind, GraphSnapshot
from frob.logging import get_logger
from frob.process._guard import ProcessGuardError, guarded_subprocess_run
from frob.process._pytest_spawn import resolve_pytest_argv
from frob.testing._models import CollectedTests

_log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Invariant gate
# ---------------------------------------------------------------------------


def _invariant_anchors(snapshot: GraphSnapshot) -> set[str]:
    """Invariant ids carrying a `frob:invariant` anchor edge in code."""
    return {e.target for e in snapshot.edges if e.kind == EdgeKind.INVARIANT}


# frob:ticket T-0543
def _invariant_anchor_symrefs(inv_id: str, snapshot: GraphSnapshot) -> set[str]:
    """The code symref(s) `inv_id` is anchored to via a `frob:invariant`
    edge (edge src -> the anchored symbol, edge target -> the invariant
    id)."""
    return {
        e.src
        for e in snapshot.edges
        if e.kind == EdgeKind.INVARIANT and e.target == inv_id
    }


# frob:ticket T-0543
def _evidence_binds_to_symrefs(
    evidence: str, symrefs: set[str], snapshot: GraphSnapshot
) -> bool:
    """Whether `evidence` (a pytest/cargo node id) is the test-side of some
    `TESTS` edge whose OTHER side is exactly one of `symrefs` -- reuses the
    same either-direction `TESTS`-edge walk `_evidence_binds_to_scope` (D-02,
    T-0398) uses to bind ticket evidence to a scope glob, here binding
    invariant evidence to the invariant's own anchor(s) instead (B12): a
    test that merely collects, with no edge reaching the anchored symbol at
    all, proves nothing about THIS invariant."""
    from frob.gates import _node_id_matches_symref  # noqa: PLC0415 -- breaks the
    # __init__ <-> _inv circular import (__init__ imports this module at its
    # own import time; _node_id_matches_symref is only needed once a gate
    # actually runs, by which point __init__ has finished loading).

    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS:
            continue
        for test_side, source_side in (
            (edge.src, edge.target),
            (edge.target, edge.src),
        ):
            if _node_id_matches_symref(evidence, test_side) and source_side in symrefs:
                return True
    return False


# frob:ticket T-0543
# frob:enforces CHK-GATE-INV005
def _inv005(inv: Invariant) -> Violation:
    """INV005: an invariant's collected evidence never shown (via a
    `frob:tests` edge or same-file trust) to reach its own `frob:invariant`
    anchor -- WARN, same best-effort posture as COV006, since this is a
    name/edge-based check that can miss a genuine but unconventionally
    bound test."""
    return Violation(
        rule="INV005",
        severity=Severity.WARN,
        file=inv.path,
        line=0,
        message=(
            f"INV005: {inv.id}'s evidence collects but is never shown to "
            f"reach its frob:invariant anchor; add a frob:tests edge from "
            f"the evidence test to the anchored symbol, or confirm it "
            f"genuinely exercises the invariant"
        ),
    )


def _invariant_evidence_proves_anchor(
    evidence: str, anchor_symrefs: set[str], snapshot: GraphSnapshot
) -> bool:
    """B12: whether `evidence` (already known to be a collected test node
    id) actually reaches the invariant's anchored symbol, not merely that
    SOME test collected somewhere in the repo. When the invariant has no
    anchor at all, this is vacuously satisfied -- INV002 already flags the
    missing-anchor case on its own, and there is nothing to bind against
    here. Two routes, mirroring `evidence_covers_scope`'s D-02 routes: (1)
    a `frob:tests` edge from this evidence to one of `anchor_symrefs`, or
    (2) the evidence's own file is the same file as an anchor (same-file
    binding, the same trust `evidence_covers_scope` extends when a
    ticket's scope already names the test file directly)."""
    if not anchor_symrefs:
        return True
    if _evidence_binds_to_symrefs(evidence, anchor_symrefs, snapshot):
        return True
    anchor_files = {a.split("::", 1)[0] for a in anchor_symrefs}
    return evidence.split("::", 1)[0] in anchor_files


# frob:waive DUP001 reason="sibling INV001/INV002 violation builders in the same \
# module: same tiny Violation(...)-building shape, independently-evolving rule codes"
# frob:enforces CHK-GATE-INV001
def _inv001(inv: Invariant) -> Violation:
    """INV001: an invariant with no standing evidence."""
    return Violation(
        rule="INV001",
        severity=Severity.ERROR,
        file=inv.path,
        line=0,
        message=(
            f"INV001: {inv.id} has no evidence resolving to a collected "
            f"test or loaded policy rule; add a passing test or POL rule "
            f"to its evidence list"
        ),
    )


# frob:waive DUP001 reason="sibling INV001/INV002 violation builders in the same \
# module: same tiny Violation(...)-building shape, independently-evolving rule codes"
# frob:enforces CHK-GATE-INV002
def _inv002(inv: Invariant) -> Violation:
    """INV002: an invariant with no code anchor."""
    return Violation(
        rule="INV002",
        severity=Severity.ERROR,
        file=inv.path,
        line=0,
        message=(
            f"INV002: {inv.id} has no frob:invariant anchor in code; "
            f"add: frob:invariant {inv.id} at the enforcing site"
        ),
    )


# frob:doc docs/modules/gates.md#public-api
def invariant_gate(
    invariants: tuple[Invariant, ...],
    snapshot: GraphSnapshot,
    tests: CollectedTests,
    policy_rule_ids: frozenset[str] = frozenset(),
) -> tuple[Violation, ...]:
    """INV001 (no evidence), INV002 (no code anchor), and INV005 (evidence
    collected but never shown to reach the anchor).

    **Deviation**: adds an optional `policy_rule_ids` parameter beyond
    docs/modules/gates.md's `(invariants, snapshot, tests)` signature so INV001 can
    treat a loaded policy rule id as valid evidence, per the doc's own
    evidence-list example (`POL-no-direct-lock-write`); without it there
    would be no way for this pure function to see policy state at all.

    B12 (T-0543): a collected test node id satisfies INV001 by mere
    EXISTENCE -- `def test_x(): pass` clears it regardless of whether the
    test reaches, let alone asserts against, the invariant's own anchored
    symbol. Tightening INV001 itself outright breaks a large slice of this
    repo's own already-adopted invariants (their evidence predates any
    edge/same-file binding convention; a legacy-adoption survey to add
    `frob:tests` edges or rebind evidence across all of them is out of this
    ticket's budget, same "large, needs its own pass" shape as B1/B6/B2).
    INV001/INV002 stay behaviorally unchanged (ERROR, ungated by binding);
    `_invariant_evidence_proves_anchor` instead feeds a new WARN-severity
    INV005 -- same non-blocking, best-effort posture as COV006's identical
    remedy family for `frob:tests` reachability -- so an agent adding a NEW
    invariant gets a loud nudge toward a real binding without a legacy
    INV001 mass-failure.
    """
    from frob.gates import _evidence_collected  # noqa: PLC0415 -- see module docstring

    anchors = _invariant_anchors(snapshot)
    violations: list[Violation] = []
    for inv in invariants:
        anchor_symrefs = _invariant_anchor_symrefs(inv.id, snapshot)
        collected_evidence = [
            item for item in inv.evidence if _evidence_collected(item, tests)
        ]
        has_evidence = bool(collected_evidence) or any(
            item in policy_rule_ids for item in inv.evidence
        )
        if not inv.evidence or not has_evidence:
            _log.debug("INV001: %s has no standing evidence", inv.id)
            violations.append(_inv001(inv))
        elif anchor_symrefs and not any(
            _invariant_evidence_proves_anchor(item, anchor_symrefs, snapshot)
            for item in collected_evidence
        ):
            _log.debug(
                "INV005: %s's collected evidence never shown to reach its anchor",
                inv.id,
            )
            violations.append(_inv005(inv))
        if inv.id not in anchors:
            _log.debug("INV002: %s has no code anchor", inv.id)
            violations.append(_inv002(inv))
    return tuple(violations)


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0462
_DOC_INVARIANT_MARKER_RE = re.compile(r"<!--\s*frob:invariant\s+(INV-\d{3})\s*-->")

# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0509
# Markdown-side waiver marker: `<!-- frob:waive INV003 reason="..." -->`.
# `_match_waiver` (the code-side waiver path) keys off graph edges, which
# doc prose carries none of -- this is a separate, file/section-scoped
# marker so a genuine-but-unprovable claim (prose describing a design
# intent rather than an enforced behavior) can be dispositioned honestly
# instead of either being hand-bound to a fake invariant or silently
# ignored. A missing/empty reason does not count as a waiver (same
# honesty requirement as `frob:waive`'s code-side WAIVE001).
_DOC_WAIVE_MARKER_RE = re.compile(
    r'<!--\s*frob:waive\s+(INV00[34])\s+reason="([^"]+)"\s*-->'
)

# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0522
# A reason consisting of nothing but a placeholder ellipsis (the literal
# `"..."` gates.md's own INV003/INV004 documentation necessarily spells
# out when it teaches the marker syntax by example) is not a real,
# specific reason -- treat it the same as an empty reason so a doc's
# ILLUSTRATIVE example of the waiver syntax cannot silently self-satisfy
# that same doc's own INV003/INV004 findings (T-0522).
_DOC_WAIVE_PLACEHOLDER_RE = re.compile(r"^\.{2,}$")

# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0509
# INV003 is scoped to these repo-relative directories (spec-normative
# design/module docs), not all of docs/**.md -- exclusivity claims worth
# gating live in the docs that describe enforced contracts; a narrative
# design doc or changelog making a passing "only" remark is not the same
# failure mode T-0462 named. INV004 (the coarser advisory signal) keeps
# scanning all of docs/ -- see `inv004_gate`.
INV003_SPEC_DIRS: tuple[str, ...] = ("docs/modules", "docs/strata")


# frob:ticket T-1649
def _spec_dir_md_files(root: Path) -> tuple[Path, ...]:
    """Every `.md` file under any `INV003_SPEC_DIRS` entry, one `iter_files`
    scan of `root` total (T-1649) -- the pre-fix shape both `inv003_gate`
    and `inv004_gate` shared called `iter_files` once PER `spec_dir`
    (PERF011: `INV003_SPEC_DIRS` is a fixed 2-entry tuple both callers
    already hold, so re-walking/re-`git ls-files`-ing the whole repo once
    per entry re-scans the same tree instead of filtering one scan's
    result by prefix)."""
    prefixes = tuple(f"{spec_dir}/" for spec_dir in INV003_SPEC_DIRS)
    return tuple(
        path
        for path in iter_files(root, suffix=".md")
        if path.relative_to(root).as_posix().startswith(prefixes)
    )


# frob:doc docs/modules/gates.md#invariants
# frob:waive COV007 reason="docs/modules/gates.md's Invariants section (INV003/INV004 \
# subsections) is a deliberate architecture doc walking through this exact helper's \
# design (T-0524), not a caller-side public-API summary"
# frob:ticket T-0509
def _file_has_reasoned_doc_waiver(path: Path, rule: str) -> bool:
    """True if `path` carries a `<!-- frob:waive <rule> reason="..." -->`
    marker anywhere in the file, with a non-empty reason.

    Deliberately NOT folded into `_inv003_doc_violations`'s own body: that
    function's `frob:ticket T-0462` directive is one of several bindings
    sharing that same ticket-id target across this file (T-0462 also
    covers `inv003_gate`, still public) -- COV005's rebind check matches
    old/new directive bindings by `(kind, target)` alone, so editing
    inside an already-ticket-tagged private helper whose target is shared
    with a public sibling elsewhere in the file spuriously reads as "this
    directive rode onto a new private symbol" even though nothing rebound.
    Applying the waiver filter from the (public, freshly-tagged) gate
    function instead avoids that false positive entirely.

    T-0522: a placeholder-ellipsis reason (`reason="..."`, the literal
    text gates.md's own INV003/INV004 sections necessarily spell out when
    they teach the marker syntax by illustrative example) does NOT count
    as a reasoned waiver -- without this, a doc that merely EXPLAINS the
    waiver syntax in prose silently self-waived its own findings, since
    the regex has no way to distinguish a real marker from an example one
    written in the same literal shape.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("%s: could not read %s for waiver check: %s", rule, path, exc)
        return False
    return any(
        matched_rule == rule and reason and not _DOC_WAIVE_PLACEHOLDER_RE.match(reason)
        for matched_rule, reason in _DOC_WAIVE_MARKER_RE.findall(text)
    )


# frob:doc docs/modules/gates.md#invariants
# frob:waive COV007 reason="docs/modules/gates.md's Invariants section (INV003 \
# subsection) is a deliberate architecture doc walking through this exact helper's \
# design (T-0524), not a caller-side public-API summary"
# frob:ticket T-0462
# frob:enforces CHK-GATE-INV003
def _inv003_doc_violations(
    root: Path, path: Path, known_ids: frozenset[str]
) -> tuple[Violation, ...]:
    """INV003 findings for one doc file: an exclusivity claim
    (`frob.gates.invariants.find_exclusivity_claims`) with no
    `<!-- frob:invariant INV-### -->` marker in the same file naming a
    REAL (loaded) invariant id.

    File-granularity, not per-section: a doc large enough to need
    section-level binding should already be split, and file granularity
    is enough to catch the actual failure mode this ticket names --
    prose asserting exclusivity with nothing tracking whether it still
    holds.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("INV003: could not read %s: %s", path, exc)
        return ()
    claims = find_exclusivity_claims(text)
    if not claims:
        return ()
    bound_ids = set(_DOC_INVARIANT_MARKER_RE.findall(text))
    if bound_ids & known_ids:
        return ()
    rel = path.relative_to(root).as_posix()
    return (
        Violation(
            rule="INV003",
            severity=Severity.WARN,
            file=rel,
            line=0,
            message=(
                f"INV003: {rel} makes an exclusivity/normative claim "
                f"({', '.join(sorted(claims))}) with no "
                f"`<!-- frob:invariant INV-### -->` marker in the file "
                f"naming a real invariant -- bind an invariant that "
                f"covers the claim, or reword to drop the exclusivity "
                f"language if it isn't actually enforced"
            ),
        ),
    )


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0462
def inv003_gate(root: Path, invariants: tuple[Invariant, ...]) -> tuple[Violation, ...]:
    """INV003: every exclusivity claim in a spec-normative doc
    (`INV003_SPEC_DIRS`) needs a bound invariant.

    T-0509: scoped to `INV003_SPEC_DIRS` (docs/modules, docs/strata), not
    all of docs/**.md -- exclusivity claims worth gating describe enforced
    contracts, which is what those two trees are for; a narrative design
    doc or changelog making a passing "only" remark is a different failure
    mode than T-0462 named. Combined with the stronger claim-shape scan
    (`find_exclusivity_claims`: noise-stripped, verb-bearing sentences
    only) and markdown-side `frob:waive` support (`_DOC_WAIVE_MARKER_RE`),
    this narrows the original ~765-warning INV003+INV004 pool to a
    genuinely reviewable set (T-0509's Done report has the exact counts).

    WARN severity (does not fail `frob check`), not ERROR like INV001/
    INV002: even after calibration, a claim can still be genuine design
    intent rather than an enforced behavior -- WARN surfaces the signal
    for human triage rather than forcing a bind-or-waive on every hit.
    """
    known_ids = frozenset(inv.id for inv in invariants)
    violations: list[Violation] = []
    for path in _spec_dir_md_files(root):
        file_violations = _inv003_doc_violations(root, path, known_ids)
        if file_violations and _file_has_reasoned_doc_waiver(path, "INV003"):
            _log.debug("INV003: %s waived by markdown frob:waive marker", path)
            continue
        violations.extend(file_violations)
    return tuple(violations)


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0452
_MD_HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)


# frob:doc docs/modules/gates.md#invariants
# frob:waive COV007 reason="docs/modules/gates.md's Invariants section (INV004 \
# subsection) is a deliberate architecture doc walking through this exact helper's \
# design (T-0524), not a caller-side public-API summary"
# frob:ticket T-0452
def _markdown_sections(text: str) -> tuple[str, ...]:
    """Split `text` into ATX-heading-delimited sections (each section runs
    from one `#`-line up to, but not including, the next); a file with no
    heading at all is one whole-file section.

    Coarser than a full outline (T-0452's density signal doesn't need
    heading level/nesting, just "a chunk of prose"), so this is a plain
    split on heading boundaries rather than a hierarchical tree.
    """
    starts = [m.start() for m in _MD_HEADING_RE.finditer(text)]
    if not starts:
        return (text,) if text.strip() else ()
    bounds = [*starts, len(text)]
    return tuple(text[bounds[i] : bounds[i + 1]] for i in range(len(starts)))


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0515
# frob:waive COV007 reason="docs/modules/gates.md's Invariants section (INV004 \
# subsection) is a deliberate architecture doc walking through this exact helper's \
# design (T-0524), not a caller-side public-API summary"
# frob:enforces CHK-GATE-INV004
def _inv004_doc_violations(root: Path, path: Path) -> tuple[Violation, ...]:
    """INV004 findings for one doc file: at least one section uses
    normative language (`frob.gates.invariants.find_normative_claims`)
    while the FILE AS A WHOLE anchors ZERO `<!-- frob:invariant INV-###
    -->` markers.

    T-0515: file-granularity, not per-section -- the original T-0452
    per-section scan produced 573 warnings (mostly many hits per file for
    docs that are entirely unbound rather than 573 distinct under-
    specified regions), overwhelming any real triage. This mirrors
    `_inv003_doc_violations`'s already-established per-file rationale: a
    doc large enough to need section-level tracking should already be
    split into `invariants/INV-###.md` entries, so one advisory per file
    carries the same signal (some claim in this doc is unbound) without
    the noise of one line per section.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("INV004: could not read %s: %s", path, exc)
        return ()
    if _DOC_INVARIANT_MARKER_RE.search(text) is not None:
        return ()
    rel = path.relative_to(root).as_posix()
    all_claims: set[str] = set()
    first_heading: str | None = None
    for section in _markdown_sections(text):
        claims = find_normative_claims(section)
        if not claims:
            continue
        all_claims.update(claims)
        if first_heading is None:
            heading_match = re.match(r"^(#{1,6}\s.*)$", section, re.MULTILINE)
            first_heading = (
                heading_match.group(1).strip() if heading_match else "(no heading)"
            )
    if not all_claims:
        return ()
    return (
        Violation(
            rule="INV004",
            severity=Severity.WARN,
            file=rel,
            line=0,
            message=(
                f"INV004: {rel} describes behavior "
                f"({', '.join(sorted(all_claims))}), first at section "
                f"{first_heading!r}, but anchors zero `<!-- "
                f"frob:invariant INV-### -->` markers anywhere in the "
                f"file -- likely under-specified; add an "
                f"`invariants/INV-###.md` plus a marker if the behavior "
                f"is meant to be guaranteed"
            ),
        ),
    )


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0515
def inv004_gate(root: Path) -> tuple[Violation, ...]:
    """INV004 (advisory): a doc file under `INV003_SPEC_DIRS` that
    describes behavior (normative language) but anchors zero invariants
    at all, file-granularity (T-0515).

    T-0515: scoped to `INV003_SPEC_DIRS` (docs/modules, docs/strata), not
    all of `docs/**.md` -- matching INV003's T-0509 rationale, a narrative
    design/audit/guide doc using "must"/"always" in passing is a
    different failure mode than an enforced-contract doc with no bound
    invariants at all. Always WARN -- under-specification is a suggestion
    to formalize, not a broken obligation; never fails `frob check`.
    """
    violations: list[Violation] = []
    for path in _spec_dir_md_files(root):
        file_violations = _inv004_doc_violations(root, path)
        if file_violations and _file_has_reasoned_doc_waiver(path, "INV004"):
            _log.debug("INV004: %s waived by markdown frob:waive marker", path)
            continue
        violations.extend(file_violations)
    return tuple(violations)


# ---------------------------------------------------------------------------
# INV010: time-stable invariants (T-4221, F-362/H4-1)
# ---------------------------------------------------------------------------

#: The ONE shared contract between `time_stable_gate` and any test bound
#: to a `frob:invariant ... kind="time-stable"` anchor: the runner sets
#: this env var to an integer offset (seconds) before spawning the test,
#: and the test itself must consult it -- via `time_stable_offset_s()`
#: below, or by reading the env var directly -- when it computes "now",
#: instead of calling `time.time()`/`datetime.now()` unconditionally. A
#: test with no time-stable anchor never needs to read it at all.
# frob:ticket T-4221
# frob:doc docs/modules/gate-time-stable-invariant.md#inv010-t-4221
TIME_STABLE_OFFSET_ENV = "FROB_TIME_STABLE_OFFSET_S"

#: `horizon="<N><unit>"`'s unit-to-seconds table (T-4221) -- matches
#: `frob.graph.dsl._HORIZON_RE`'s grammar exactly (that regex is this
#: table's own validation; a unit accepted there and missing here would
#: be a silent split-brain between the two).
# frob:ticket T-4221
_HORIZON_UNIT_SECONDS: dict[str, int] = {
    "d": 86_400,
    "w": 7 * 86_400,
    "m": 30 * 86_400,
    "y": 365 * 86_400,
}

#: Fraction of the declared horizon sampled at the MIDPOINT, in addition
#: to 0 (today) and the full horizon itself (T-4221: "at any sampled
#: point", plural) -- three points catch a predicate that only breaks
#: partway across the horizon (e.g. a leap-year boundary), not only at
#: its two ends, while staying a fixed, cheap, O(1) sample count per
#: invariant rather than a sweep.
# frob:ticket T-4221
_TIME_STABLE_SAMPLE_FRACTIONS: tuple[float, ...] = (0.0, 0.5, 1.0)

#: One time-stable test run's own subprocess budget (T-4221) -- mirrors
#: `_bug_repro._BUG_REPRO_TIMEOUT_S`'s reasoning exactly: generous enough
#: for a small bound-evidence test, bounded so a hang cannot stall a
#: `frob check` run indefinitely.
# frob:ticket T-4221
_TIME_STABLE_TIMEOUT_S = 60.0


# frob:ticket T-4221
# frob:doc docs/modules/gate-time-stable-invariant.md#inv010-t-4221
def time_stable_offset_s() -> int:
    """The current process's own time-stable clock offset, in seconds
    (`TIME_STABLE_OFFSET_ENV`, default `0`) -- the one function a test
    bound to a `frob:invariant ... kind="time-stable"` anchor calls
    wherever it would otherwise call `time.time()`/`datetime.now()` for
    "now", so `time_stable_gate` can advance its clock by re-spawning it
    with the env var set, with no other coordination needed between the
    runner and the test."""
    raw = os.environ.get(TIME_STABLE_OFFSET_ENV, "0")
    try:
        return int(raw)
    except ValueError:
        _log.warning(
            "time_stable: %s=%r is not an integer, treating as 0",
            TIME_STABLE_OFFSET_ENV,
            raw,
        )
        return 0


# frob:ticket T-4221
def _horizon_seconds(horizon: str) -> int | None:
    """`horizon` (already grammar-checked by `frob.graph.dsl._HORIZON_RE`
    at parse time -- this only re-derives the integer, it does not
    re-validate the shape) converted to seconds, or `None` if it somehow
    reaches here malformed (a directive `parse_directives` itself should
    already have rejected; defensive, never a raise)."""
    match = re.match(r"^(\d+)([dwmy])$", horizon)
    if match is None:
        return None
    return int(match.group(1)) * _HORIZON_UNIT_SECONDS[match.group(2)]


# frob:ticket T-4221
def _time_stable_anchors(
    snapshot: GraphSnapshot,
) -> tuple[tuple[str, str, int], ...]:
    """Every `(inv_id, anchor_symref, horizon_seconds)` triple for a
    `frob:invariant ... kind="time-stable" horizon="..."` edge in
    `snapshot` -- `EdgeKind.INVARIANT` edges whose `attrs` carry both
    (the grammar in `frob.graph.dsl` guarantees they are either both
    present and well-formed, or neither is present at all)."""
    found: list[tuple[str, str, int]] = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.INVARIANT:
            continue
        if edge.attrs.get("kind") != "time-stable":
            continue
        horizon = edge.attrs.get("horizon")
        if horizon is None:
            continue
        seconds = _horizon_seconds(horizon)
        if seconds is None:
            _log.warning(
                "time_stable: %s's horizon=%r failed to parse despite "
                "passing grammar validation -- skipping",
                edge.target,
                horizon,
            )
            continue
        found.append((edge.target, edge.src, seconds))
    return tuple(found)


# frob:ticket T-4221
def _spawn_time_stable_test(
    root: Path, test_id: str, offset_s: int
) -> tuple[bool, str] | None:
    """Run `test_id` under `root`'s own interpreter with
    `TIME_STABLE_OFFSET_ENV=offset_s`, mirroring `frob.gates._bug_repro.
    _spawn_designated_test`'s own `resolve_pytest_argv` +
    `guarded_subprocess_run` shape (same one-convention-for-pytest-
    spawning discipline, T-3311) but in-place (no worktree checkout --
    this is advancing the CLOCK, not the git ref).

    Returns `(passed, detail)` on any real exit, or `None` when no real
    exit was ever reached (exec disabled, pytest not importable, or the
    process hit its own timeout budget) -- `None` is `time_stable_gate`'s
    own signal to report UNRESOLVED for that sample rather than treating
    a could-not-run as either a pass or a fail."""
    resolved = resolve_pytest_argv(test_id, "-q", "-p", "no:cacheprovider")
    if resolved.is_err:
        _log.warning(
            "time_stable: %s -- no verdict for %s at offset=%ds",
            resolved.danger_err,
            test_id,
            offset_s,
        )
        return None
    env = dict(os.environ)
    env[TIME_STABLE_OFFSET_ENV] = str(offset_s)
    guarded = guarded_subprocess_run(
        resolved.danger_ok,
        cwd=str(root),
        capture_output=True,
        timeout=_TIME_STABLE_TIMEOUT_S,
        text=True,
        check=False,
        env=env,
    )
    if guarded.is_err:
        if guarded.danger_err is ProcessGuardError.Timeout:
            _log.warning(
                "time_stable: %s at offset=%ds exceeded its %gs budget -- no verdict",
                test_id,
                offset_s,
                _TIME_STABLE_TIMEOUT_S,
            )
        else:
            _log.warning(
                "time_stable: %s at offset=%ds -- %s, no verdict",
                test_id,
                offset_s,
                guarded.danger_err,
            )
        return None
    proc = guarded.danger_ok
    return (proc.returncode == 0, (proc.stdout or "") + (proc.stderr or ""))


# frob:ticket T-4221
def _time_stable_baseline_result(
    root: Path, inv_path: str, inv_id: str, evidence_id: str
) -> tuple[bool, Violation | None]:
    """T-4221: the offset-0 (today) run for one evidence id -- `None`
    means "skip this evidence id entirely" (could not measure at all,
    already reported as UNRESOLVED, or genuinely failing today and
    therefore not this gate's concern), else `(True, None)` meaning
    proceed to the later samples (split out of `time_stable_gate` to
    keep that function under ARCH001's long-AND-complex threshold,
    behavior unchanged)."""
    baseline = _spawn_time_stable_test(root, evidence_id, 0)
    if baseline is None:
        return False, Violation(
            rule="INV010",
            severity=Severity.UNRESOLVED,
            file=inv_path,
            line=0,
            message=(
                f"INV010: {inv_id}'s baseline run of "
                f"{evidence_id} could not be measured at all "
                f"(exec disabled, pytest not importable, or a "
                f"timeout) -- not a clean pass"
            ),
        )
    baseline_passed, _detail = baseline
    if not baseline_passed:
        _log.debug(
            "time_stable: %s's %s does not pass at offset=0, nothing to discharge here",
            inv_id,
            evidence_id,
        )
        return False, None
    return True, None


# frob:ticket T-4221
def _time_stable_sample_violation(
    root: Path,
    inv_path: str,
    inv_id: str,
    symref: str,
    evidence_id: str,
    horizon_s: int,
    offset_s: int,
) -> tuple[Violation | None, bool]:
    """T-4221: one post-baseline sample re-run -- returns the `Violation`
    to report (if any) and whether the sample run FAILED (so the caller's
    sample loop should stop early, matching the original break-on-first-
    failure behavior; split out of `time_stable_gate` to keep that
    function under ARCH001's long-AND-complex threshold)."""
    result = _spawn_time_stable_test(root, evidence_id, offset_s)
    if result is None:
        return (
            Violation(
                rule="INV010",
                severity=Severity.UNRESOLVED,
                file=inv_path,
                line=0,
                message=(
                    f"INV010: {inv_id}'s run of {evidence_id} "
                    f"at offset={offset_s}s (horizon={horizon_s}s) "
                    f"could not be measured at all -- not a "
                    f"clean pass"
                ),
            ),
            False,
        )
    passed, _detail = result
    if passed:
        return None, False
    _log.debug(
        "INV010: %s's %s fails at offset=%ds (horizon=%ds)",
        inv_id,
        evidence_id,
        offset_s,
        horizon_s,
    )
    return (
        Violation(
            rule="INV010",
            severity=Severity.WARN,
            file=inv_path,
            line=0,
            message=(
                f"INV010: {inv_id} (anchored at {symref}) "
                f"passes today but {evidence_id} fails once "
                f"the clock advances {offset_s}s into its "
                f"declared horizon={horizon_s}s -- a "
                f"wall-clock-dependent predicate that is "
                f"passing only because every sample so far "
                f"used the same instant for 'now' and the "
                f"artifact's own timestamp"
            ),
        ),
        True,
    )


# frob:ticket T-4221
def _time_stable_evidence_violations(
    root: Path,
    inv_path: str,
    inv_id: str,
    symref: str,
    evidence_id: str,
    horizon_s: int,
) -> list[Violation]:
    """T-4221: every INV010 violation for one evidence id across the
    baseline plus every post-baseline sampled offset (split out of
    `time_stable_gate` to keep that function under ARCH001's long-AND-
    complex threshold, per-evidence-id logic unchanged)."""
    ok, baseline_violation = _time_stable_baseline_result(
        root, inv_path, inv_id, evidence_id
    )
    if not ok:
        return [baseline_violation] if baseline_violation is not None else []
    found: list[Violation] = []
    for fraction in _TIME_STABLE_SAMPLE_FRACTIONS[1:]:
        offset_s = int(horizon_s * fraction)
        v, failed = _time_stable_sample_violation(
            root, inv_path, inv_id, symref, evidence_id, horizon_s, offset_s
        )
        if v is not None:
            found.append(v)
        if failed:
            break
    return found


# frob:ticket T-4221
# frob:enforces CHK-GATE-INV010
# frob:doc docs/modules/gate-time-stable-invariant.md#inv010-t-4221
def time_stable_gate(
    root: Path, invariants: tuple[Invariant, ...], snapshot: GraphSnapshot
) -> tuple[Violation, ...]:
    """INV010 (T-4221, F-362/H4-1): a `frob:invariant ... kind="time-
    stable" horizon="..."` anchor whose bound test does not still pass
    once the clock is advanced across the declared horizon.

    For each time-stable anchor, every collected evidence id belonging
    to the same invariant is re-run (`_spawn_time_stable_test`) at three
    sampled offsets across the horizon (`_TIME_STABLE_SAMPLE_FRACTIONS`:
    0, the midpoint, and the full horizon) with `TIME_STABLE_OFFSET_ENV`
    set to each sample's second count. The offset-0 run is the BASELINE:
    if it does not pass, this invariant has nothing to discharge here at
    all (INV001 already flags "no standing evidence" separately) and is
    skipped rather than double-reported. If the baseline passes but a
    later sample fails, that is exactly the "passes today, fails
    tomorrow" class this invariant kind exists to catch -- WARN severity
    (advisory, matching this repo's posture for every other newly-
    introduced, not-yet-repo-wide-calibrated gate this sprint), waivable
    with the standard `frob:waive INV010 reason="..."` directive.

    UNRESOLVED (not a silent pass) when a sample could not be measured
    at all (`_spawn_time_stable_test` returning `None` -- exec disabled,
    pytest not importable, or a subprocess timeout): the T-2391 fail-
    loudly doctrine this repo already applies elsewhere (ENV001's
    missing-pyproject case) -- a could-not-run answer is a different
    claim than "ran and found nothing.\""""
    known_ids = frozenset(inv.id for inv in invariants)
    by_id = {inv.id: inv for inv in invariants}
    violations: list[Violation] = []
    for inv_id, symref, horizon_s in _time_stable_anchors(snapshot):
        if inv_id not in known_ids:
            _log.debug(
                "time_stable: %s anchored at %s has no loaded invariant, skipping",
                inv_id,
                symref,
            )
            continue
        inv = by_id[inv_id]
        for evidence_id in inv.evidence:
            if "::" not in evidence_id:
                # T-4221: not a pytest node id (e.g. a POL-* policy rule
                # id) -- nothing this runner can spawn.
                continue
            violations.extend(
                _time_stable_evidence_violations(
                    root, inv.path, inv_id, symref, evidence_id, horizon_s
                )
            )
    return tuple(violations)


# ---------------------------------------------------------------------------
# RACE001 / RACE002 (T-3953, F-181/T-3942 item 7)
# ---------------------------------------------------------------------------

# T-3953: call/context-manager targets whose PRESENCE anywhere in a
# function is treated as "this read-then-write is already guarded" --
# a lock, a Lua/atomic script, an INCR-style single-op update, or a
# conditional/transactional UPDATE. Heuristic and deliberately generous
# (a false NEGATIVE here just means RACE001 stays silent, never a false
# claim) -- T-3919/T-3942's own audit caveat warns this shape gets waived
# into uselessness fast if it is not conservative about firing.
# frob:ticket T-3953
_RACE001_GUARD_RE = re.compile(
    r"lock|acquire|incr|watch|multi|pipeline|eval|atomic|transaction|cas\b",
    re.IGNORECASE,
)

# T-3953 (acceptance item 2): docstring vocabulary this repo's own audit
# named as the "spec claims single-writer-safe behavior" trigger.
# frob:ticket T-3953
_RACE002_CLAIM_RE = re.compile(r"\b(cap|quota|single-use|idempotent)\b", re.IGNORECASE)
# frob:ticket T-3953
_RACE002_CONCURRENT_TEST_RE = re.compile(
    r"concurrent|thread|race|parallel", re.IGNORECASE
)


# frob:ticket T-3953
def _race001_guard_present(func_node: ast.AST) -> bool:
    """True if `func_node`'s body mentions any lock/atomic-update-shaped
    call or `with` target anywhere -- T-3953's generous "already guarded,
    do not fire" signal (module-level docstring's own false-negative-
    over-false-positive posture)."""
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            target = node.func
            name = None
            if isinstance(target, ast.Attribute):
                name = target.attr
            elif isinstance(target, ast.Name):
                name = target.id
            if name and _RACE001_GUARD_RE.search(name):
                return True
        if isinstance(node, ast.withitem):
            expr = node.context_expr
            if isinstance(expr, ast.Call):
                target = expr.func
                name = target.attr if isinstance(target, ast.Attribute) else None
                name = name or (target.id if isinstance(target, ast.Name) else None)
                if name and _RACE001_GUARD_RE.search(name):
                    return True
            elif isinstance(expr, ast.Name) and _RACE001_GUARD_RE.search(expr.id):
                return True
    return False


# frob:ticket T-3953
def _race001_subscript_read(value: ast.expr) -> tuple[str, str] | None:
    """`(base, key)` for a `BASE[KEY]` read or a `BASE.get(KEY, ...)`
    call -- the two read shapes T-3953's read-then-write pattern starts
    from -- or `None` if `value` is neither."""
    if isinstance(value, ast.Subscript) and isinstance(value.value, ast.Name):
        try:
            key = ast.unparse(value.slice)
        except (ValueError, TypeError):
            return None
        return value.value.id, key
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Attribute)
        and value.func.attr == "get"
        and isinstance(value.func.value, ast.Name)
        and value.args
    ):
        try:
            key = ast.unparse(value.args[0])
        except (ValueError, TypeError):
            return None
        return value.func.value.id, key
    return None


# frob:ticket T-3953
def _race001_subscript_write_targets(
    stmt: ast.AST,
) -> list[tuple[str, str, ast.expr]]:
    """`[(base, key, rhs)]` for every `BASE[KEY] = rhs`/`BASE[KEY] += rhs`
    assignment `stmt` makes at its top level (never nested -- callers
    already `ast.walk` every statement)."""
    targets: list[ast.expr] = []
    rhs: ast.expr | None = None
    if isinstance(stmt, ast.Assign):
        targets = list(stmt.targets)
        rhs = stmt.value
    elif isinstance(stmt, ast.AugAssign):
        targets = [stmt.target]
        rhs = stmt.value
    else:
        return []
    out: list[tuple[str, str, ast.expr]] = []
    for target in targets:
        if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
            try:
                key = ast.unparse(target.slice)
            except (ValueError, TypeError):
                continue
            out.append((target.value.id, key, rhs))
    return out


# frob:ticket T-3953
def _race001_function_violation(
    subject_symref: str, subject_path: str, func_node: ast.AST
) -> Violation | None:
    """RACE001 for one function: an unlocked `BASE[KEY]` (or `BASE.get
    (KEY, ...)`) read whose result feeds a LATER `BASE[KEY] = ...` write
    to the SAME base/key, with no lock/atomic-update guard anywhere in
    the function (T-3953's own generous guard check, `_race001_guard_
    present`) -- the exact read-check-write shape F-181's delta audit
    kept re-finding un-tracked."""
    if not isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None
    if _race001_guard_present(func_node):
        return None
    reads: dict[str, str] = {}  # temp var name -> "base::key"
    for node in ast.walk(func_node):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                read = _race001_subscript_read(node.value)
                if read is not None:
                    reads[target.id] = f"{read[0]}::{read[1]}"
        write_targets = _race001_subscript_write_targets(node)
        for base, key, rhs in write_targets:
            write_key = f"{base}::{key}"
            rhs_names = {n.id for n in ast.walk(rhs) if isinstance(n, ast.Name)}
            for temp_name, read_key in reads.items():
                if read_key == write_key and temp_name in rhs_names:
                    line = getattr(node, "lineno", 0)
                    return Violation(
                        rule="RACE001",
                        severity=Severity.WARN,
                        file=subject_path,
                        line=line,
                        symref=subject_symref,
                        message=(
                            f"RACE001: {subject_symref} reads {base}[{key}] then "
                            f"later writes {base}[{key}] derived from that read, "
                            "with no lock/Lua/INCR/conditional-UPDATE guard "
                            "anywhere in the function -- two concurrent callers "
                            "can race the read-check-write and lose an update. "
                            "Guard with a lock, an atomic single-op update "
                            "(INCR-style), or a conditional UPDATE."
                        ),
                    )
    return None


# frob:ticket T-3953
def _race002_binding_tests_are_concurrent(
    snapshot: GraphSnapshot, root: Path, subject_symref: str
) -> tuple[bool, bool]:
    """`(has_binding_tests, has_concurrent_binding_test)` for
    `subject_symref`'s `frob:tests` targets -- a target counts as
    "concurrent" if its own pytest node id names threading/concurrency
    (`_RACE002_CONCURRENT_TEST_RE` against the qualname), or, failing
    that, if its resolved test source body does (T-3953: cheap name check
    first, source scan only when the name alone does not already say
    so)."""
    targets = [
        edge.target
        for edge in snapshot.edges
        if edge.kind is EdgeKind.TESTS and edge.src == subject_symref
    ]
    if not targets:
        return False, False
    for target in targets:
        if _RACE002_CONCURRENT_TEST_RE.search(target):
            return True, True
    for target in targets:
        test_path, sep, _qualname = target.partition("::")
        if not sep or not test_path.endswith(".py"):
            continue
        try:
            source = (root / test_path).read_text(encoding="utf-8")
        except OSError:
            continue
        if _RACE002_CONCURRENT_TEST_RE.search(source):
            return True, True
    return True, False


# frob:ticket T-3953
def _race002_test_obligation_violation(
    root: Path,
    snapshot: GraphSnapshot,
    subject_symref: str,
    subject_path: str,
    func_node: ast.AST,
) -> Violation | None:
    """RACE002 (T-3953 acceptance item 2): `func_node`'s own docstring
    claims cap/quota/single-use/idempotent behavior, but none of its
    `frob:tests` binding tests looks like a concurrent-callers test --
    the spec claim has no evidence a second caller cannot break it."""
    if not isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None
    doc = ast.get_docstring(func_node) or ""
    if not _RACE002_CLAIM_RE.search(doc):
        return None
    has_tests, has_concurrent = _race002_binding_tests_are_concurrent(
        snapshot, root, subject_symref
    )
    if not has_tests or has_concurrent:
        return None
    claim = _RACE002_CLAIM_RE.search(doc)
    claim_word = claim.group(0) if claim else "cap/quota/single-use/idempotent"
    return Violation(
        rule="RACE002",
        severity=Severity.WARN,
        file=subject_path,
        line=func_node.lineno,
        symref=subject_symref,
        message=(
            f"RACE002: {subject_symref}'s docstring claims {claim_word!r} "
            "behavior, but none of its frob:tests binding tests exercises "
            "concurrent callers -- add a test that calls it from multiple "
            "threads/processes (or otherwise names 'concurrent'/'race'/"
            "'parallel'/'thread') to prove the claim holds under real "
            "concurrency, not just single-caller correctness."
        ),
    )


# frob:doc \
# docs/modules/gate-race001.md#race001race002-concurrent-read-then-write-test-obligation-t-3953  # noqa: E501
# frob:ticket T-3953
# frob:enforces CHK-GATE-RACE001
def race001_violations(root: Path, snapshot: GraphSnapshot) -> list[Violation]:
    """RACE001/RACE002 (T-3953, F-181/T-3942 item 7): every Python
    function symbol in `snapshot` is checked for two independent, related
    defects -- RACE001, an unlocked read-then-write of the same key
    inside the function body (`_race001_function_violation`); and
    RACE002, a docstring claiming cap/quota/single-use/idempotent
    behavior with no concurrent-callers test among the symbol's own
    `frob:tests` bindings (`_race002_test_obligation_violation`). Both are
    `Severity.WARN` (T-3919/T-3942's own audit caveat: this is a
    heuristic shape that gets waived into uselessness fast if pitched as
    a hard-error gate) and both are deliberately biased toward silence
    over false claims -- see each helper's own guard-detection doctrine."""
    violations: list[Violation] = []
    for symref in sorted(snapshot.symbols):
        path, sep, qualname = symref.partition("::")
        if not sep or not path.endswith(".py"):
            continue
        try:
            source = (root / path).read_text(encoding="utf-8")
            tree = ast.parse(source, filename=path)
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            _log.debug("RACE001: cannot parse %s: %s", path, exc)
            continue
        scope: list[ast.stmt] = list(tree.body)
        func_node: ast.AST | None = None
        for part in qualname.split("."):
            func_node = next(
                (
                    n
                    for n in scope
                    if isinstance(
                        n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                    )
                    and n.name == part
                ),
                None,
            )
            if func_node is None:
                break
            scope = list(func_node.body)
        if func_node is None:
            continue
        race001 = _race001_function_violation(symref, path, func_node)
        if race001 is not None:
            violations.append(race001)
        race002 = _race002_test_obligation_violation(
            root, snapshot, symref, path, func_node
        )
        if race002 is not None:
            violations.append(race002)
    return violations
