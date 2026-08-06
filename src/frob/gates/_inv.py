# frob:waive INV006 preset="split-carried-prose"
"""frob.gates._inv -- INV00x invariant-coverage gate family (T-1188).

Split out of `frob.gates.__init__` (T-1072/T-1140/T-1159/T-1170/T-1174/
T-1183/T-1187/T-1188 one-family-per-land discipline, `_sys.py`'s T-1187
precedent) so the parent module can keep dropping toward the large-file
threshold without changing any public behavior. `invariant_gate`,
`inv003_gate`, `inv004_gate`, and `inv006_gate` are re-exported from
`frob.gates` unchanged -- the names this family is externally imported by
(`run_gates`'s job table, `tests/test_gates.py`); every other symbol here
stays private to this module.

One cohesive family: INV001/INV002/INV005 (`invariant_gate`, declared-
invariant evidence/anchor/reachability checks), INV003/INV004
(`inv003_gate`/`inv004_gate`, doc-side exclusivity/normative-claim
coverage), and INV006 (`inv006_gate`, the source-side completeness half of
T-0408) -- all four gates share the same "does a `frob:invariant` claim
have standing evidence/anchor" shape, just applied to different claim
sources (declared invariants, spec docs, source files).

`_evidence_collected`/`_node_id_matches_symref` are generic evidence-
matching helpers that predate this split and stay defined in
`frob.gates.__init__` (shared with the TEST00x family there too) --
imported here lazily, inside the functions that need them, rather than
at module import time, since `frob.gates.__init__` itself imports this
module and a top-level import would be circular.
"""
# frob:ticket T-1188

from __future__ import annotations

import re
from pathlib import Path

from frob.excludes import iter_files
from frob.gates._inv006_split_assist import find_carried_waiver
from frob.gates._models import Severity, Violation
from frob.gates._ratchet import (
    RatchetLock,
    load_ratchet_lock,
    ratchet_enabled_rules,
    resolve_ratchet_severity,
)
from frob.gates.invariants import (
    Invariant,
    find_exclusivity_claims,
    find_normative_claims,
)
from frob.graph import EdgeKind, GraphSnapshot
from frob.logging import get_logger
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


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0408
# T-0408: INV003/INV004 (T-0509/T-0515) deliberately scope to
# `INV003_SPEC_DIRS` (docs/modules, docs/strata) -- prose/comment claims
# living in SOURCE code (docstrings, `//`/`#` comments describing a
# guarantee) were entirely outside either gate's reach, which is exactly
# the "128 files asserting a guarantee in prose, only 4 formal
# invariants" gap the user named: the coverage gate only ever checked
# DECLARED invariants, never whether enough of the repo's own guarantee
# claims were declared at all. INV006 closes that blind spot for source
# trees without re-deriving INV003's noise-prone doc-only heuristics from
# scratch: same claim vocabulary (`find_exclusivity_claims`, already
# noise-filtered by T-0509's claim-shape scan), applied per-file to
# `INV006_SRC_DIRS`, bound-check against the SAME `GraphSnapshot` every
# other code-anchor gate already loads (a real `frob:invariant` edge
# anywhere in the file, not an HTML-comment marker regex that would never
# match non-markdown comment syntax).
INV006_SRC_DIRS: tuple[str, ...] = (
    "src",
    "strata-core/src",
    "frob-core/src",
)
# frob:doc docs/modules/gates.md#inv006-t-0408
# frob:ticket T-0408
INV006_SRC_SUFFIXES: tuple[str, ...] = (".py", ".rs")


