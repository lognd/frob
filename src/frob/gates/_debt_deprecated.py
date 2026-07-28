"""frob.gates._debt_deprecated -- DEBT00x (`frob:debt`) and DEPR00x
(`frob:deprecated`) gate families, split out of `frob.gates.__init__`
(T-1115, following T-1072/T-1077's precedent).

Kept together because `frob:deprecated` is `frob:debt` generalized to the
API surface itself (DEPR001-004 mirror DEBT001-003's shape one-for-one;
DEPR005 is deprecated-specific, T-0639) and both feed the same REL001
release-blocking check in `run_gates`'s spine.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/gates/_debt_deprecated.py's exclusivity-vocabulary hits are \
# source-level design-rationale prose (docstrings and comments describing \
# already-implemented internal behavior, verifiable by reading the code \
# they annotate) rather than a separate cross-module contract needing its \
# own tracked invariant; disposed as a calibration batch, not claim-by- \
# claim -- module prose split verbatim from the pre-T-1115 \
# gates/__init__.py monolith, mirroring the T-1077/_todo_fmt.py precedent"

from __future__ import annotations

import re
from pathlib import Path

from frob.exports import exports_consumers
from frob.gates._deprecated_baseline import (
    file_reference_counts,
    load_deprecated_baseline,
)
from frob.gates._models import DebtEntry, DeprecatedEntry, Severity, Violation
from frob.graph import Edge, EdgeKind, GraphSnapshot
from frob.logging import get_logger
from frob.tickets import TicketQueue
from frob.xref import xref

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# T-0412: the debt-vs-waive distinction
#
# `frob:waive <RULE> reason="..."` is PERMANENT: a genuine, forever-
# acceptable exception. `frob:debt <RULE> reason="..." ticket="T-####"
# [until="..."]` is its TEMPORARY counterpart -- an accepted gap that is
# TRACKED as owed, bound to an open ticket (never optional, unlike a
# waiver's ticket-free reason), and escalates to a hard ERROR once its
# `until` boundary (a date `YYYY-MM-DD` or a semver `X.Y.Z`) passes. The
# release gate additionally refuses to bless a release while ANY debt is
# still open at all, expired or not (`_release_open_debt_violations`) --
# debt is collected and re-raised before shipping, never silently carried
# forward as a de facto permanent exception the way an un-audited
# `frob:waive` can be.
# ---------------------------------------------------------------------------


def _debt_edges(snapshot: GraphSnapshot) -> tuple[Edge, ...]:
    """Every `frob:debt` edge in the snapshot (dsl.py already rejects one
    missing `reason=`/`ticket=` as a MalformedDirective, T-0412)."""
    from frob.gates import _edges_of_kind

    return _edges_of_kind(snapshot, EdgeKind.DEBT)


# frob:waive DUP001 reason="dup grouped this with the sibling per-directive \
# malformed-directive builders (DEBT001/DEPR001/TEST010 are three \
# independently-evolving per-directive checks -- frob:debt/frob:deprecated/frob:tests \
# kind= -- with the same MalformedDirective-surfacing shape by established convention) \
# (T-0861)"
# frob:enforces CHK-GATE-DEBT001
def _debt001_violations(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DEBT001: a `frob:debt` directive missing `reason="..."` and/or
    `ticket="T-####"` -- surfaced from `frob.graph`'s MalformedDirective
    list, mirroring WAIVE001's own shape for `frob:waive`."""
    violations: list[Violation] = []
    for md in snapshot.malformed:
        if "frob:debt" not in md.reason:
            continue
        _log.debug("DEBT001: %s:%d %s", md.file, md.line, md.reason)
        violations.append(
            Violation(
                rule="DEBT001",
                severity=Severity.ERROR,
                file=md.file,
                line=md.line,
                message=f"DEBT001: {md.file}:{md.line} {md.reason}",
            )
        )
    return tuple(violations)


