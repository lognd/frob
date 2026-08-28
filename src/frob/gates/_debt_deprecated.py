"""frob.gates._debt_deprecated -- DEBT00x (`frob:debt`) and DEPR00x
(`frob:deprecated`) gate families, split out of `frob.gates.__init__`
(T-1115, following T-1072/T-1077's precedent).

Kept together because `frob:deprecated` is `frob:debt` generalized to the
API surface itself (DEPR001-004 mirror DEBT001-003's shape one-for-one;
DEPR005 is deprecated-specific, T-0639) and both feed the same REL001
release-blocking check in `run_gates`'s spine.
"""
# frob:waive LARGE001 reason="T-1651-grade review (T-2828): this module's own \
# docstring already states the reason these two families are kept together -- \
# frob:deprecated is frob:debt generalized to the API surface itself (DEPR001-004 \
# mirror DEBT001-003's shape one-for-one), and both feed the same REL001 \
# release-blocking check in run_gates's spine. This is deliberately-paired-by-design \
# (T-1115 following T-1072/T-1077 precedent), not two bolted-together unrelated \
# concerns."

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from tree_sitter import Node, Tree

from frob.exports import _IMPORT_LINE_RE
from frob.gates._deprecated_baseline import (
    BASELINE_REL,
    file_reference_counts,
    load_deprecated_baseline,
)
from frob.gates._models import DebtEntry, DeprecatedEntry, Severity, Violation
from frob.graph import Edge, EdgeKind, GraphSnapshot
from frob.lang import iter_identifiers, parse_file, raw_tree
from frob.logging import get_logger
from frob.tickets import TicketQueue
from frob.xref import _collect_source_files, _definition_symbols

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


def _call_node_text(node: Node, source: bytes) -> str:
    """Decode `node`'s own source bytes (T-2178's local escape-hatch
    helper -- `frob.lang._extract`'s equivalent is private to that module,
    and `raw_tree`'s whole point is handing back real tree-sitter `Node`s
    for a caller to read directly rather than exposing a second normalized
    API for it)."""
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _callee_bare_name(func_node: Node, source: bytes) -> str | None:
    """The bare identifier a `call` node's `function` field resolves to:
    the name itself for a bare call (`run(...)`), or the trailing
    `.attribute` for a qualified call (`mod.run(...)` -> `"run"`),
    mirroring `_bare_symbol_name`'s own last-segment convention. `None`
    for any other callee shape (a call on a call result, a subscript,
    etc.) -- those cannot resolve to a bare deprecated-symbol name at all."""
    if func_node.type == "identifier":
        return _call_node_text(func_node, source)
    if func_node.type == "attribute":
        attr = func_node.child_by_field_name("attribute")
        return _call_node_text(attr, source) if attr is not None else None
    return None


def _python_call_and_alias_sites(
    tree: Tree, source: bytes
) -> tuple[dict[str, list[int]], dict[str, str]]:
    """AST-derived call sites and import aliases for one parsed python tree
    (T-2178): resolves `deprecated_current_references`'s "is this a call"
    and "was this symbol imported under another name" questions from real
    tree-sitter structure instead of `_looks_like_call`'s former raw-line
    regex, which decided from the WHOLE source line's text and so matched a
    `symbol(` sequence sitting inside a same-line trailing comment or
    string literal just as readily as a genuine call (T-2178 acceptance
    [1]) -- a comment/string is an opaque tree-sitter leaf with no `call`
    or `identifier` children inside it, so this walk structurally cannot
    see into one.

    Returns `(calls, aliases)`:
    - `calls[name]` -- every 1-based line where `name` (a bare identifier,
      or a qualified call's trailing attribute segment) is the CALLEE of a
      real `call` node.
    - `aliases[local_name]` -- for `from mod import real as local`, the
      locally-bound name mapped back to the imported bare name, so a call
      reached only through the alias (`local(...)`) can still be
      recognised as a reference to `real` (T-2178 acceptance [2] -- the
      former bare-identifier index had no notion of an alias at all, since
      it indexed literal identifier TEXT and an aliased call site never
      contains the original name as a token anywhere)."""
    calls: dict[str, list[int]] = {}
    aliases: dict[str, str] = {}

    def visit(node: Node) -> None:
        node_type = node.type
        if node_type == "call":
            func = node.child_by_field_name("function")
            if func is not None:
                name = _callee_bare_name(func, source)
                if name:
                    calls.setdefault(name, []).append(node.start_point[0] + 1)
        elif node_type == "import_from_statement":
            for name_node in node.children_by_field_name("name"):
                if name_node.type == "aliased_import":
                    real = name_node.child_by_field_name("name")
                    alias = name_node.child_by_field_name("alias")
                    if real is not None and alias is not None:
                        aliases[_call_node_text(alias, source)] = _call_node_text(
                            real, source
                        )
        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return calls, aliases