# frob:ticket T-1649
def _inv006_src_files(root: Path) -> tuple[Path, ...]:
    """Every file under any `INV006_SRC_DIRS` entry with any `INV006_SRC_
    SUFFIXES` extension, one `iter_files` scan of `root` total (T-1649) --
    the pre-fix shape called `iter_files` once per `(src_dir, suffix)`
    pair (3 dirs x 2 suffixes = 6 full-repo scans for a fixed, small
    cross product both loop variables' own callers already hold; PERF011).
    """
    prefixes = tuple(f"{src_dir}/" for src_dir in INV006_SRC_DIRS)
    lowered_suffixes = {s.lower() for s in INV006_SRC_SUFFIXES}
    return tuple(
        path
        for path in iter_files(root)
        if path.suffix.lower() in lowered_suffixes
        and path.relative_to(root).as_posix().startswith(prefixes)
    )


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0408
def _inv006_waived(rel: str, snapshot: GraphSnapshot) -> bool:
    """True if some `frob:waive INV006 reason="..."` edge binds to `rel`
    (dsl.py already refuses a reason-less waive as a MalformedDirective,
    so every surviving WAIVE edge here carries a reason -- same contract
    `_waive_edges` documents)."""
    return any(
        edge.kind == EdgeKind.WAIVE
        and edge.target == "INV006"
        and (
            edge.origin.rpartition(":")[0] == rel
            or edge.src == rel
            or edge.src.startswith(f"{rel}::")
        )
        for edge in snapshot.edges
    )


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0408
# frob:ticket T-0594
def _inv006_src_violations(
    root: Path,
    path: Path,
    snapshot: GraphSnapshot,
    ratchet_rules: frozenset[str],
    ratchet_lock: RatchetLock,
) -> tuple[Violation, ...]:
    """INV006 findings for one source file: an exclusivity claim
    (`frob.gates.invariants.find_exclusivity_claims`) with no
    `frob:invariant` edge anchored anywhere in the file.

    T-0594: when INV006 is opted into `[gates.ratchet] rules` in
    `frob.toml`, the finding's severity is resolved against the committed
    `frob-ratchet.lock.json` baseline (`resolve_ratchet_severity`,
    T-0569) instead of always reporting the gate's static WARN -- a
    baselined file (an existing claim, already triaged) stays WARN, a
    NEW one errors for real. `ratchet_rules`/`ratchet_lock` are loaded
    once by the caller (`inv006_gate`), not per file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("INV006: could not read %s: %s", path, exc)
        return ()
    claims = find_exclusivity_claims(text)
    if not claims:
        return ()
    rel = path.relative_to(root).as_posix()
    if any(
        edge.kind == EdgeKind.INVARIANT and edge.origin.rpartition(":")[0] == rel
        for edge in snapshot.edges
    ):
        return ()
    if _inv006_waived(rel, snapshot):
        _log.debug("INV006: %s waived by frob:waive INV006", rel)
        return ()
    severity = Severity.WARN
    if "INV006" in ratchet_rules:
        resolved = resolve_ratchet_severity("INV006", rel, ratchet_lock)
        severity = Severity.ERROR if resolved == "error" else Severity.WARN
        _log.debug(
            "INV006: %s ratchet-resolved to %s (rules=%s)", rel, resolved, ratchet_rules
        )
    message = (
        f"INV006: {rel} makes an exclusivity/normative claim "
        f"({', '.join(sorted(claims))}) with no `frob:invariant "
        f"INV-###` edge anchored anywhere in the file -- bind an "
        f"invariant that covers the claim, waive with a reason, "
        f"or reword to drop the exclusivity language if it isn't "
        f"actually enforced"
    ) + _inv006_split_assist_suffix(root, text, rel, snapshot)
    return (
        Violation(
            rule="INV006",
            severity=severity,
            file=rel,
            line=0,
            message=message,
        ),
    )


# frob:ticket T-1134
def _inv006_split_assist_suffix(
    root: Path, text: str, rel: str, snapshot: GraphSnapshot
) -> str:
    """T-1134: `""` unless this claim sentence in `text` was moved VERBATIM
    out of a file that already carries a covering INV006 waiver/invariant
    (a module split, the recurring T-1103/T-1107/T-1072/T-1077/T-1081/
    T-1082 cost this drive) -- otherwise the message suffix naming that
    source and offering its disposition as a copy-pastable fix-it, instead
    of leaving "remember the carried waiver" a silent human step."""
    carried = find_carried_waiver(
        root,
        text,
        exclude_rel=rel,
        candidate_dirs=INV006_SRC_DIRS,
        candidate_suffixes=INV006_SRC_SUFFIXES,
        snapshot=snapshot,
    )
    if carried is None:
        return ""
    source_rel, kind, fixit = carried
    return (
        f" -- T-1134: this claim was moved verbatim from {source_rel}, "
        f"which already carries a covering {kind}; carry it here: {fixit}"
    )


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0408
# frob:enforces CHK-GATE-INV006
def inv006_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """INV006 (advisory): every exclusivity claim in a source file under
    `INV006_SRC_DIRS` needs a `frob:invariant` edge bound somewhere in
    that file.

    WARN severity, matching INV003's posture: a source-level claim can
    still be genuine design intent rather than an enforced behavior, so
    this surfaces the signal for triage rather than forcing a bind on
    every hit. This is the coverage-COMPLETENESS half of T-0408 (INV001/
    INV002 only ever validated invariants that already existed to be
    validated; nothing previously checked whether ENOUGH of the repo's
    own prose guarantee claims outside docs/ had one declared at all).

    T-0594: if `INV006` is opted into `[gates.ratchet] rules` in
    `root/frob.toml`, per-file severity is resolved against the committed
    `frob-ratchet.lock.json` baseline (`resolve_ratchet_severity`) instead
    of the static WARN -- a baselined file stays WARN, a fresh one errors.
    Ratchet state is loaded once here, not per file.
    """
    ratchet_rules = ratchet_enabled_rules(root)
    ratchet_lock = (
        load_ratchet_lock(root) if "INV006" in ratchet_rules else RatchetLock()
    )
    violations: list[Violation] = []
    for path in _inv006_src_files(root):
        violations.extend(
            _inv006_src_violations(root, path, snapshot, ratchet_rules, ratchet_lock)
        )
    return tuple(violations)
