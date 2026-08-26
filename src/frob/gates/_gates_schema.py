"""GATESSCHEMA001 (T-2390 epic, child T-2435): an unknown key in
`[gates.ratchet]`, or an unknown RULE ID as a key in `[gates.severity]`,
is silently ignored today -- the "config-file keys are never validated"
defect class T-2390 exists to close, applied to the full `[gates]`
namespace (19 leaves total: 18 in `[gates.severity]`, 1 in
`[gates.ratchet]` -- there is no bare `[gates]` table itself in this
repo's own frob.toml, only these two nested sub-tables).

TWO GENUINELY DIFFERENT VALIDATION SHAPES under one rule, kept in one
child per the ticket's own note that `[gates]`'s full key surface was not
fully surveyed at filing time:

- `[gates.ratchet]` (`frob.gates._ratchet`, `rules = [...]`) is an
  ordinary fixed-key-set table, same shape as every other T-2390 child --
  its only known key is `rules`.
- `[gates.severity]` (`frob.gates._waive._severity_overrides`) is
  structurally different: its KEYS are themselves gate rule ids (e.g.
  `COV001 = "error"`), not a small fixed vocabulary -- a project may
  legitimately override the severity of any registered rule. The
  existing reader already degrades a malformed VALUE gracefully (a
  non-"warn"/"error" value logs a warning and is ignored) -- what it does
  NOT catch is a malformed KEY: a misspelled rule id (e.g. `COV0011`,
  an extra trailing digit on `COV001`) silently sits in the overrides
  dict forever, matching against nothing,
  doing nothing. This rule's job for `[gates.severity]` is validating
  every KEY against the canonical live rule-id registry (`frob.gates.
  _waive._KNOWN_GATE_RULES`), not re-deriving a project-configurable
  known-key set the way every other T-2390 child does -- there is
  nothing to "declare" here beyond the registry itself, since a
  frob.toml-configurable known-key set for "which rule ids exist" would
  be circular.

PORTABILITY (T-2384's doctrine) for `[gates.ratchet]`: no hardcoded key
list beyond the one obvious name -- declared via `[gates_schema]
ratchet_known_keys = "module:symbol"`, resolved through the same `frob.
gates._docblocks_shared.resolve_dotted_symbol` idiom every T-2390 child
uses.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED` mechanism): no `[gates_schema] ratchet_known_keys` declared,
an unresolvable dotted path, or a resolved value that is neither a set
nor a set-returning callable all report `Severity.UNRESOLVED` for the
`[gates.ratchet]` half -- never a silently empty (and therefore falsely
"clean") violation list. `[gates.severity]`'s rule-id-registry check has
no equivalent "undeclared schema" state -- `_KNOWN_GATE_RULES` is always
available (it is this codebase's own gate registry, same component,
imported directly, no cross-component Flow question) -- so it reports
findings or a clean pass, never UNRESOLVED.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, cast

from frob.gates._docblocks_shared import resolve_dotted_symbol
from frob.gates._models import Severity, Violation
from frob.gates._waive import _KNOWN_GATE_RULES
from frob.logging import get_logger

_log = get_logger(__name__)

#: This repo's own declared known-key set for `[gates.ratchet]` --
#: referenced by `[gates_schema] ratchet_known_keys` in frob.toml, the
#: same module:symbol idiom every T-2390 child uses.
# frob:doc docs/modules/gates.md#gatesschema001-t-2390-epic-child-t-2435
# frob:ticket T-2435
GATES_RATCHET_KNOWN_KEYS: frozenset[str] = frozenset({"rules"})


# frob:ticket T-2435
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _unresolved(message: str) -> Violation:
    """One GATESSCHEMA001 `Severity.UNRESOLVED` finding -- this check
    could not determine an answer, never rendered as a clean zero."""
    return Violation(
        rule="GATESSCHEMA001",
        severity=Severity.UNRESOLVED,
        file="frob.toml",
        line=0,
        message=f"GATESSCHEMA001: {message}",
    )


# frob:ticket T-2435
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _unknown_ratchet_key_violation(key: str) -> Violation:
    """One GATESSCHEMA001 `Severity.ERROR` finding: `[gates.ratchet]`
    carries an undeclared key `key`."""
    return Violation(
        rule="GATESSCHEMA001",
        severity=Severity.ERROR,
        file="frob.toml",
        line=0,
        message=(
            f"GATESSCHEMA001: [gates.ratchet] has an undeclared key "
            f"{key!r} -- not in this project's declared "
            f"[gates_schema] ratchet_known_keys set, so it is silently "
            f"ignored by frob.gates._ratchet's own raw-table read; fix "
            f"the typo, remove the stray key, or extend the declared "
            f"schema if this key is genuinely meant to be supported"
        ),
    )


# frob:ticket T-2435
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _unknown_severity_rule_violation(rule_id: str) -> Violation:
    """One GATESSCHEMA001 `Severity.ERROR` finding: `[gates.severity]`
    carries a key `rule_id` that is not a registered gate rule."""
    return Violation(
        rule="GATESSCHEMA001",
        severity=Severity.ERROR,
        file="frob.toml",
        line=0,
        message=(
            f"GATESSCHEMA001: [gates.severity] {rule_id} = ... names a "
            f"rule id not in frob.gates._waive._KNOWN_GATE_RULES -- this "
            f"override silently matches nothing and does nothing (frob."
            f"gates._waive._severity_overrides only ever consults "
            f"overrides whose key equals a real Violation.rule at "
            f"apply time); fix the typo, remove the stray override, or "
            f"register the rule id if it is genuinely new"
        ),
    )


# frob:ticket T-2435
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _resolve_ratchet_known_keys(
    root: Path,
) -> tuple[frozenset[str] | None, Violation | None]:
    """Resolve `[gates_schema] ratchet_known_keys` to a real
    `frozenset[str]`, or return the `Violation` explaining why not."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None, _unresolved(
            "no frob.toml at all -- GATESSCHEMA001 cannot determine "
            "this project's [gates.ratchet] surface"
        )
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return None, _unresolved(f"frob.toml unreadable: {exc}")

    schema_dotted = doc.get("gates_schema", {}).get("ratchet_known_keys")
    if not isinstance(schema_dotted, str) or not schema_dotted:
        return None, _unresolved(
            "no [gates_schema] ratchet_known_keys declared in frob.toml "
            "-- GATESSCHEMA001 cannot determine this project's "
            "[gates.ratchet] known-key set at all; this is an "
            "UNMEASURED project, not a clean pass. Declare "
            'ratchet_known_keys = "module:symbol" (a frozenset[str], or '
            "a zero-arg callable returning one) to enable this half of "
            "the check"
        )

    resolved = resolve_dotted_symbol(schema_dotted, log_prefix="gatesschema001")
    if resolved is None:
        return None, _unresolved(
            f"could not resolve ratchet_known_keys={schema_dotted!r} -- "
            f"see the gatesschema001 warning log line for the "
            f"underlying import/attribute error; GATESSCHEMA001 is "
            f"UNMEASURED, not clean"
        )

    known = cast(Any, resolved)() if callable(resolved) else resolved
    if not isinstance(known, frozenset | set):
        return None, _unresolved(
            f"ratchet_known_keys={schema_dotted!r} resolved to a "
            f"{type(known).__name__}, not a frozenset[str]/set[str] "
            f"(directly, or via a zero-arg callable) -- GATESSCHEMA001 "
            f"is UNMEASURED, not clean"
        )
    return cast("frozenset[str]", frozenset(known)), None


