"""REG001-REG005: the exhaustiveness drift-lock over docs/design/registry/
*.yaml (docs/design/registry/EXHAUSTIVENESS-GATE.md, T-0343).

LINCHPIN / ANTI-LIE MANDATE. Root cause this module closes: the unified
design-knowledge registry (`docs/design/registry/*.yaml`, ~1950 entries
consolidating 11 design corpora) was built, documented as a "unified
machine-readable registry", and then read by ZERO code -- catalogued, not
enforced. No gate was watching that gap. This module is the watcher: a
FAIL-CLOSED gate, wired into `frob check` at ERROR severity as a real
`Violation` family, not a skippable pytest and not advisory-only. A
catalogued-but-undispositioned entry can never pass silently again.

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
  ``out-of-scope(<reason>)`` -- valid if `<reason>` is non-empty. Per the
  ticket's own concession, `caught_by` verification against the T-0382
  Area-2 mechanism is NOT enforced yet (that mechanism does not exist in
  this build) -- `caught_by` is accepted as a free-form string for now;
  this is a named, tracked gap, not a silent one (see the module's
  `_OUT_OF_SCOPE_CAUGHT_BY_GAP` note below).
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

On first turn-on this gate is RED for the ~1950 entries the registry
currently carries (~1006 explicitly `pending`, ~27 bare `addressed`, plus
every CWE entry's inherited `duplicate-of`/`out-of-scope` disposition
which predates and does not yet match this module's `handled_by`/
`deferred`/`out_of_scope` grammar) -- that red is the honest current
state. It is driven green only by the per-registry reconciliation tickets
(T-0384..T-0392), never by suppressing or bulk-waiving this gate.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from frob.gates._models import Severity, Violation
from frob.logging import get_logger
from frob.tickets._models import TicketQueue, TicketState

_log = get_logger(__name__)

__all__ = ["registry_gate", "REGISTRY_FILES"]

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
)

# The RECONCILIATION.md split-finding table this gate cross-checks against
# (finding (b)); a quoted literal here also closes REF001/REF002 for that
# file the same way REGISTRY_FILES does for the manifests themselves.
_RECONCILIATION_FILE = "RECONCILIATION.md"

_HANDLED_BY_RE = re.compile(r"^handled_by:(?P<rule>\S+)$")
_DEFERRED_RE = re.compile(r"^deferred:(?P<ticket>\S+)$")
_DUPLICATE_RE = re.compile(r"^duplicate[_-]of:(?P<target>\S+)$")
_OUT_OF_SCOPE_RE = re.compile(r"^out[_-]of[_-]scope[:(](?P<reason>.+?)[)]?$")

# T-0343 named gap: `out_of_scope` dispositions are meant to route through
# Area-2's VERIFIED `caught_by` mechanism (T-0382); that mechanism does not
# exist in this build yet, so `caught_by` is accepted as a bare string for
# now rather than blocking every out-of-scope disposition on unbuilt
# infrastructure. Tracked here, not silently assumed solved.
_OUT_OF_SCOPE_CAUGHT_BY_GAP = "T-0382 Area-2 caught_by verification not yet built"


def _load_yaml_file(path: Path) -> dict[str, Any] | None:
    """Best-effort parsed YAML mapping, or `None` (malformed/unreadable --
    the caller emits a REG005 violation for the file itself in that case,
    never a silent skip)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("registry_gate: %s unreadable: %s", path, exc)
        return None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        _log.warning("registry_gate: %s malformed YAML: %s", path, exc)
        return None
    if not isinstance(data, dict):
        return None
    return data


def _entry_lists(data: dict[str, Any]) -> list[tuple[str, list[Any]]]:
    """Every `(key, entries)` pair `data` carries under `entries` or any
    key ending in `_entries` -- most registry files use a single
    `entries:` list, but `weaknesses.yaml` splits its CWE-sourced and
    other-framework-sourced entries into `cwe_entries`/
    `other_weakness_framework_entries` (two disjoint denominators, one
    per source doc, each with its own `_total` field) rather than one
    combined list. Generic key matching means a future registry file
    choosing either shape works without a code change here."""
    return [
        (key, value)
        for key, value in data.items()
        if isinstance(value, list) and (key == "entries" or key.endswith("_entries"))
    ]