# frob:enforces CHK-GATE-DEBT002
def _debt002_violations(
    snapshot: GraphSnapshot, queue: TicketQueue
) -> tuple[Violation, ...]:
    """DEBT002: a `frob:debt`'s `ticket="..."` names a ticket that is
    missing or not open (T-0412's "anti-lie" requirement -- a debt must
    point at real, open, owed work, never a closed/nonexistent ticket
    pretending the gap is still tracked). Reuses the same open-ticket
    check `_todo002_edges` (TODO002) applies to `frob:todo`, but at ERROR
    severity: an untracked deferral is a hygiene warning, a mis-tracked
    DEBT is a structural lie about what is actually owed."""
    from frob.gates import _OPEN_STATES, _site_from_edge_origin

    violations: list[Violation] = []
    for edge in _debt_edges(snapshot):
        ticket_id = edge.attrs.get("ticket", "")
        target = queue.tickets.get(ticket_id)
        if target is not None and target.state in _OPEN_STATES:
            continue
        file, line = _site_from_edge_origin(edge.origin)
        _log.debug("DEBT002: %s -> ticket=%s not open", edge.src, ticket_id)
        violations.append(
            Violation(
                rule="DEBT002",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"DEBT002: frob:debt {edge.target} at {edge.src} is bound to "
                    f"ticket={ticket_id!r}, which is not open (missing or closed); "
                    f"a debt must point at real, owed work -- rebind to an open "
                    f"ticket or resolve the debt and remove the directive"
                ),
            )
        )
    return tuple(violations)


def _debt_is_expired(until: str, *, current_date: str, current_version: str) -> bool:
    """Whether `until` (a `YYYY-MM-DD` date or an `X.Y.Z` semver) has
    passed, judged against `current_date`/`current_version` (T-0412). An
    unparseable `until` is treated as NOT expired here -- DEBT003 only
    fires on a boundary it can actually evaluate; a malformed `until`
    value is a separate, human-readable concern (not silently ignored: it
    still shows up verbatim in `frob debt`'s listing)."""
    date_match = re.match(r"^\d{4}-\d{2}-\d{2}$", until.strip())
    if date_match:
        return until.strip() <= current_date
    parsed_until = _debt_parse_version(until)
    parsed_current = _debt_parse_version(current_version)
    if parsed_until is not None and parsed_current is not None:
        return parsed_current >= parsed_until
    return False


_DEBT_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def _debt_parse_version(version: str) -> tuple[int, int, int] | None:
    """`(major, minor, patch)` from an `X.Y.Z(-suffix)` string, or `None`
    (T-0412) -- a small self-contained copy of `frob.release`'s own
    `_parse`, kept local rather than importing a private symbol across
    the module boundary (`frob.gates` -> `frob.release` is already a
    dependency for `release_gate`, but only of its PUBLIC API)."""
    match = _DEBT_VERSION_RE.match(version.strip())
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


# frob:enforces CHK-GATE-DEBT003
def _debt003_violations(
    snapshot: GraphSnapshot, *, current_date: str, current_version: str
) -> tuple[Violation, ...]:
    """DEBT003: a `frob:debt` whose `until="..."` boundary has passed --
    escalates from a suppressed finding to a hard ERROR (T-0412's whole
    point: debt with an expiry that nothing enforces is not actually
    temporary). A debt with no `until` at all never expires on its own;
    it is still caught at release time by `_release_open_debt_violations`
    (ALL open debt blocks a release, not just expired debt)."""
    from frob.gates import _site_from_edge_origin

    violations: list[Violation] = []
    for edge in _debt_edges(snapshot):
        until = edge.attrs.get("until", "")
        if not until:
            continue
        if not _debt_is_expired(
            until, current_date=current_date, current_version=current_version
        ):
            continue
        file, line = _site_from_edge_origin(edge.origin)
        _log.debug("DEBT003: %s expired (until=%s)", edge.src, until)
        violations.append(
            Violation(
                rule="DEBT003",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"DEBT003: frob:debt {edge.target} at {edge.src} expired "
                    f"(until={until!r}); resolve the debt (fix the underlying "
                    f"gap) and remove the directive, or file a follow-up and "
                    f"extend `until` with a written reason"
                ),
            )
        )
    return tuple(violations)