@dataclass(frozen=True)
class _DeprecatedRefIndex:
    """T-1207: one repo-wide identifier index, built by a SINGLE pass over
    every Python source file under a root, shared across every deprecated
    symbol `_depr005_violations` answers in one gate run -- replacing the
    prior per-symbol double full-repo scan (`exports_consumers` +
    `xref`, each itself a full walk) that made DEPR005's cost grow
    linearly with the number of baselined `frob:deprecated` symbols.

    `identifier_hits[name]` is every `(file, line, context)` occurrence of
    bare identifier `name` across the whole tree, in file-then-line order
    (mirrors what a per-symbol `xref` call used to return, just gathered
    for all names at once). `definition_sites[name]` is every `(file,
    line)` where `name` is itself defined (function/class/method), and
    `first_definition_file[name]` is the first such file in sorted file
    order -- both needed to reproduce `xref`'s own-declaration and
    own-defining-file exclusions without re-deriving them from a fresh
    per-symbol `xref()` call."""

    identifier_hits: dict[str, list[tuple[str, int, str]]] = field(default_factory=dict)
    definition_sites: dict[str, set[tuple[str, int]]] = field(default_factory=dict)
    first_definition_file: dict[str, str] = field(default_factory=dict)
    #: T-2178: per-file `{callee_bare_name: [line, ...]}`, from a real
    #: `call` node's `function` field -- never a raw-text regex match, so a
    #: same-line comment or string mentioning `name(` cannot register.
    file_calls: dict[str, dict[str, list[int]]] = field(default_factory=dict)
    #: T-2178: per-file `{local_alias_name: real_bare_name}` from
    #: `from mod import real as local` -- lets a call reached only through
    #: an import alias still resolve back to the deprecated symbol it
    #: actually calls.
    file_aliases: dict[str, dict[str, str]] = field(default_factory=dict)


def _index_identifier_hits(path: Path, rel: str, index: _DeprecatedRefIndex) -> None:
    """`_build_deprecated_ref_index`'s identifier-hit pass for one file
    (T-2178 split, keeping that function under ARCH001's threshold):
    populates `index.identifier_hits[name]` with every `(rel, line,
    context)` occurrence, used for import-line detection (`_IMPORT_LINE_RE`)
    -- the actual "is this a call" decision has moved to
    `_index_call_and_alias_sites`, which reads real AST structure instead
    of this raw-line context text."""
    ids_result = iter_identifiers(path)
    if not ids_result.is_ok:
        return
    try:
        src_lines = path.read_bytes().decode(errors="replace").splitlines()
    except OSError:
        src_lines = []
    try:
        for name, line in ids_result.danger_ok:
            ctx = src_lines[line - 1] if 0 < line <= len(src_lines) else ""
            index.identifier_hits.setdefault(name, []).append((rel, line, ctx))
    except Exception:
        # A single file's identifier/line data being surprising (an
        # out-of-range span, unexpected shape) must not abort the
        # whole-tree index build for every OTHER file (EXHAUST001/
        # EXHAUST002, T-1371) -- same "one bad input, keep going" posture
        # every pass in this module's index build shares.
        _log.debug("_index_identifier_hits: skipping %s (bad identifiers)", rel)