def _entry_disposition(entry: dict[str, Any]) -> str | None:
    """The raw `disposition` string on `entry`, or `None` if missing/not a
    string at all (both collapse to REG001 undispositioned)."""
    value = entry.get("disposition")
    return value if isinstance(value, str) else None


def _classify(
    entry_id: str,
    disposition: str | None,
    known_rules: frozenset[str],
    all_entry_ids: frozenset[str],
    queue: TicketQueue,
) -> tuple[str, str] | None:
    """`(rule, message)` for the violation `entry_id`'s disposition earns,
    or `None` if it is a fully verified, honest disposition.

    Every branch VERIFIES its claim against real state (`known_rules`,
    `queue`, `all_entry_ids`) rather than trusting the string -- this is
    the anti-lie half of the gate."""
    if disposition is None or disposition.strip() == "" or disposition == "pending":
        return (
            "REG001",
            f"REG001: {entry_id} has no disposition (missing or 'pending') -- "
            f"every registry entry must carry handled_by:<rule-id>, "
            f"deferred:<ticket-id>, duplicate_of:<id>, or "
            f"out_of_scope:<reason>",
        )
    if disposition == "addressed":
        return (
            "REG001",
            f"REG001: {entry_id} has disposition 'addressed' with no "
            f"handled_by:<rule-id> attached -- an unverifiable claim; name "
            f"the real rule/gate that handles it (handled_by:<rule-id>) or "
            f"re-disposition it",
        )
    handled = _HANDLED_BY_RE.match(disposition)
    if handled is not None:
        rule = handled.group("rule")
        if rule not in known_rules:
            return (
                "REG002",
                f"REG002: {entry_id} disposition handled_by:{rule} names a "
                f"rule that does not exist in the live gate/policy rule "
                f"registry -- dangling enforcement reference",
            )
        return None
    deferred = _DEFERRED_RE.match(disposition)
    if deferred is not None:
        ticket_id = deferred.group("ticket")
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
    duplicate = _DUPLICATE_RE.match(disposition)
    if duplicate is not None:
        target = duplicate.group("target")
        if target not in all_entry_ids:
            return (
                "REG004",
                f"REG004: {entry_id} disposition duplicate_of:{target} "
                f"names an id that does not exist anywhere in the "
                f"registry -- dangling duplicate reference",
            )
        return None
    out_of_scope = _OUT_OF_SCOPE_RE.match(disposition)
    if out_of_scope is not None:
        reason = out_of_scope.group("reason").strip()
        if not reason:
            return (
                "REG001",
                f"REG001: {entry_id} disposition out_of_scope has no reason",
            )
        return None
    return (
        "REG001",
        f"REG001: {entry_id} disposition {disposition!r} does not parse "
        f"under the handled_by/deferred/duplicate_of/out_of_scope grammar",
    )


def _reg005_total_field_name(entries_key: str) -> str:
    """The `total:`-shaped field name paired with `entries_key`: bare
    `entries` pairs with `total`; a split key like `cwe_entries` pairs
    with `cwe_total` (matching `weaknesses.yaml`'s own
    `cwe_total`/`other_total` convention)."""
    if entries_key == "entries":
        return "total"
    return entries_key.removesuffix("_entries") + "_total"


