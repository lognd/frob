"""REG001-REG007: the exhaustiveness drift-lock over docs/design/registry/
*.yaml (docs/design/registry/EXHAUSTIVENESS-GATE.md, T-0343, unified onto
`frob.registry`'s typed model by T-0407).

LINCHPIN / ANTI-LIE MANDATE. Root cause this module closes: the unified
design-knowledge registry (`docs/design/registry/*.yaml`, ~1950 entries
consolidating 11 design corpora) was built, documented as a "unified
machine-readable registry", and then read by ZERO code -- catalogued, not
enforced. No gate was watching that gap. This module is the watcher: a
FAIL-CLOSED gate, wired into `frob check` at ERROR severity as a real
`Violation` family, not a skippable pytest and not advisory-only. A
catalogued-but-undispositioned entry can never pass silently again.

T-0407 unification: parsing (disposition grammar, YAML loading, entry
shape) now lives ONCE in `frob.registry._models` -- `RegistryEntry`,
`Disposition`, `load_registry_dir` -- instead of duplicated inline here.
This module is purely the POLICY layer over that typed model: which
`DispositionKind` earns which `Violation`, verified against live state
(`known_rules`, the ticket `TicketQueue`, the cross-file id set).

Every registry entry's `disposition` field is parsed against a strict
grammar and VERIFIED, never trusted at face value:

- ``handled_by:<rule-id>`` -- valid only if `<rule-id>` names a rule this
  build's own gate/policy rule registry actually knows about (cross-
  checked against the caller-supplied `known_rules`, which is
  `frob.gates._KNOWN_GATE_RULES` unioned with the loaded policy rule ids
  at call time). A `handled_by` naming a nonexistent rule is REG002 --
  writing `handled_by: SEC999` when SEC999 does not fire is exactly the
  lie this gate exists to catch.
- ``deferred:<ticket-id>`` -- valid only if `<ticket-id>` resolves to a
  ticket in the loaded `TicketQueue` that is NOT `done`/`dropped`. A
  deferral pointing at a closed or nonexistent ticket is REG003 -- the
  work was never actually deferred anywhere real.
- ``duplicate_of:<id>`` / ``duplicate-of:<id>`` -- valid only if `<id>`
  resolves to another real entry id somewhere in the loaded registry
  (across all files, not just the same file). A dangling duplicate
  reference is REG004.
- ``out_of_scope:<reason>`` / ``out-of-scope:<reason>`` /
  ``out-of-scope(<reason>)`` -- REG001 (ERROR) if `<reason>` is empty.
  T-0680 additionally routes non-empty `<reason>` through the same
  `caught_by` verification T-0382 built for `strata`'s `OutOfScopeEntry`/
  `BenignCapability`/`OutOfScopeRegulation` models
  (`frob.strata._threat._caught_by_unresolved_tokens`): `<reason>` must
  either name a real, live catching control (a rule-id- or CWE-id-shaped
  token that resolves) or be a substantive `"none -- <explanation>"`
  reasoned-none disclosure -- anything else is REG011 (WARN; see
  `_classify_out_of_scope_caught_by` below).
- anything else -- a missing `disposition`, the bare literal `pending`,
  the bare literal `addressed` with no `handled_by` rule attached, or any
  string that does not parse under the grammar above -- is REG001,
  undispositioned. `addressed` with nothing backing it is deliberately
  treated as undispositioned rather than accepted at face value: an
  unverifiable claim of "this is handled" is exactly the unaccountable
  state this gate exists to make loud.

REG005 is the exhaustiveness meta-test: each registry file MAY declare a
top-level `total: <int>`; if present, it must equal the file's actual
`len(entries)`. A file that declares no `total` is not checked (nothing to
compare against) -- this is intentionally the narrowest form of the
denominator check: it catches a FUTURE silent entry drop/duplication in a
file that has opted in to declaring its own count, not a retroactive claim
about files that never stated one.

REG004 also covers RECONCILIATION.md's documented SPLIT findings (finding
(b): named concepts appearing under multiple, currently unlinked ids
across registry files) -- any registry id RECONCILIATION.md's own split
table names is required to carry at least one `cross_refs` entry; an id
still showing `cross_refs: []` despite being documented as split is a
live, unresolved split and fails REG004.

T-0407 closes two early-exit/partial-coverage holes the pre-unification
gate had:

- REG006 -- a list item under an `entries:`/`*_entries:` key that is not a
  mapping, or has no string `id`, was previously SILENTLY skipped (`if not
  isinstance(entry, dict)... continue`, no violation ever raised). That is
  exactly the "enumerate a universe, then silently drop part of it" shape
  T-0407 exists to close: a malformed entry now surfaces as a loud REG006
  instead of vanishing from the count with no trace.
- REG007 -- the same `id` string defined by TWO OR MORE entries anywhere
  in the loaded registry (as opposed to a `duplicate_of:` reference, which
  REG004 already covers) means the cross-file id index silently keeps only
  the last-seen entry and drops every earlier one from `frob registry
  audit`'s accounting -- REG007 makes that collision loud instead of a
  silent last-write-wins.

On first turn-on this gate is RED for the ~1950 entries the registry
currently carries (~1006 explicitly `pending`, ~27 bare `addressed`, plus
every CWE entry's inherited `duplicate-of`/`out-of-scope` disposition
which predates and does not yet match this module's `handled_by`/
`deferred`/`out_of_scope` grammar) -- that red is the honest current
state. It is driven green only by the per-registry reconciliation tickets
(T-0384..T-0392), never by suppressing or bulk-waiving this gate.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import re
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.graph._models import EdgeKind, GraphSnapshot
from frob.logging import get_logger
from frob.registry._models import (
    Disposition,
    DispositionKind,
    RegistryEntry,
    RegistryFile,
    load_registry_dir,
)
from frob.registry._staleness import missing_gate_rule_ids

# NOTE: frob.strata._threat is imported LAZILY (inside the functions below,
# not here at module scope) -- frob.gates.__init__ imports this module
# during its own top-level import, which can happen mid-initialization of
# frob.strata._threat itself (frob.strata._threat -> frob.strata._effects
# -> frob.vet -> frob.vet._models -> frob.gates._models, which triggers
# frob.gates.__init__ -> this module). A module-scope import here hits
# that partially-initialized module and raises ImportError; a lazy,
# call-time import (same pattern already used by
# frob.gates.__init__._policy_gate/_native_staleness_gate and others for
# frob.strata symbols) sidesteps it.
from frob.tickets._models import TicketQueue, TicketState

_log = get_logger(__name__)

__all__ = ["registry_gate", "REGISTRY_FILES", "path_ever_tracked"]

# Every registry file this gate reads, as bare basenames -- quoted string
# literals here are what makes REF001/REF002 (frob.gates._refs's
# anti-orphan gate) stop treating these files as orphans: the auto-scan
# token-reach check matches a target's full basename appearing as a quoted
# literal in a referencing file's text (frob.gates._refs._tokens_reach),
# and each file below also carries a `frob:used-by
# src/frob/gates/_registry_exhaustiveness.py` declaration for the
# declared-consumer half of that same check.
# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#registry-exhaustiveness-drift-lock-t-0343  # noqa: E501
REGISTRY_FILES: tuple[str, ...] = (
    "arch-checks.yaml",
    "compliance.yaml",
    "evasion.yaml",
    "patterns.yaml",
    "pii.yaml",
    "secrets.yaml",
    "supply-chain.yaml",
    "system-design.yaml",
    "weaknesses.yaml",
    # T-0424: frob's own check-coverage, the reflexive registry -- the
    # unified model makes adding a new registry instance exactly this,
    # a filename here, not a second mechanism.
    "check-coverage.yaml",
)

# The RECONCILIATION.md split-finding table this gate cross-checks against
# (finding (b)); a quoted literal here also closes REF001/REF002 for that
# file the same way REGISTRY_FILES does for the manifests themselves.
_RECONCILIATION_FILE = "RECONCILIATION.md"

# T-0560: check-coverage.yaml's gate_rule_entries is the ONE file REG010's
# staleness check runs against -- a quoted literal here also closes
# REF001/REF002 for it the same way REGISTRY_FILES does.
_CHECK_COVERAGE_FILE = "check-coverage.yaml"

# T-0343 named this a tracked gap ("out_of_scope dispositions are meant to
# route through Area-2's VERIFIED caught_by mechanism, T-0382, which does
# not exist in this build yet"). T-0680 closes it: `_classify_out_of_
# scope_caught_by` below routes registry-YAML `out_of_scope:<reason>`
# strings through that now-built T-0382 mechanism (REG011).


# frob:enforces CHK-GATE-REG002
def _classify_handled_by(
    entry_id: str, rule: str, known_rules: frozenset[str]
) -> tuple[str, str] | None:
    """REG002 when `handled_by:<rule>` names a rule id absent from the live
    gate/policy registry -- split out of `_classify` for ARCH001."""
    if rule not in known_rules:
        return (
            "REG002",
            f"REG002: {entry_id} disposition handled_by:{rule} names a "
            f"rule that does not exist in the live gate/policy rule "
            f"registry -- dangling enforcement reference",
        )
    return None


# frob:enforces CHK-GATE-REG003
def _classify_deferred(
    entry_id: str, ticket_id: str, queue: TicketQueue
) -> tuple[str, str] | None:
    """REG003 when `deferred:<ticket>` names a missing or already-closed
    ticket -- split out of `_classify` for ARCH001."""
    ticket = queue.tickets.get(ticket_id)
    if ticket is None:
        return (
            "REG003",
            f"REG003: {entry_id} disposition deferred:{ticket_id} names "
            f"a ticket that does not exist",
        )
    if ticket.state in (TicketState.DONE, TicketState.DROPPED):
        return (
            "REG003",
            f"REG003: {entry_id} disposition deferred:{ticket_id} names "
            f"a {ticket.state.value} ticket -- deferral to a closed "
            f"ticket is not a real deferral",
        )
    return None


def _classify_duplicate(
    entry_id: str, target: str, all_entry_ids: frozenset[str]
) -> tuple[str, str] | None:
    """REG004 when `duplicate_of:<target>` names an id absent from the
    whole registry -- split out of `_classify` for ARCH001."""
    if target not in all_entry_ids:
        return (
            "REG004",
            f"REG004: {entry_id} disposition duplicate_of:{target} "
            f"names an id that does not exist anywhere in the "
            f"registry -- dangling duplicate reference",
        )
    return None


# frob:enforces CHK-GATE-REG001
def _classify_out_of_scope(entry_id: str, reason: str) -> tuple[str, str] | None:
    """REG001 when `out_of_scope` carries no reason text -- split out of
    `_classify` for ARCH001."""
    if not reason.strip():
        return (
            "REG001",
            f"REG001: {entry_id} disposition out_of_scope has no reason",
        )
    return None


def _is_reasoned_none(reason: str) -> bool:
    """True if `reason` is a SUBSTANTIVE `"none -- <explanation>"`
    disclosure per T-0382's `CAUGHT_BY_NONE_MARKER` convention (an honest
    admission that no compensating control exists yet, WITH the actual
    explanation) -- the bare word `"none"` alone, with nothing after it,
    is not substantive and does not count."""
    from frob.strata._threat import CAUGHT_BY_NONE_MARKER  # lazy: see module note

    stripped = reason.strip()
    if not stripped.lower().startswith(CAUGHT_BY_NONE_MARKER):
        return False
    remainder = stripped[len(CAUGHT_BY_NONE_MARKER) :].strip(" -")
    return bool(remainder)


# frob:ticket T-0680
# frob:enforces CHK-GATE-REG011
def _classify_out_of_scope_caught_by(
    entry_id: str,
    reason: str,
    known_rules: frozenset[str],
    cataloged_cwes: frozenset[str],
) -> Violation | None:
    """REG011 (T-0680): the registry-YAML `out_of_scope:<reason>` surface
    routed through the same `caught_by` verification T-0382 built for
    `strata`'s `OutOfScopeEntry`/`BenignCapability`/`OutOfScopeRegulation`
    models (`frob.strata._threat._caught_by_unresolved_tokens`, reused
    here rather than re-implemented -- charter: no duplication). An
    `out_of_scope` reason must either (a) name a real, live catching
    control -- a rule-id- or CWE-id-shaped token that resolves against
    `known_rules`/`cataloged_cwes` -- or (b) be a SUBSTANTIVE
    `"none -- ..."` reasoned-none disclosure (`_is_reasoned_none`). A
    reason that names no catching control at all AND is not a reasoned-
    none is exactly the unaccountable excuse this rule exists to make
    loud; a reason that DOES name a control but the control does not
    resolve is the fabricated-reference case THREAT006/COMPLIANCE004
    already catch for the `strata` surface -- REG011 is that same check
    for the registry-YAML surface T-0343's original gate left unrouted.

    WARN, not ERROR, matching REG008/REG009's first-turn-on precedent
    (`frob.gates._registry_exhaustiveness.registry_gate`'s own docstring):
    this repo's registry carries hundreds of pre-existing `out_of_scope`
    entries (`patterns.yaml`, `compliance.yaml`, ...) written before this
    check existed, an honest debt this pass surfaces rather than silently
    retrofits reasons for -- promoting to ERROR is a future reconciliation
    ticket's job, not this one's."""
    from frob.strata._threat import (  # lazy: see module note
        _caught_by_referenced_tokens,
        _caught_by_unresolved_tokens,
    )

    if _is_reasoned_none(reason):
        return None
    rule_ids, cwe_ids = _caught_by_referenced_tokens(reason)
    if not rule_ids and not cwe_ids:
        return Violation(
            rule="REG011",
            severity=Severity.WARN,
            file="",
            line=0,
            message=(
                f"REG011: {entry_id} disposition out_of_scope reason "
                f"{reason!r} names no catching control (no rule-id- or "
                f"CWE-id-shaped token) and is not a substantive "
                f"'none -- <explanation>' reasoned-none disclosure -- an "
                f"unaccountable excuse"
            ),
        )
    unresolved = _caught_by_unresolved_tokens(reason, known_rules, cataloged_cwes)
    if unresolved:
        named = ", ".join(sorted(unresolved))
        return Violation(
            rule="REG011",
            severity=Severity.WARN,
            file="",
            line=0,
            message=(
                f"REG011: {entry_id} disposition out_of_scope reason "
                f"{reason!r} references unknown control(s) that do not "
                f"exist: {named}"
            ),
        )
    return None


def _classify(
    entry_id: str,
    disposition: Disposition,
    known_rules: frozenset[str],
    all_entry_ids: frozenset[str],
    queue: TicketQueue,
) -> tuple[str, str] | None:
    """`(rule, message)` for the violation `entry_id`'s typed `disposition`
    earns, or `None` if it is a fully verified, honest disposition.

    Every branch VERIFIES its claim against real state (`known_rules`,
    `queue`, `all_entry_ids`) rather than trusting the string -- this is
    the anti-lie half of the gate. `disposition` is already the parsed
    `frob.registry.Disposition` (T-0407) -- this function is pure policy
    over that typed shape, no string matching left here."""
    if disposition.kind is DispositionKind.UNDISPOSITIONED:
        return (
            "REG001",
            f"REG001: {entry_id} has no disposition (missing, 'pending', "
            f"or an unverifiable bare 'addressed') -- every registry entry "
            f"must carry handled_by:<rule-id>, deferred:<ticket-id>, "
            f"duplicate_of:<id>, or out_of_scope:<reason>",
        )
    if disposition.kind is DispositionKind.HANDLED_BY:
        assert disposition.target is not None
        return _classify_handled_by(entry_id, disposition.target, known_rules)
    if disposition.kind is DispositionKind.DEFERRED:
        assert disposition.target is not None
        return _classify_deferred(entry_id, disposition.target, queue)
    if disposition.kind is DispositionKind.DUPLICATE_OF:
        assert disposition.target is not None
        return _classify_duplicate(entry_id, disposition.target, all_entry_ids)
    assert disposition.kind is DispositionKind.OUT_OF_SCOPE
    assert disposition.target is not None
    return _classify_out_of_scope(entry_id, disposition.target)


# frob:enforces CHK-GATE-REG005
def _reg005_total_mismatch(
    rel_path: str, registry_file: RegistryFile, entries_key: str
) -> Violation | None:
    """REG005: a declared `<prefix>total:` that does not match the
    matching entry list's actual length -- the denominator drift check.
    A file/list with no matching total field declared is not checked
    (nothing declared to drift from). Uses `RegistryFile.malformed_count`
    too: a malformed (REG006) item was still a real line in the source
    YAML list, so it counts toward the actual length the declared total
    is compared against, same as `len(data[entries_key])` did pre-T-0407."""
    total_field = (
        "total"
        if entries_key == "entries"
        else (entries_key.removesuffix("_entries") + "_total")
    )
    total = registry_file.declared_totals.get(total_field)
    if total is None:
        return None
    actual = len(registry_file.entry_lists.get(entries_key, ()))
    if total == actual:
        return None
    return Violation(
        rule="REG005",
        severity=Severity.ERROR,
        file=rel_path,
        line=0,
        message=(
            f"REG005: {rel_path} declares {total_field}: {total} but "
            f"{entries_key} has {actual} actual entries -- an entry "
            f"was silently added or dropped without updating the declared "
            f"denominator"
        ),
    )


# frob:enforces CHK-GATE-REG006
def _reg006_malformed(rel_path: str, registry_file: RegistryFile) -> Violation | None:
    """REG006 (T-0407): one or more list items under `rel_path` were not a
    mapping, or had no string `id` -- these were silently dropped pre-
    T-0407 instead of raising, exactly the early-exit hole the ticket
    names ("an entry present in prose but not the registry")."""
    if registry_file.malformed_count == 0:
        return None
    return Violation(
        rule="REG006",
        severity=Severity.ERROR,
        file=rel_path,
        line=0,
        message=(
            f"REG006: {rel_path} has {registry_file.malformed_count} "
            f"structurally malformed entry/entries (not a mapping, or "
            f"missing a string `id`) silently unaccounted for -- every "
            f"list item under entries:/*_entries: must be a real, "
            f"id-bearing entry"
        ),
    )


_SPLIT_ID_RE = re.compile(r"`([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)`")


def _split_ids_from_reconciliation(text: str) -> frozenset[str]:
    """Every registry id RECONCILIATION.md's finding (b) split table names
    (backtick-quoted `SOMETHING-LIKE-THIS` tokens within that section) --
    the id-shaped regex mirrors the registry's own `<DOMAIN>-<...>`
    convention (README.md's Schema section)."""
    marker = "### (b) SPLIT entries"
    start = text.find(marker)
    if start == -1:
        return frozenset()
    next_section = text.find("\n### (c)", start)
    section = text[start : next_section if next_section != -1 else len(text)]
    return frozenset(_SPLIT_ID_RE.findall(section))


# frob:enforces CHK-GATE-REG004
def _reg004_unresolved_splits(
    rel_reconciliation: str,
    split_ids: frozenset[str],
    entries_by_id: dict[str, tuple[str, RegistryEntry]],
) -> list[Violation]:
    """REG004 for every RECONCILIATION.md-documented split id that still
    shows an empty `cross_refs` in its owning registry file -- a live,
    unresolved split (same real-world item under two-plus unlinked ids)."""
    violations = []
    for split_id in sorted(split_ids):
        located = entries_by_id.get(split_id)
        if located is None:
            continue
        rel_path, entry = located
        if entry.cross_refs:
            continue
        violations.append(
            Violation(
                rule="REG004",
                severity=Severity.ERROR,
                file=rel_path,
                line=0,
                message=(
                    f"REG004: {split_id} is documented in "
                    f"{rel_reconciliation} as a split entry (same "
                    f"real-world item under multiple unlinked ids) but "
                    f"still has empty cross_refs -- unresolved split"
                ),
            )
        )
    return violations


# frob:enforces CHK-GATE-REG007
def _reg007_duplicate_ids(
    parsed: dict[str, RegistryFile],
) -> list[Violation]:
    """REG007 (T-0407): the same `id` string defined by two or more
    entries anywhere across the loaded registry -- a real id collision
    (as opposed to `duplicate_of:`, an intentional cross-reference, which
    REG004 already governs). Pre-T-0407 the cross-file id index silently
    kept only the last-seen entry for a collided id; this makes the
    collision itself a loud violation instead of a silent drop."""
    seen: dict[str, list[str]] = {}
    for rel_path, registry_file in parsed.items():
        for entries in registry_file.entry_lists.values():
            for entry in entries:
                seen.setdefault(entry.id, []).append(rel_path)
    violations = []
    for entry_id, locations in sorted(seen.items()):
        if len(locations) < 2:
            continue
        violations.append(
            Violation(
                rule="REG007",
                severity=Severity.ERROR,
                file=locations[0],
                line=0,
                message=(
                    f"REG007: id {entry_id} is defined by {len(locations)} "
                    f"entries across {sorted(set(locations))} -- a real id "
                    f"collision (use duplicate_of: on the redundant entry "
                    f"if it is intentional) silently drops all but one "
                    f"entry from any id-keyed accounting"
                ),
            )
        )
    return violations


def _index_entries_by_id(
    parsed: dict[str, RegistryFile],
) -> tuple[dict[str, tuple[str, RegistryEntry]], frozenset[str]]:
    """`{entry_id: (rel_path, entry)}` and the frozen id set over every
    entry in `parsed` -- the shared cross-reference index REG004's
    duplicate-target and split-resolution checks both need. On a REG007
    id collision, the LAST entry for that id wins the index (matching the
    documented last-write-wins semantics REG007 now makes loud rather
    than leaving it a silent, undetectable behavior)."""
    entries_by_id: dict[str, tuple[str, RegistryEntry]] = {}
    all_ids: set[str] = set()
    for rel_path, registry_file in parsed.items():
        for entries in registry_file.entry_lists.values():
            for entry in entries:
                entries_by_id[entry.id] = (rel_path, entry)
                all_ids.add(entry.id)
    return entries_by_id, frozenset(all_ids)


def _classify_all_entries(
    parsed: dict[str, RegistryFile],
    known_rules: frozenset[str],
    all_ids_frozen: frozenset[str],
    queue: TicketQueue,
    cataloged_cwes: frozenset[str] = frozenset(),
) -> list[Violation]:
    """REG001-REG002-REG003-REG004 (disposition) plus REG005/REG006
    (denominator/structural) and REG011 (T-0680, out_of_scope caught_by)
    violations over every entry in `parsed`."""
    violations: list[Violation] = []
    for rel_path, registry_file in parsed.items():
        malformed = _reg006_malformed(rel_path, registry_file)
        if malformed is not None:
            violations.append(malformed)
        for entries_key, entries in registry_file.entry_lists.items():
            mismatch = _reg005_total_mismatch(rel_path, registry_file, entries_key)
            if mismatch is not None:
                violations.append(mismatch)
            for entry in entries:
                outcome = _classify(
                    entry.id, entry.disposition, known_rules, all_ids_frozen, queue
                )
                if outcome is None:
                    continue
                rule, message = outcome
                violations.append(
                    Violation(
                        rule=rule,
                        severity=Severity.ERROR,
                        file=rel_path,
                        line=0,
                        message=message,
                    )
                )
            violations.extend(
                _reg011_out_of_scope_caught_by(
                    rel_path, entries, known_rules, cataloged_cwes
                )
            )
    return violations


def _reg011_out_of_scope_caught_by(
    rel_path: str,
    entries: tuple[RegistryEntry, ...],
    known_rules: frozenset[str],
    cataloged_cwes: frozenset[str],
) -> list[Violation]:
    """REG011 (T-0680) for every `out_of_scope`-dispositioned entry in
    `entries` -- split out of `_classify_all_entries` for ARCH001; fills
    in `file=rel_path` since `_classify_out_of_scope_caught_by` is a pure
    per-entry classifier with no file context of its own."""
    violations: list[Violation] = []
    for entry in entries:
        if entry.disposition.kind is not DispositionKind.OUT_OF_SCOPE:
            continue
        assert entry.disposition.target is not None
        violation = _classify_out_of_scope_caught_by(
            entry.id, entry.disposition.target, known_rules, cataloged_cwes
        )
        if violation is None:
            continue
        violations.append(
            Violation(
                rule=violation.rule,
                severity=violation.severity,
                file=rel_path,
                line=violation.line,
                message=violation.message,
            )
        )
    return violations


def _reconciliation_violations(
    base: Path,
    repo_root: Path,
    entries_by_id: dict[str, tuple[str, RegistryEntry]],
) -> list[Violation]:
    """REG004 for every RECONCILIATION.md-documented split id still
    unresolved in its owning registry file, or `[]` if the file is absent
    or unreadable -- split out of `registry_gate` for ARCH001."""
    reconciliation_path = base / _RECONCILIATION_FILE
    if not reconciliation_path.exists():
        return []
    rel_reconciliation = (
        str(reconciliation_path.relative_to(repo_root))
        if _is_relative(reconciliation_path, repo_root)
        else str(reconciliation_path)
    )
    try:
        text = reconciliation_path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("registry_gate: %s unreadable: %s", reconciliation_path, exc)
        return []
    split_ids = _split_ids_from_reconciliation(text)
    return _reg004_unresolved_splits(rel_reconciliation, split_ids, entries_by_id)


# frob:ticket T-0428
def _enforced_concept_ids(snapshot: GraphSnapshot) -> frozenset[str]:
    """Every concept id named by a `frob:enforces <concept-id>` edge
    anywhere in `snapshot` -- the CODE side of T-0428's two-SSOT
    conformance check (code declares what it enforces; this is the
    derived truth a hand-typed `handled_by:<rule-id>` disposition is
    cross-checked against, never the other way around)."""
    return frozenset(
        edge.target for edge in snapshot.edges if edge.kind == EdgeKind.ENFORCES
    )


# frob:ticket T-0428
# frob:enforces CHK-GATE-REG008
def _reg008_undeclared_enforcement(
    parsed: dict[str, RegistryFile], enforced_ids: frozenset[str]
) -> list[Violation]:
    """REG008 (WARN, advisory): an entry dispositioned
    `handled_by:<rule-id>` (a claim that SOME rule enforces it) with no
    `frob:enforces` edge anywhere in code naming that entry's id -- the
    yaml claims enforcement that the code does not itself declare, a
    code<->corpus conformance drift T-0428 calls out as the two-SSOT
    split's required bidirectional check.

    WARN, not ERROR: this repo's registry carries ~1950 entries built
    before `frob:enforces` existed, essentially all of them undeclared in
    code by this measure -- an honest first-turn-on debt, the same shape
    as INV003/INV004's own initial red state, not something this pass
    can retroactively backfill in one ticket."""
    violations: list[Violation] = []
    for rel_path, registry_file in parsed.items():
        for entries in registry_file.entry_lists.values():
            for entry in entries:
                disposition = entry.disposition
                if disposition.kind is not DispositionKind.HANDLED_BY:
                    continue
                if entry.id in enforced_ids:
                    continue
                violations.append(
                    Violation(
                        rule="REG008",
                        severity=Severity.WARN,
                        file=rel_path,
                        line=0,
                        message=(
                            f"REG008: {rel_path} entry {entry.id!r} is "
                            f"dispositioned handled_by:{disposition.target} "
                            f"but no `frob:enforces {entry.id}` edge exists "
                            f"anywhere in code -- add the directive to the "
                            f"enforcing rule, or re-disposition the entry"
                        ),
                    )
                )
    return violations


# frob:ticket T-0428
# frob:enforces CHK-GATE-REG009
def _reg009_phantom_enforcement(
    snapshot: GraphSnapshot, all_ids: frozenset[str]
) -> list[Violation]:
    """REG009 (WARN, advisory): a `frob:enforces <concept-id>` edge in
    code naming a concept id that does not resolve to any loaded
    registry entry -- a typo'd id, or a rule enforcing something the
    universe corpus never enumerated. The other direction of T-0428's
    bidirectional conformance check (REG008 is corpus-claims-but-code-
    silent; REG009 is code-claims-but-corpus-does-not-know-it)."""
    violations: list[Violation] = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.ENFORCES:
            continue
        if edge.target in all_ids:
            continue
        origin_file, _, _ = edge.origin.rpartition(":")
        violations.append(
            Violation(
                rule="REG009",
                severity=Severity.WARN,
                file=origin_file or edge.origin,
                line=0,
                message=(
                    f"REG009: {edge.src} declares `frob:enforces "
                    f"{edge.target}` but {edge.target!r} does not resolve "
                    f"to any loaded docs/design/registry/*.yaml entry -- "
                    f"fix the id, or append the concept to the universe "
                    f"corpus if it genuinely exists and was never "
                    f"enumerated"
                ),
            )
        )
    return violations


# frob:ticket T-0560
# frob:enforces CHK-GATE-REG010
def _reg010_gate_rule_staleness(
    base: Path, repo_root: Path, known_rules: frozenset[str]
) -> list[Violation]:
    """REG010 (WARN, advisory): a LIVE rule in `known_rules` with no
    `CHK-GATE-<rule>` entry anywhere in `check-coverage.yaml` -- the
    scheduled-audit half of T-0424/T-0560: a newly added gate rule that
    nobody remembered to register in the reflexive registry is caught by
    the very next `frob check`, not left to a human noticing (or a
    scheduler that might not run) at some later point.

    WARN, not ERROR: this repo's own `check-coverage.yaml` already has a
    handful of pre-existing gaps of exactly this shape (confirmed via
    `tests/test_check_coverage_registry.py`'s own reflexive count check,
    which predates this gate and was already red on `main`) -- promoting
    straight to ERROR would immediately fail the build on old debt this
    ticket's job is to catch FUTURE drift on, not retroactively clear."""
    check_coverage = base / _CHECK_COVERAGE_FILE
    if not check_coverage.is_file():
        return []
    missing = missing_gate_rule_ids(check_coverage, known_rules)
    if not missing:
        return []
    rel_path = _rel_registry_path(check_coverage, repo_root)
    return [
        Violation(
            rule="REG010",
            severity=Severity.WARN,
            file=rel_path,
            line=0,
            message=(
                f"REG010: {len(missing)} live gate rule(s) have no "
                f"CHK-GATE-<rule> entry in {rel_path} "
                f"({', '.join(sorted(missing)[:8])}"
                f"{'...' if len(missing) > 8 else ''}) -- run "
                f"`frob registry audit --sync-gate-rules` to file them"
            ),
        )
    ]


def _rel_registry_path(path: Path, repo_root: Path) -> str:
    """`path` shortened relative to `repo_root` for report-friendly output,
    or its absolute form if it does not actually sit under `repo_root`."""
    if _is_relative(path, repo_root):
        return str(path.relative_to(repo_root))
    return str(path)


# frob:ticket T-0894
# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#reg012-adopted-then-deleted-registry-t-0894  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestPathEverTracked.test_never_committed_path_is_false  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestPathEverTracked.test_deleted_after_commit_is_true  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestPathEverTracked.test_git_failure_is_false  # noqa: E501
def path_ever_tracked(repo_root: Path, rel_path: str) -> bool:
    """True if `rel_path` (relative to `repo_root`) appears anywhere in
    HEAD's own commit history -- added, and possibly later deleted --
    even though it is absent from the working tree right now.

    T-0894: `registry_gate`/`compliance_gate`/`decisions_gate` all shared
    one "missing backing file/dir means no claim, not a violation"
    posture with no way to tell "this repo never adopted the registry"
    (genuinely silent) from "this repo adopted the registry and someone
    deleted it" (a real, structurally invisible vacuousness hole --
    deletion cleared every violation the registry existing would have
    produced, and nothing else in the gate catalog fired on the deletion
    itself). This is the shared signal that tells the two apart: `git log
    -1 -- <rel_path>` against HEAD returns a commit only if the path was
    ever committed on this branch's history, regardless of its current
    working-tree state. A `git` spawn failure (not a repo, no git binary,
    timeout) degrades to `False` -- the caller's existing "never adopted"
    posture -- rather than escalating a plumbing failure into a false
    compliance/registry violation."""
    from frob.gitio import run_argv

    spawned = run_argv(
        ("git", "-C", str(repo_root), "log", "-1", "--pretty=%H", "--", rel_path)
    )
    if spawned.is_err:
        _log.warning(
            "path_ever_tracked: git spawn failed for %s: %s",
            rel_path,
            spawned.danger_err,
        )
        return False
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning(
            "path_ever_tracked: git log failed (rc=%d) for %s: %s",
            result.returncode,
            rel_path,
            result.stderr,
        )
        return False
    return bool(result.stdout.strip())


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#registry-exhaustiveness-drift-lock-t-0343  # noqa: E501
# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#reg011-out-of-scope-caught_by-t-0680  # noqa: E501
# frob:doc docs/design/registry/RECONCILIATION.md#reg008reg009-t-0428
# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#reg010-gate-rule-staleness-t-0560  # noqa: E501
# frob:ticket T-0343
# frob:ticket T-0407
# REG001-007 fire at Severity.ERROR: every registry entry must carry an
# honest disposition (handled_by/deferred/duplicate_of/out_of_scope), and
# the active-falsehood rules (REG002 dangling handled_by, REG003 deferred-to-
# closed ticket) are hard errors. Promoted from the interim WARN state once
# the backlog was fully drained to zero (T-0426, 2026-07-20). REG006/REG007
# added by T-0407 to close the malformed-entry and duplicate-id early-exit
# holes the pre-unification gate silently allowed.
# frob:tests tests/test_registry_exhaustiveness.py::TestDisposition.test_undispositioned_entry_fails  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestDisposition.test_dangling_handled_by_fails  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestDisposition.test_deferred_to_closed_ticket_fails  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestDisposition.test_fully_dispositioned_fixture_passes  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestMalformedEntry.test_malformed_entry_fails  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestDuplicateId.test_duplicate_id_across_files_fails  # noqa: E501
# T-0424: check-coverage.yaml added to REGISTRY_FILES below.
# frob:tests tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile.test_is_in_registry_files  # noqa: E501
# frob:tests tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage.test_no_check_coverage_violations  # noqa: E501
# T-0428: REG008/REG009 derived-coverage two-SSOT conformance.
# frob:tests tests/test_registry_exhaustiveness.py::TestEnforcesConformance.test_handled_by_with_no_frob_enforces_edge_warns  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestEnforcesConformance.test_handled_by_with_frob_enforces_edge_is_silent  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestEnforcesConformance.test_no_snapshot_skips_reg008_reg009  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestEnforcesConformance.test_phantom_enforces_edge_warns  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestEnforcesConformance.test_matching_enforces_edge_no_reg009  # noqa: E501
# T-0680: REG011 routes out_of_scope reasons through T-0382 caught_by verification.
# frob:tests tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy.test_reason_naming_no_control_warns  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy.test_reason_naming_unresolved_rule_warns  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy.test_reason_naming_resolved_rule_is_silent  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy.test_substantive_reasoned_none_is_silent  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy.test_bare_none_is_not_substantive  # noqa: E501
# T-0894: REG012 -- a repo that ever committed docs/design/registry/ and
# then deleted it is loud, not silently downgraded to "never adopted".
# frob:tests tests/test_registry_exhaustiveness.py::TestDeletedRegistry.test_never_adopted_registry_dir_is_silent  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestDeletedRegistry.test_deleted_after_adoption_fires_reg012  # noqa: E501
# frob:enforces CHK-GATE-REG012
def registry_gate(
    repo_root: Path,
    queue: TicketQueue,
    known_rules: frozenset[str],
    registry_dir: Path | None = None,
    snapshot: GraphSnapshot | None = None,
) -> tuple[Violation, ...]:
    """REG001 (undispositioned) / REG002 (dangling handled_by) / REG003
    (deferred to closed/missing ticket) / REG004 (dangling duplicate_of,
    or a RECONCILIATION.md-documented split still unlinked) / REG005
    (declared total drift) / REG006 (structurally malformed entry
    silently unaccounted for) / REG007 (the same id defined twice, a real
    collision) / REG008 (handled_by claim with no `frob:enforces` edge
    anywhere in code, T-0428) / REG009 (a `frob:enforces` edge naming a
    concept id absent from the registry, T-0428) / REG011 (an
    out_of_scope reason naming no resolvable catching control and no
    substantive reasoned-none, T-0680) / REG012 (the registry directory
    itself was committed on this branch's history and has since been
    deleted from the working tree -- "never adopted" and "adopted then
    deleted" are structurally distinguishable now, T-0894) over every
    `docs/design/registry/*.yaml` manifest under `registry_dir` (defaults
    to `repo_root / "docs/design/registry"`).

    REG001-REG007 are ERROR severity -- the fail-closed anti-lie core: a
    catalogued-but-undispositioned entry, or a dispositioned entry whose
    claim does not actually verify, fails `frob check`'s exit code, it
    does not merely warn. REG008-REG011 are WARN/advisory (each an honest
    first-turn-on debt over this repo's own large pre-existing corpus, per
    their own docstrings -- not weaker checks, just not yet promotable to
    ERROR without immediately redding the build on old debt). `known_rules`
    is the caller's live gate-rule-id + policy-rule-id union, so
    `handled_by` (and REG011's caught_by resolution) are checked against
    what this BUILD actually enforces, never a hardcoded list.

    T-0407: loading and entry/disposition parsing now go through the
    single `frob.registry.load_registry_dir` loader instead of a
    duplicated inline YAML+regex parser -- this module is purely the
    policy layer over that typed model.

    T-0428: `snapshot` is OPTIONAL and keyword-only, defaulting to `None`
    -- REG008/REG009 (the two-SSOT code<->corpus conformance check) only
    run when a `GraphSnapshot` is supplied; without one, this function
    makes no claim about code-side enforcement declarations rather than
    failing every `handled_by` entry closed by assumption (a caller that
    has not wired the graph yet gets REG001-007 unchanged, not a new
    false-positive family)."""
    base = (
        registry_dir
        if registry_dir is not None
        else (repo_root / "docs/design/registry")
    )
    if not base.is_dir():
        rel_base = _rel_registry_path(base, repo_root)
        if path_ever_tracked(repo_root, rel_base):
            _log.warning(
                "registry_gate: %s existed in HEAD's history but is now "
                "deleted from the working tree (REG012)",
                base,
            )
            return (
                Violation(
                    rule="REG012",
                    severity=Severity.ERROR,
                    file=rel_base,
                    line=0,
                    message=(
                        f"REG012: {rel_base} was previously committed on "
                        "this branch but has been deleted -- a registry "
                        "this repo has adopted cannot silently disappear "
                        "back into 'never adopted' (T-0894); restore it or "
                        "file a decision record explaining the removal"
                    ),
                ),
            )
        _log.info("registry_gate: %s does not exist, skipping", base)
        return ()

    loaded = load_registry_dir(base, REGISTRY_FILES)
    parsed: dict[str, RegistryFile] = {}
    violations: list[Violation] = []
    for filename, result in loaded.items():
        rel_path = _rel_registry_path(base / filename, repo_root)
        if result.is_err:
            violations.append(
                Violation(
                    rule="REG005",
                    severity=Severity.ERROR,
                    file=rel_path,
                    line=0,
                    message=f"REG005: {rel_path} is missing or not valid YAML "
                    f"({result.danger_err.value})",
                )
            )
            continue
        parsed[rel_path] = result.danger_ok

    from frob.strata._threat import ALL_CATALOG  # lazy: see module note

    entries_by_id, all_ids_frozen = _index_entries_by_id(parsed)
    cataloged_cwes = frozenset(entry.id for entry in ALL_CATALOG)
    violations.extend(
        _classify_all_entries(
            parsed, known_rules, all_ids_frozen, queue, cataloged_cwes
        )
    )
    violations.extend(_reg007_duplicate_ids(parsed))
    violations.extend(_reconciliation_violations(base, repo_root, entries_by_id))
    violations.extend(_reg010_gate_rule_staleness(base, repo_root, known_rules))
    if snapshot is not None:
        enforced_ids = _enforced_concept_ids(snapshot)
        violations.extend(_reg008_undeclared_enforcement(parsed, enforced_ids))
        violations.extend(_reg009_phantom_enforcement(snapshot, all_ids_frozen))
    all_ids = set(all_ids_frozen)

    _log.info(
        "registry_gate: %d registry file(s), %d entries, %d violation(s)",
        len(parsed),
        len(all_ids),
        len(violations),
    )
    return tuple(violations)


def _is_relative(path: Path, root: Path) -> bool:
    """True if `path` sits under `root` -- guards the `relative_to` call
    used only for cosmetic (report-friendly) path shortening."""
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