def _index_definition_sites(path: Path, rel: str, index: _DeprecatedRefIndex) -> None:
    """`_build_deprecated_ref_index`'s definition-site pass for one file
    (T-2178 split): populates `index.definition_sites`/`first_definition_file`
    from `parse_file`'s own symbol table."""
    parsed_result = parse_file(path)
    if not parsed_result.is_ok:
        return
    try:
        for sym in _definition_symbols(parsed_result.danger_ok.symbols):
            _, _, name = sym.qualname.rpartition(".")
            index.definition_sites.setdefault(name, set()).add((rel, sym.span[0]))
            index.first_definition_file.setdefault(name, rel)
    except Exception:
        _log.debug("_index_definition_sites: skipping %s (bad symbols)", rel)


def _index_call_and_alias_sites(
    path: Path, rel: str, index: _DeprecatedRefIndex
) -> None:
    """`_build_deprecated_ref_index`'s call/alias-site pass for one file
    (T-2178 split): populates `index.file_calls`/`file_aliases` from real
    tree-sitter structure, replacing the former raw-line regex
    (`_looks_like_call`) that decided "is this a call" from the WHOLE
    source line's text."""
    tree_result = raw_tree(path)
    if not tree_result.is_ok:
        return
    try:
        tree, source, _lang = tree_result.danger_ok
        calls, aliases = _python_call_and_alias_sites(tree, source)
        if calls:
            index.file_calls[rel] = calls
        if aliases:
            index.file_aliases[rel] = aliases
    except Exception:
        # Same "one bad input, keep going" posture as the two passes
        # above (EXHAUST001/EXHAUST002, T-1371) -- a surprising tree shape
        # in one file must not abort the whole-tree index build for every
        # other file.
        _log.debug("_index_call_and_alias_sites: skipping %s (bad call sites)", rel)


def _build_deprecated_ref_index(root: Path) -> _DeprecatedRefIndex:
    """One full pass over every Python file under `root` (T-1207),
    populating a `_DeprecatedRefIndex` that every baselined `frob:deprecated`
    symbol in the run answers `deprecated_current_references` from --
    instead of each symbol independently re-walking the whole tree via
    `exports_consumers`+`xref` (the O(files * symbols) cost this ticket
    exists to collapse to O(files + symbols)). T-2178 split the per-file
    work into `_index_identifier_hits`/`_index_definition_sites`/
    `_index_call_and_alias_sites`, each a separate pass over the same file
    (still one `_collect_source_files` walk overall)."""
    index = _DeprecatedRefIndex()
    for path in _collect_source_files(root, "python"):
        try:
            rel = str(path.relative_to(root)) if root.is_dir() else path.name
        except ValueError:
            rel = str(path)

        _index_identifier_hits(path, rel, index)
        _index_definition_sites(path, rel, index)
        _index_call_and_alias_sites(path, rel, index)
    return index


def _references_from_index(symbol: str, index: _DeprecatedRefIndex) -> frozenset[str]:
    """`deprecated_current_references`'s answer for `symbol`, read from an
    already-built `_DeprecatedRefIndex` (T-1207) rather than re-scanning the
    tree -- see that function's docstring for the exact semantics this
    reproduces.

    T-1338 (PERF003): a single pass over `hits` collects import-line
    references and the set of importing files; a second pass then only
    iterates `importing_files` and looks each up in `index.file_calls` (T-2178:
    real `call`-node sites, not a raw-text regex), instead of re-scanning
    the full `hits` list a second time to re-derive which lines belong to
    which file (the O(n) rescan PERF003 flagged as the nested-loop-shaped
    equality-join pattern).

    T-2178: a file that imports `symbol` under an alias (`from mod import
    symbol as local`) is folded into `importing_files` too, even though the
    bare identifier `symbol` never appears there as a token -- its calls
    are read from `file_calls[file][local]` and reported the same as a
    direct call."""
    hits = index.identifier_hits.get(symbol, ())
    def_sites = index.definition_sites.get(symbol, frozenset())
    definition_file = index.first_definition_file.get(symbol)

    refs: set[str] = set()
    importing_files: set[str] = set()
    for file, line, ctx in hits:
        if (file, line) in def_sites:
            continue
        if _IMPORT_LINE_RE.match(ctx):
            refs.add(f"{file}:{line}")
            importing_files.add(file)

    alias_locals_by_file: dict[str, set[str]] = {}
    for file, aliases in index.file_aliases.items():
        # frob:waive PERF003 reason="single-pass comprehension over one file's own small alias dict (typically 0-1 entries), not an O(n*m) equality join between two collections; the outer loop's bound var (file) never appears in the inner == at all -- PERF003's relaxed lexical scan false-positives on any comprehension following an unrelated outer loop"  # noqa: E501
        locals_for_symbol = {local for local, real in aliases.items() if real == symbol}
        if locals_for_symbol:
            importing_files.add(file)
            alias_locals_by_file[file] = locals_for_symbol

    for file in importing_files:
        if definition_file is not None and file == definition_file:
            continue
        file_calls = index.file_calls.get(file, {})
        for line in file_calls.get(symbol, ()):
            if (file, line) not in def_sites:
                refs.add(f"{file}:{line}")
        for local in alias_locals_by_file.get(file, ()):
            for line in file_calls.get(local, ()):
                if (file, line) not in def_sites:
                    refs.add(f"{file}:{line}")
    return frozenset(refs)