# frob:doc docs/modules/gates.md#debt-gate-t-0412
# frob:tests tests/test_gates.py::TestDebtGate.test_debt001_malformed_directive_is_reported  # noqa: E501
# frob:tests tests/test_gates.py::TestDebtGate.test_debt002_closed_ticket_is_reported  # noqa: E501
# frob:tests tests/test_gates.py::TestDebtGate.test_debt003_expired_by_date_is_reported  # noqa: E501
# frob:tests tests/test_gates.py::TestDebtGate.test_debt003_expired_by_version_is_reported  # noqa: E501
# frob:tests tests/test_gates.py::TestDebtGate.test_clean_debt_produces_no_violations  # noqa: E501
def debt_gate(
    snapshot: GraphSnapshot,
    queue: TicketQueue,
    *,
    current_date: str,
    current_version: str,
) -> tuple[Violation, ...]:
    """DEBT001-003 (T-0412): `frob:debt`'s three failure modes -- a
    malformed directive, a directive bound to a non-open ticket, and a
    directive whose `until` boundary has passed. `current_date`
    (`YYYY-MM-DD`) and `current_version` (`X.Y.Z`) are injected rather than
    computed here so this stays a pure function over its inputs, matching
    every other gate in this module."""
    return (
        *_debt001_violations(snapshot),
        *_debt002_violations(snapshot, queue),
        *_debt003_violations(
            snapshot, current_date=current_date, current_version=current_version
        ),
    )


# frob:doc docs/modules/gates.md#debt-gate-t-0412
# frob:tests tests/test_gates.py::TestDebtGate.test_lists_every_debt_entry  # noqa: E501
def list_debt(
    snapshot: GraphSnapshot, *, current_date: str, current_version: str
) -> tuple[DebtEntry, ...]:
    """Every currently-recorded `frob:debt` entry (T-0412), for `frob debt`
    to report honestly -- independent of whether each entry is itself
    well-formed/open/expired (a malformed or mis-tracked one still shows up
    here; DEBT001/002/003 are what fail the BUILD over it, this is what
    lets a human/agent see the whole outstanding set at a glance)."""
    entries: list[DebtEntry] = []
    for edge in _debt_edges(snapshot):
        until = edge.attrs.get("until", "")
        expired = bool(until) and _debt_is_expired(
            until, current_date=current_date, current_version=current_version
        )
        entries.append(
            DebtEntry(
                rule=edge.target,
                site=edge.src,
                ticket=edge.attrs.get("ticket", ""),
                until=until,
                expired=expired,
            )
        )
    return tuple(entries)


# frob:enforces CHK-GATE-REL001
def _release_open_debt_violations(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """REL001: a release must never ship with ANY open `frob:debt` --
    expired or not (T-0412's central requirement: debt is collected and
    re-raised BEFORE release, never silently carried forward as a de facto
    permanent exception). Reported under REL001, the same rule id
    `release_gate`'s other findings use, since this is a release-blocking
    condition, not a new independent failure mode of its own."""
    from frob.gates import _site_from_edge_origin

    debts = _debt_edges(snapshot)
    if not debts:
        return ()
    violations: list[Violation] = []
    for edge in debts:
        file, line = _site_from_edge_origin(edge.origin)
        violations.append(
            Violation(
                rule="REL001",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"REL001: frob:debt {edge.target} at {edge.src} "
                    f"(ticket={edge.attrs.get('ticket', '')!r}) is still open; "
                    f"all debt must be resolved (or its owning ticket closed, "
                    f"clearing the directive) before a release, run: frob debt"
                ),
            )
        )
    return tuple(violations)