# frob:ticket T-2435
# frob:waive EXHAUST003 reason="the try/except here is narrowly scoped to \
# tomllib.load's own documented failure modes (OSError, tomllib.TOMLDecodeError), \
# identical in shape to _resolve_ratchet_known_keys's own tomllib.load call a few \
# lines above in this same file (not flagged) -- the resolver's coverage gap is \
# inherent ambiguity in resolving doc.get(...).get(...) chains on an untyped tomllib \
# result, not a real unhandled-exception risk"
def _gates_tables(root: Path) -> tuple[dict, dict] | None:
    """The RAW `[gates.ratchet]` and `[gates.severity]` tables straight
    off `tomllib.load`, as a `(ratchet, severity)` pair. Returns `None`
    if frob.toml is missing/malformed (same fail-open posture the
    resolvers above use)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    gates = doc.get("gates", {})
    if not isinstance(gates, dict):
        return {}, {}
    ratchet = gates.get("ratchet", {})
    severity = gates.get("severity", {})
    return (
        ratchet if isinstance(ratchet, dict) else {},
        severity if isinstance(severity, dict) else {},
    )


# frob:enforces CHK-GATE-GATESSCHEMA001
# frob:doc docs/modules/gates.md#gatesschema001-t-2390-epic-child-t-2435
# frob:tests \
# tests/unit/test_gates_table_schema.py::TestGatesSchemaGate.test_must_now_fire_reports\
# _the_undeclared_ratchet_key kind="unit"
# frob:tests \
# tests/unit/test_gates_table_schema.py::TestGatesSchemaGate.test_must_still_pass_this_\
# repos_own_frob_toml kind="unit"
# frob:ticket T-2435
def gates_schema_gate(root: Path) -> tuple[Violation, ...]:
    """GATESSCHEMA001: `[gates.ratchet]`'s key set checked against the
    declared `[gates_schema] ratchet_known_keys` source (`Severity.
    UNRESOLVED`, never a silent pass, when no schema is declared or it
    fails to resolve), PLUS every `[gates.severity]` key checked against
    the live `frob.gates._waive._KNOWN_GATE_RULES` registry (always
    available, no UNRESOLVED state -- see this module's docstring for
    why). See the module docstring for the full two-shape rationale."""
    ratchet_known, ratchet_violation = _resolve_ratchet_known_keys(root)

    tables = _gates_tables(root)
    if tables is None:
        if ratchet_violation is not None:
            return (ratchet_violation,)
        return (
            _unresolved(
                "frob.toml unreadable while re-reading raw "
                "[gates.ratchet]/[gates.severity] tables after "
                "ratchet_known_keys resolved successfully -- "
                "GATESSCHEMA001 is UNMEASURED"
            ),
        )
    ratchet_table, severity_table = tables

    violations: list[Violation] = []
    if ratchet_violation is not None:
        violations.append(ratchet_violation)
    else:
        assert ratchet_known is not None  # noqa: S101 -- invariant: _resolve_ratchet_known_keys returns exactly one of (known, violation) as non-None
        violations.extend(
            _unknown_ratchet_key_violation(key)
            for key in ratchet_table
            if key not in ratchet_known
        )

    violations.extend(
        _unknown_severity_rule_violation(rule_id)
        for rule_id in severity_table
        if rule_id not in _KNOWN_GATE_RULES
    )
    return tuple(violations)