# frob:doc docs/modules/gates.md#depr005-new-caller-baseline-ratchet-t-0639-redesigned-t-1052  # noqa: E501
# frob:tests tests/test_gates.py::TestDeprecatedGate.test_depr005_reference_set_combines_consumers_and_xref kind="unit"  # noqa: E501
# frob:tests tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating.test_unrelated_same_name_call_in_non_importing_file_is_excluded kind="unit"  # noqa: E501
def deprecated_current_references(symbol: str, root: Path) -> frozenset[str]:
    """The current `file:line` reference set for bare identifier `symbol`
    under `root` (T-0639, callgraph-resolved as of T-1052, index-backed as
    of T-1207): the union of import-statement consumers (T-0876, what
    `frob.exports.exports_consumers` used to answer standalone) and
    Python-scoped, call-shaped identifier usages (`_python_call_and_alias_sites`,
    AST-derived as of T-2178) --
    but a call-shaped usage only counts when it falls in a file that
    itself imports `symbol`, excluding any usage in the symbol's own
    defining file (its declaration line and any purely internal same-file
    mention are not a "new caller").

    A standalone caller (this function, called directly rather than
    through `_depr005_violations`'s shared index) still pays one full-repo
    pass -- `_build_deprecated_ref_index` builds an index for every
    identifier in one walk regardless of how many symbols will be looked
    up against it, so a single-symbol call is exactly as expensive as
    before; the win is `_depr005_violations` building the index ONCE and
    answering every baselined symbol from it, instead of once per symbol.

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
    index = _build_deprecated_ref_index(root)
    return _references_from_index(symbol, index)


def _depr005_edge_violations(
    edge: Edge, ticket_id: str, index: _DeprecatedRefIndex, entry: object
) -> tuple[Violation, ...]:
    """T-1338 (ARCH001): the per-edge body of `_depr005_violations` --
    resolves `edge`'s current reference set against its already-loaded
    baseline `entry` and returns one `Violation` per file whose resolved
    reference COUNT exceeds what is baselined (see `_depr005_violations`'s
    own docstring for the full DEPR005 semantics this reproduces).
    Extracted so `_depr005_violations` itself stays under the long-function
    threshold; `entry` is a `DeprecatedBaselineEntry` (typed loosely here to
    avoid importing that private type just for an annotation)."""
    violations: list[Violation] = []
    symbol = _bare_symbol_name(edge.src)
    current_refs = _references_from_index(symbol, index)
    current_counts = file_reference_counts(current_refs)
    baseline_counts = entry.file_counts()  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
    grown_files = sorted(
        file
        for file, count in current_counts.items()
        if count > baseline_counts.get(file, 0)
    )
    for grown_file in grown_files:
        # frob:waive PERF004 reason="T-1115: grown_lines sorts the current reference \
        # set's own line numbers for THIS grown_file only -- a different, \
        # per-iteration distinct subset each time, not a shared re-sort hoistable out \
        # of the loop"
        grown_lines = sorted(
            int(ref.rpartition(":")[2])
            for ref in current_refs
            if ref.rpartition(":")[0] == grown_file and ref.rpartition(":")[2].isdigit()
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
    DEPR002 already fired for the same edge, same posture as DEPR003/004.

    T-1338 (PERF008): the eligible-edge filter (open ticket AND a baseline
    entry) runs as its own pass BEFORE `_build_deprecated_ref_index` is
    ever called, so the loop-invariant, transitively fs-walking index build
    happens at most once, entirely outside any loop -- not merely memoized
    behind an `if index is None` guard inside one (PERF008's syntactic
    loop-invariant-call detector cannot see through that guard; hoisting
    the call out of loop-body position is what actually satisfies it, and
    it also means an all-ineligible-edges run never builds the index at
    all, same as before)."""
    from frob.gates import _OPEN_STATES

    baseline = load_deprecated_baseline(root)
    eligible: list[tuple[Edge, str, object]] = []
    for edge in _deprecated_edges(snapshot):
        ticket_id = edge.attrs.get("ticket", "")
        target = queue.tickets.get(ticket_id)
        if target is None or target.state not in _OPEN_STATES:
            continue
        entry = baseline.for_symbol(edge.src)
        if entry is None:
            _log.debug("DEPR005: %s not yet baselined, skipping", edge.src)
            continue
        eligible.append((edge, ticket_id, entry))

    if not eligible:
        return ()

    # T-1207/T-1338: one repo-wide index, built ONCE outside any loop, shared
    # across every eligible edge below.
    index = _build_deprecated_ref_index(root)

    violations: list[Violation] = []
    for edge, ticket_id, entry in eligible:
        violations.extend(_depr005_edge_violations(edge, ticket_id, index, entry))
    return tuple(violations)