# ---------------------------------------------------------------------------
# Deprecated-symbol gate (T-0576): `frob:debt` generalized to the API
# surface itself. A `frob:deprecated <since> sunset="YYYY-MM-DD"
# ticket="T-####" [reason="..."]` directive on a public symbol declares a
# ticket-bound, dated exit -- distinct from `frob:debt` in that its subject
# is the symbol's continued EXISTENCE, not a suppressed lint finding.
#
# DEPR001: malformed directive (missing/invalid `sunset=`/`ticket=`), same
# shape as DEBT001. DEPR002: the bound ticket is not open (missing, or
# closed with the directive -- and presumably the symbol -- still in
# place), same shape and severity as DEBT002. DEPR003: the sunset date has
# not yet passed -- a WARNING, not an error, so a live-but-scheduled
# deprecation stays visible in ordinary `frob check` output rather than
# being wholly silent until the date arrives (`frob:debt` has no equivalent
# "still valid" signal; a deprecated PUBLIC symbol needs one, per T-0576's
# body). DEPR004: the sunset date has passed -- escalates to ERROR, mirroring
# DEBT003's expiry escalation. DEPR003/DEPR004 are mutually exclusive per
# edge (a given `frob:deprecated` is either still in its warning window or
# past sunset, never both), and DEPR002 suppresses both when the ticket
# itself is not open (a mistracked deprecation is the more actionable
# finding). DEPR005 (T-0639): a deprecated symbol's reference set gained a
# NEW member absent from the committed `frob-deprecated-baseline.lock.json`
# baseline (`frob.gates._deprecated_baseline`) -- a fresh adopter of a
# symbol already declared on its way out, distinct from DEPR003/004's
# sunset-clock states and orthogonal to them (a symbol can be both
# in-window/past-sunset AND gaining new callers). `release_gate` additionally
# refuses to stamp a release while
# ANY *expired* deprecation is still open (`_release_expired_deprecated_
# violations`) -- unlike DEBT's release check, a still-live deprecation
# (within its warning window) does not block a release; the point is that
# an unenforced sunset never quietly survives past its own date.
# ---------------------------------------------------------------------------


def _deprecated_edges(snapshot: GraphSnapshot) -> tuple[Edge, ...]:
    """Every `frob:deprecated` edge in the snapshot (dsl.py already rejects
    one missing `sunset=`/`ticket=`, or with a non-`YYYY-MM-DD` `sunset=`,
    as a MalformedDirective, T-0576)."""
    from frob.gates import _edges_of_kind

    return _edges_of_kind(snapshot, EdgeKind.DEPRECATED)


# frob:waive DUP001 reason="dup grouped this with the sibling per-directive \
# malformed-directive builders -- see _debt001_violations for full reasoning (T-0861)"
# frob:enforces CHK-GATE-DEPR001
def _depr001_violations(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DEPR001: a `frob:deprecated` directive missing/invalid `sunset=` or
    missing `ticket=` -- surfaced from `frob.graph`'s MalformedDirective
    list, mirroring DEBT001's own shape for `frob:debt`."""
    violations: list[Violation] = []
    for md in snapshot.malformed:
        if "frob:deprecated" not in md.reason:
            continue
        _log.debug("DEPR001: %s:%d %s", md.file, md.line, md.reason)
        violations.append(
            Violation(
                rule="DEPR001",
                severity=Severity.ERROR,
                file=md.file,
                line=md.line,
                message=f"DEPR001: {md.file}:{md.line} {md.reason}",
            )
        )
    return tuple(violations)


# frob:enforces CHK-GATE-DEPR002
def _depr002_violations(
    snapshot: GraphSnapshot, queue: TicketQueue
) -> tuple[Violation, ...]:
    """DEPR002: a `frob:deprecated`'s `ticket="..."` names a ticket that is
    missing or not open -- the "ticket closes without removal" failure mode
    from T-0576's body: once the owning ticket closes, the directive (and
    presumably the symbol it sunsets) must be gone; if it is still there,
    that is a structural lie about what is actually tracked, same posture
    as DEBT002 for `frob:debt`."""
    from frob.gates import _OPEN_STATES, _site_from_edge_origin

    violations: list[Violation] = []
    for edge in _deprecated_edges(snapshot):
        ticket_id = edge.attrs.get("ticket", "")
        target = queue.tickets.get(ticket_id)
        if target is not None and target.state in _OPEN_STATES:
            continue
        file, line = _site_from_edge_origin(edge.origin)
        _log.debug("DEPR002: %s -> ticket=%s not open", edge.src, ticket_id)
        violations.append(
            Violation(
                rule="DEPR002",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"DEPR002: frob:deprecated {edge.target} at {edge.src} is "
                    f"bound to ticket={ticket_id!r}, which is not open (missing "
                    f"or closed); a deprecation must point at real, open "
                    f"removal work -- rebind to an open ticket, or finish the "
                    f"removal and delete the directive along with the symbol"
                ),
            )
        )
    return tuple(violations)