def _reg005_total_mismatch(
    rel_path: str, data: dict[str, Any], entries_key: str, entries: list[Any]
) -> Violation | None:
    """REG005: a declared `<prefix>total:` that does not match the
    matching entry list's actual length -- the denominator drift check.
    A file/list with no matching total field declared is not checked
    (nothing declared to drift from)."""
    total_field = _reg005_total_field_name(entries_key)
    total = data.get(total_field)
    if not isinstance(total, int):
        return None
    if total == len(entries):
        return None
    return Violation(
        rule="REG005",
        severity=Severity.ERROR,
        file=rel_path,
        line=0,
        message=(
            f"REG005: {rel_path} declares {total_field}: {total} but "
            f"{entries_key} has {len(entries)} actual entries -- an entry "
            f"was silently added or dropped without updating the declared "
            f"denominator"
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


def _reg004_unresolved_splits(
    rel_reconciliation: str,
    split_ids: frozenset[str],
    entries_by_id: dict[str, tuple[str, dict[str, Any]]],
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
        cross_refs = entry.get("cross_refs")
        if cross_refs:
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


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#registry-exhaustiveness-drift-lock-t-0343  # noqa: E501
# frob:ticket T-0343
# REG001-005 fire at Severity.ERROR: every registry entry must carry an
# honest disposition (handled_by/deferred/duplicate_of/out_of_scope), and
# the active-falsehood rules (REG002 dangling handled_by, REG003 deferred-to-
# closed ticket) are hard errors. Promoted from the interim WARN state once
# the backlog was fully drained to zero (T-0426, 2026-07-20).
# frob:tests tests/test_registry_exhaustiveness.py::TestDisposition.test_undispositioned_entry_fails  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestDisposition.test_dangling_handled_by_fails  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestDisposition.test_deferred_to_closed_ticket_fails  # noqa: E501
# frob:tests tests/test_registry_exhaustiveness.py::TestDisposition.test_fully_dispositioned_fixture_passes  # noqa: E501
def registry_gate(
    repo_root: Path,
    queue: TicketQueue,
    known_rules: frozenset[str],
    registry_dir: Path | None = None,
) -> tuple[Violation, ...]:
    """REG001 (undispositioned) / REG002 (dangling handled_by) / REG003
    (deferred to closed/missing ticket) / REG004 (dangling duplicate_of,
    or a RECONCILIATION.md-documented split still unlinked) / REG005
    (declared total drift) over every `docs/design/registry/*.yaml`
    manifest under `registry_dir` (defaults to `repo_root /
    "docs/design/registry"`).

    All ERROR severity -- this is the fail-closed anti-lie gate: a
    catalogued-but-undispositioned entry, or a dispositioned entry whose
    claim does not actually verify, fails `frob check`'s exit code, it
    does not merely warn. `known_rules` is the caller's live
    gate-rule-id + policy-rule-id union, so `handled_by` is checked
    against what this BUILD actually enforces, never a hardcoded list."""
    base = (
        registry_dir
        if registry_dir is not None
        else (repo_root / "docs/design/registry")
    )
    if not base.is_dir():
        _log.info("registry_gate: %s does not exist, skipping", base)
        return ()

    parsed: dict[str, dict[str, Any]] = {}
    violations: list[Violation] = []
    for filename in REGISTRY_FILES:
        path = base / filename
        if not path.exists():
            continue
        rel_path = (
            str(path.relative_to(repo_root))
            if _is_relative(path, repo_root)
            else str(path)
        )
        data = _load_yaml_file(path)
        if data is None:
            violations.append(
                Violation(
                    rule="REG005",
                    severity=Severity.ERROR,
                    file=rel_path,
                    line=0,
                    message=f"REG005: {rel_path} is missing or not valid YAML",
                )
            )
            continue
        parsed[rel_path] = data

    entries_by_id: dict[str, tuple[str, dict[str, Any]]] = {}
    all_ids: set[str] = set()
    for rel_path, data in parsed.items():
        for _key, entries in _entry_lists(data):
            for entry in entries:
                if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                    entries_by_id[entry["id"]] = (rel_path, entry)
                    all_ids.add(entry["id"])
    all_ids_frozen = frozenset(all_ids)

    for rel_path, data in parsed.items():
        for entries_key, entries in _entry_lists(data):
            violations.extend(
                v
                for v in (_reg005_total_mismatch(rel_path, data, entries_key, entries),)
                if v
            )
            for entry in entries:
                if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
                    continue
                entry_id = entry["id"]
                disposition = _entry_disposition(entry)
                outcome = _classify(
                    entry_id, disposition, known_rules, all_ids_frozen, queue
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

    reconciliation_path = base / _RECONCILIATION_FILE
    if reconciliation_path.exists():
        rel_reconciliation = (
            str(reconciliation_path.relative_to(repo_root))
            if _is_relative(reconciliation_path, repo_root)
            else str(reconciliation_path)
        )
        try:
            text = reconciliation_path.read_text(encoding="utf-8")
        except OSError as exc:
            _log.warning("registry_gate: %s unreadable: %s", reconciliation_path, exc)
        else:
            split_ids = _split_ids_from_reconciliation(text)
            violations.extend(
                _reg004_unresolved_splits(rel_reconciliation, split_ids, entries_by_id)
            )

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