# frob:ticket T-3228
# frob:enforces CHK-GATE-DEPR006
# frob:tests tests/unit/gates/test_deprecated_baseline.py::TestDepr006ProducerAbandoned.test_abandoned_producer_fires_error kind="unit"  # noqa: E501
# frob:tests tests/unit/gates/test_deprecated_baseline.py::TestDepr006ProducerAbandoned.test_pinned_producer_stays_quiet kind="unit"  # noqa: E501
def _depr006_producer_abandoned(root: Path) -> tuple[Violation, ...]:
    """DEPR006 (T-3228, error): `frob.gates._lock_producer.producer_status`
    for the `deprecated-baseline` lock reads `ABANDONED` -- unpinned, and
    `code_commits_since` has crossed `ABANDONED_CODE_COMMIT_THRESHOLD`
    with no re-stamp. Same shape as TEST012's coverage-lock producer
    check (`frob.gates.__init__._test012_producer_abandoned`): DEPR005's
    content check alone (does a symbol's reference set exceed what is
    baselined) cannot catch a lock nobody has re-stamped in months but
    that happens to still cover every live caller -- this is the LOUD,
    separate signal that the PRODUCER (`tighten_deprecated_baseline`)
    itself has stopped running."""
    from frob.gates._lock_producer import KNOWN_LOCKS, producer_status

    lock = next(entry for entry in KNOWN_LOCKS if entry.name == "deprecated-baseline")
    status = producer_status(root, lock)
    if status.verdict != "ABANDONED":
        return ()
    return (
        Violation(
            rule="DEPR006",
            severity=Severity.ERROR,
            file=str(BASELINE_REL),
            line=0,
            message=(
                "DEPR006: deprecated-baseline lock producer looks ABANDONED "
                f"-- {status.code_commits_since} commit(s) touched "
                f"{lock.code_glob} since {BASELINE_REL} was last stamped "
                f"({status.last_stamp_date}) with no re-stamp and no pin; "
                "re-run tighten_deprecated_baseline and commit the "
                "refreshed lock, or if this IS a deliberate freeze add a "
                'top-level {"pin": {"reason": "...", "ticket": "T-####"}} '
                f"to {BASELINE_REL}"
            ),
        ),
    )


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
    """DEPR001-006 (T-0576, DEPR005 T-0639, DEPR006 T-3228):
    `frob:deprecated`'s states -- a malformed directive, a directive bound
    to a non-open ticket, a directive still in its warning window, a
    directive past its sunset date, a directive whose reference set
    gained a new, un-baselined caller, and (DEPR006) the baseline lock's
    own producer looking abandoned (see `_depr006_producer_abandoned`).
    `current_date` (`YYYY-MM-DD`) is injected rather than computed here
    so this stays a pure function of its inputs, matching `debt_gate`;
    `root` is needed by DEPR005 (to resolve
    `frob-deprecated-baseline.lock.json` and the current reference set)
    and DEPR006 (to measure the lock's own git history)."""
    return (
        *_depr001_violations(snapshot),
        *_depr002_violations(snapshot, queue),
        *_depr003_violations(snapshot, queue, current_date=current_date),
        *_depr004_violations(snapshot, queue, current_date=current_date),
        *_depr005_violations(snapshot, queue, root, current_date=current_date),
        *_depr006_producer_abandoned(root),
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


# frob:ticket T-2581
# frob:enforces CHK-GATE-REL001
# frob:tests tests/test_gates.py::TestReleaseOpenMilestoneViolations.test_open_ticket_in_cut_milestone_refuses  # noqa: E501
# frob:tests tests/test_gates.py::TestReleaseOpenMilestoneViolations.test_open_ticket_in_other_milestone_does_not_refuse  # noqa: E501
# frob:tests tests/test_gates.py::TestReleaseOpenMilestoneViolations.test_terminal_ticket_in_cut_milestone_does_not_refuse  # noqa: E501
# frob:tests tests/test_gates.py::TestReleaseOpenMilestoneViolations.test_no_open_tickets_in_milestone_succeeds  # noqa: E501
# frob:tests tests/test_gates.py::TestReleaseOpenMilestoneViolations.test_names_every_blocking_ticket  # noqa: E501
# frob:tests tests/test_gates.py::TestReleaseOpenMilestoneViolations.test_queue_unavailable_does_not_crash  # noqa: E501
def _release_open_milestone_violations(
    root: Path, release_version: str
) -> tuple[Violation, ...]:
    """REL001 (M6, T-2581): refuse to cut release `release_version` while
    any OPEN ticket carries that EFFECTIVE milestone (declared, inherited,
    or the repo's configured `[tickets].default_milestone` --
    `frob.tickets._doable.effective_milestone`, the SAME resolution
    `doable`'s own display and the MILE00x family (M1-M5, T-2574/2576/
    2577/2579/2580) use, so this check never disagrees with what an
    operator sees in `frob ticket doable`). This is M2's own dependency
    (T-2576's backfill/default resolution) made load-bearing here for the
    first time: without every open ticket actually carrying a resolvable
    milestone, comparing "milestone X" against the release being cut would
    not mean anything.

    Names every blocking ticket id in the message (never a bare count) --
    an operator who cannot see the blocking set will override the gate
    blind, the same reasoning `_release_open_debt_violations` above
    already reports each individual `frob:debt` site by name rather than
    a total.

    Loads the ticket queue independently (`frob.tickets.load_queue`)
    rather than requiring `release_gate`'s caller to thread one through --
    `release_gate`'s signature (`root, snapshot, ticket_id`) lives outside
    this module's scope, and a queue load failure here degrades to "skip
    this check" (logged, not raised) the same fail-open shape
    `_default_milestone` (`frob.tickets._doable`) uses for an unreadable
    `frob.toml` -- a release gate must not hard-crash the whole `frob
    check`/release-cut run over a queue-load hiccup a DIFFERENT gate
    (`tickets`/`milestone`) already reports on its own terms."""
    from frob.tickets import _OPEN_STATES, load_queue
    from frob.tickets._doable import effective_milestone

    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.warning(
            "release_gate: ticket queue unavailable (%s) -- skipping the "
            "REL001 open-milestone-tickets check for this run",
            queue_result.danger_err,
        )
        return ()
    queue = queue_result.danger_ok

    blockers: list[str] = []
    for t in sorted(queue.tickets.values(), key=lambda t: t.id):
        if t.state not in _OPEN_STATES:
            continue
        milestone, _source = effective_milestone(queue, t, root)
        if milestone == release_version:
            blockers.append(t.id)
    if not blockers:
        return ()
    return (
        Violation(
            rule="REL001",
            severity=Severity.ERROR,
            file="tickets.md",
            line=0,
            message=(
                f"REL001: release {release_version} cannot be cut -- "
                f"{len(blockers)} open ticket(s) still carry (effective) "
                f"milestone {release_version}: {', '.join(blockers)}; "
                f"close them, drop them, or re-milestone them before "
                f"cutting this release"
            ),
        ),
    )