def _deprecated_is_expired(sunset: str, *, current_date: str) -> bool:
    """Whether `sunset` (a `YYYY-MM-DD` date) has passed, judged against
    `current_date` (T-0576). `sunset` is always well-formed here -- dsl.py
    rejects a non-`YYYY-MM-DD` `sunset=` as DEPR001-malformed before it ever
    becomes a `DEPRECATED` edge."""
    return sunset.strip() <= current_date


# frob:enforces CHK-GATE-DEPR003
def _depr003_violations(
    snapshot: GraphSnapshot, queue: TicketQueue, *, current_date: str
) -> tuple[Violation, ...]:
    """DEPR003: a `frob:deprecated` still inside its warning window (bound
    to an open ticket, `sunset` not yet passed) -- a WARNING, kept visible
    in ordinary `frob check` output rather than silent until the sunset
    date arrives (T-0576's "warns while in window" requirement). Suppressed
    when DEPR002 already fired for the same edge (a mistracked ticket is
    the more actionable finding) or when DEPR004 fires instead (past
    sunset -- an ERROR, not also a WARNING)."""
    from frob.gates import _OPEN_STATES, _site_from_edge_origin

    violations: list[Violation] = []
    for edge in _deprecated_edges(snapshot):
        ticket_id = edge.attrs.get("ticket", "")
        target = queue.tickets.get(ticket_id)
        if target is None or target.state not in _OPEN_STATES:
            continue
        sunset = edge.attrs.get("sunset", "")
        if _deprecated_is_expired(sunset, current_date=current_date):
            continue
        file, line = _site_from_edge_origin(edge.origin)
        _log.debug("DEPR003: %s in window (sunset=%s)", edge.src, sunset)
        violations.append(
            Violation(
                rule="DEPR003",
                severity=Severity.WARN,
                file=file,
                line=line,
                message=(
                    f"DEPR003: {edge.src} is deprecated since {edge.target!r} "
                    f"(ticket={ticket_id!r}), sunsets {sunset}; migrate off it "
                    f"before then"
                ),
            )
        )
    return tuple(violations)


# frob:enforces CHK-GATE-DEPR004
def _depr004_violations(
    snapshot: GraphSnapshot, queue: TicketQueue, *, current_date: str
) -> tuple[Violation, ...]:
    """DEPR004: a `frob:deprecated` whose `sunset` boundary has passed --
    escalates from a warning to a hard ERROR (T-0576's "errors past sunset"
    requirement), mirroring DEBT003's expiry escalation. Suppressed when
    DEPR002 already fired for the same edge (a mistracked ticket is the
    more actionable finding)."""
    from frob.gates import _OPEN_STATES, _site_from_edge_origin

    violations: list[Violation] = []
    for edge in _deprecated_edges(snapshot):
        ticket_id = edge.attrs.get("ticket", "")
        target = queue.tickets.get(ticket_id)
        if target is None or target.state not in _OPEN_STATES:
            continue
        sunset = edge.attrs.get("sunset", "")
        if not _deprecated_is_expired(sunset, current_date=current_date):
            continue
        file, line = _site_from_edge_origin(edge.origin)
        _log.debug("DEPR004: %s expired (sunset=%s)", edge.src, sunset)
        violations.append(
            Violation(
                rule="DEPR004",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"DEPR004: {edge.src} is deprecated since {edge.target!r} "
                    f"(ticket={ticket_id!r}) and past its sunset ({sunset}); "
                    f"remove the symbol and its directive, or file a follow-up "
                    f"and extend `sunset` with a written reason"
                ),
            )
        )
    return tuple(violations)


def _bare_symbol_name(edge_src: str) -> str:
    """The bare identifier a `DEPRECATED` edge's `src` (`path::qualname`)
    resolves to for `frob.exports.exports_consumers`/`frob.xref.xref`
    lookup (T-0639): the last dotted segment of the qualname half, e.g.
    `"src/a.py::Foo.bar"` -> `"bar"`. Both lookup functions match by bare
    identifier, not by fully-qualified path, so this is deliberately
    coarse -- see `deprecated_current_references`'s docstring for why that
    coarseness is harmless for a baseline-diff rule."""
    qualname = edge_src.rsplit("::", 1)[-1]
    return qualname.rsplit(".", 1)[-1]


#: Matches a call-shaped usage of a bare identifier (`name(` or `name (`,
#: allowing a preceding `.` for a qualified call like `mod.run(`) but not
#: a `def name(...)`/`class name(...)` declaration line itself -- narrows
#: `deprecated_current_references`'s xref side to actual invocations,
#: since a bare short identifier (e.g. a runner module's `run`) is
#: otherwise reused as a completely unrelated function name/parameter/
#: attribute across an unrelated part of the tree (T-0639).
def _looks_like_call(symbol: str, context: str) -> bool:
    """Whether `context` (one source line) looks like it CALLS `symbol`,
    rather than merely mentioning or (re)declaring it -- a lightweight
    textual heuristic, not a parse: a `def `/`class ` prefix is excluded
    outright, otherwise the line must contain `symbol` immediately
    followed by `(` (whitespace allowed in between)."""
    stripped = context.strip()
    if stripped.startswith(("def ", "class ", "async def ")):
        return False
    return bool(re.search(rf"\b{re.escape(symbol)}\s*\(", context))


# frob:doc docs/modules/gates.md#depr005-new-caller-baseline-ratchet-t-0639-redesigned-t-1052  # noqa: E501
# frob:tests tests/test_gates.py::TestDeprecatedGate.test_depr005_reference_set_combines_consumers_and_xref kind="unit"  # noqa: E501
# frob:tests tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating.test_unrelated_same_name_call_in_non_importing_file_is_excluded kind="unit"  # noqa: E501
def deprecated_current_references(symbol: str, root: Path) -> frozenset[str]:
    """The current `file:line` reference set for bare identifier `symbol`
    under `root` (T-0639, callgraph-resolved as of T-1052): the union of
    `frob.exports.exports_consumers`'s file-level import-statement
    consumers (T-0876) and `frob.xref.xref`'s Python-scoped, call-shaped
    identifier usages (`_looks_like_call`) -- but a call-shaped usage only
    counts when it falls in a file that itself imports `symbol` (i.e. is
    also an `exports_consumers` hit for `symbol`), excluding any usage in
    the symbol's own defining file (its declaration line and any purely
    internal same-file mention are not a "new caller").

    `frob.graph.callgraph.build_call_graph` itself never resolves an edge
    to a PUBLIC callee by design (T-0639's original design decision, see
    this module's DEPR005 docs anchor above) -- extending it would be a
    much larger change than this rule needs.
    The import-gate here is this rule's own edge resolution over the same
    substrate `build_call_graph` uses for private helpers: a bare
    identifier match is not accepted as a reference unless the file
    actually imports that exact name, which is what tells
    `subprocess.run(` (a file that never imports the deprecated `run`)
    apart from a genuine caller of a deprecated `run` (a file with `from
    xref_runner import run` and a `run(...)` call site) -- T-1052's fix
    for the bare-short-name over-match that made nearly every `.run(` in
    the tree count as a caller of any `run`-named deprecated symbol."""
    refs: set[str] = set()
    consumers_result = exports_consumers(symbol, root, lang="python")
    importing_files: set[str] = set()
    if consumers_result.is_ok:
        for consumer in consumers_result.danger_ok.consumers:
            refs.add(f"{consumer.file}:{consumer.line}")
            importing_files.add(consumer.file)
    xref_result = xref(symbol, root, lang="python")
    if xref_result.is_ok:
        xr = xref_result.danger_ok
        definition_file = xr.definition.file if xr.definition else None
        for usage in xr.usages:
            if definition_file is not None and usage.file == definition_file:
                continue
            if usage.file not in importing_files:
                continue
            if not _looks_like_call(symbol, usage.context):
                continue
            refs.add(f"{usage.file}:{usage.line}")
    return frozenset(refs)


# frob:enforces CHK-GATE-DEPR005
# frob:tests tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth.test_same_count_as_baseline_does_not_fire kind="unit"  # noqa: E501
# frob:tests tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth.test_growth_beyond_baseline_fires_at_the_right_file_and_line kind="unit"  # noqa: E501
def _depr005_violations(
    snapshot: GraphSnapshot, queue: TicketQueue, root: Path, *, current_date: str
) -> tuple[Violation, ...]:
    """DEPR005: a live `frob:deprecated` symbol's current reference set
    (`deprecated_current_references`) has a referencing file whose
    resolved-reference COUNT exceeds what is baselined for that file in
    the committed `frob-deprecated-baseline.lock.json`
    (`frob.gates._deprecated_baseline.load_deprecated_baseline`,
    `DeprecatedBaselineEntry.file_counts`) -- a genuinely NEW adopter of a
    symbol already declared on its way out, or a new call site added
    inside a file that already had some (T-0639, redesigned line-
    insensitively on the `(file, symbol)` key in T-1052: a file's count
    exceeding its baseline is what fires, never a raw file:line diff, so
    a pure line-shift inside an already-referencing file changes nothing).
    A symbol never baselined at all fires nothing (its first-observed
    reference set is legacy, seeded rather than flagged --
    `tighten_deprecated_baseline` is what performs that seeding; this
    gate only ever reads what is already committed). Suppressed when
    DEPR002 already fired for the same edge, same posture as DEPR003/004."""
    from frob.gates import _OPEN_STATES

    violations: list[Violation] = []
    baseline = load_deprecated_baseline(root)
    for edge in _deprecated_edges(snapshot):
        ticket_id = edge.attrs.get("ticket", "")
        target = queue.tickets.get(ticket_id)
        if target is None or target.state not in _OPEN_STATES:
            continue
        entry = baseline.for_symbol(edge.src)
        if entry is None:
            _log.debug("DEPR005: %s not yet baselined, skipping", edge.src)
            continue
        symbol = _bare_symbol_name(edge.src)
        current_refs = deprecated_current_references(symbol, root)
        current_counts = file_reference_counts(current_refs)
        baseline_counts = entry.file_counts()
        grown_files = sorted(
            file
            for file, count in current_counts.items()
            if count > baseline_counts.get(file, 0)
        )
        for grown_file in grown_files:
            # frob:waive PERF004 reason="T-1115: grown_lines sorts the current \
            # reference set's own line numbers for THIS grown_file only -- a \
            # different, per-iteration distinct subset each time, not a shared \
            # re-sort hoistable out of the loop"
            grown_lines = sorted(
                int(ref.rpartition(":")[2])
                for ref in current_refs
                if ref.rpartition(":")[0] == grown_file
                and ref.rpartition(":")[2].isdigit()
            )
            ref_line = grown_lines[0] if grown_lines else 1
            _log.warning("DEPR005: %s gained new caller(s) in %s", edge.src, grown_file)
            violations.append(
                Violation(
                    rule="DEPR005",
                    severity=Severity.ERROR,
                    file=grown_file,
                    line=ref_line,
                    message=(
                        f"DEPR005: {edge.src} is deprecated (ticket={ticket_id!r}) "
                        f"but gained a new caller in {grown_file} absent from "
                        f"frob-deprecated-baseline.lock.json; migrate off the "
                        f"deprecated symbol instead of adopting it further"
                    ),
                )
            )
    return tuple(violations)


# frob:doc docs/modules/gates.md#deprecated-gate-t-0576
# frob:tests tests/test_gates.py::TestDeprecatedGate.test_depr001_malformed_directive_is_reported  # noqa: E501
# frob:tests tests/test_gates.py::TestDeprecatedGate.test_depr002_closed_ticket_is_reported  # noqa: E501
# frob:tests tests/test_gates.py::TestDeprecatedGate.test_depr003_in_window_warns  # noqa: E501
# frob:tests tests/test_gates.py::TestDeprecatedGate.test_depr004_past_sunset_errors  # noqa: E501
# frob:tests tests/test_gates.py::TestDeprecatedGate.test_clean_deprecated_produces_no_violations  # noqa: E501
# frob:tests tests/test_gates.py::TestDeprecatedGate.test_depr005_new_caller_errors  # noqa: E501
# frob:tests tests/test_gates.py::TestDeprecatedGate.test_depr005_no_baseline_entry_is_silent  # noqa: E501
def deprecated_gate(
    snapshot: GraphSnapshot,
    queue: TicketQueue,
    root: Path,
    *,
    current_date: str,
) -> tuple[Violation, ...]:
    """DEPR001-005 (T-0576, DEPR005 T-0639): `frob:deprecated`'s states --
    a malformed directive, a directive bound to a non-open ticket, a
    directive still in its warning window, a directive past its sunset
    date, and a directive whose reference set gained a new, un-baselined
    caller. `current_date` (`YYYY-MM-DD`) is injected rather than computed
    here so this stays a pure function of its inputs, matching
    `debt_gate`; `root` is needed only by DEPR005, to resolve
    `frob-deprecated-baseline.lock.json` and the current reference set."""
    return (
        *_depr001_violations(snapshot),
        *_depr002_violations(snapshot, queue),
        *_depr003_violations(snapshot, queue, current_date=current_date),
        *_depr004_violations(snapshot, queue, current_date=current_date),
        *_depr005_violations(snapshot, queue, root, current_date=current_date),
    )


# frob:doc docs/modules/gates.md#deprecated-gate-t-0576
# frob:tests tests/test_gates.py::TestDeprecatedGate.test_lists_every_deprecated_entry  # noqa: E501
def list_deprecated(
    snapshot: GraphSnapshot, *, current_date: str
) -> tuple[DeprecatedEntry, ...]:
    """Every currently-recorded `frob:deprecated` entry (T-0576), for a
    human/agent to see the whole outstanding sunset set at a glance --
    independent of whether each entry is itself well-formed/open/expired
    (DEPR001/002/004 are what fail the BUILD over it, this is what reports
    honestly regardless)."""
    entries: list[DeprecatedEntry] = []
    for edge in _deprecated_edges(snapshot):
        sunset = edge.attrs.get("sunset", "")
        expired = bool(sunset) and _deprecated_is_expired(
            sunset, current_date=current_date
        )
        entries.append(
            DeprecatedEntry(
                symref=edge.src,
                since=edge.target,
                sunset=sunset,
                ticket=edge.attrs.get("ticket", ""),
                expired=expired,
            )
        )
    return tuple(entries)


# frob:enforces CHK-GATE-REL001
def _release_expired_deprecated_violations(
    snapshot: GraphSnapshot, *, current_date: str
) -> tuple[Violation, ...]:
    """REL001: a release must never ship while ANY `frob:deprecated` is
    past its sunset (T-0576) -- unlike `frob:debt` (where ALL open debt
    blocks a release), a deprecation still inside its warning window is
    fine to ship; only an unenforced, past-sunset one is a release blocker.
    Reported under REL001, the same rule id `release_gate`'s other findings
    use, since this is a release-blocking condition, not a new independent
    failure mode of its own."""
    from frob.gates import _site_from_edge_origin

    violations: list[Violation] = []
    for edge in _deprecated_edges(snapshot):
        sunset = edge.attrs.get("sunset", "")
        if not sunset or not _deprecated_is_expired(sunset, current_date=current_date):
            continue
        file, line = _site_from_edge_origin(edge.origin)
        violations.append(
            Violation(
                rule="REL001",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"REL001: frob:deprecated {edge.target} at {edge.src} "
                    f"(ticket={edge.attrs.get('ticket', '')!r}) is past its "
                    f"sunset ({sunset}); remove it (or extend `sunset` with a "
                    f"written reason) before a release, run: frob check"
                ),
            )
        )
    return tuple(violations)
