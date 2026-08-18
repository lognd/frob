"""DUPSCHEMA001/GRAPHSCHEMA001 (T-2390 epic, child T-2437): unknown keys
in the `[dup]` and `[graph]` tables are silently ignored today -- the
"config-file keys are never validated" defect class T-2390 exists to
close, applied to both tables in ONE child (unlike this epic's other
children, one table each) because each currently carries only 1 leaf
value in this repo's own frob.toml -- two genuinely disjoint readers,
each too small on its own to justify a separate ticket. The two schema
declarations and their checks are kept clearly separated below (two
distinct rules, two distinct sections) so a future split-out is
mechanical if either table grows.

`[dup]` (`frob.gates._dup._dup_config`, 4 known keys: `enforce`,
`threshold`, `region_kernel`, `native_rungs`) and `[graph]`
(`frob.excludes`, 1 known key: `exclude`) each read their own known
names via `.get(...)` -- a stray/misspelled key in either table is never
read, never validated, never reported.

COMPONENT MEMBERSHIP (the T-2429 lesson, re-applied): `frob.excludes`
lives in a different strata component from `frob.gates` -- so `[graph]`'s
known-key set here is a plain hardcoded literal, never an import of
`frob.excludes`'s own internals. `frob.gates._dup` IS in the same
component as this module, but its known-key set is likewise a plain
literal here (matching every non-pydantic-model T-2390 child) rather
than importing `_dup_config`'s own tuple-unpacking logic, which has no
single "the known keys" symbol to point at.

PORTABILITY (T-2384's doctrine): each table's known-key set is declared
via its own `module:symbol` dotted path (`[dup_schema] known_keys` /
`[graph_schema] known_keys`), resolved through the same `frob.gates.
_docblocks_shared.resolve_dotted_symbol` idiom every T-2390 child uses.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED` mechanism, same posture as every other T-2390 child): for
EACH table independently, no known_keys declared, an unresolvable dotted
path, or a resolved value that is neither a set nor a set-returning
callable reports `Severity.UNRESOLVED` for that table's half -- never a
silently empty (and therefore falsely "clean") violation list.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, cast

from frob.gates._docblocks_shared import resolve_dotted_symbol
from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

#: This repo's own declared known-key set for `[dup]` -- referenced by
#: `[dup_schema] known_keys` in frob.toml.
# frob:doc docs/modules/gates.md#dupschema001graphschema001-t-2390-epic-child-t-2437
# frob:ticket T-2437
DUP_KNOWN_KEYS: frozenset[str] = frozenset(
    {"enforce", "threshold", "region_kernel", "native_rungs"}
)

#: This repo's own declared known-key set for `[graph]` -- referenced by
#: `[graph_schema] known_keys` in frob.toml.
# frob:doc docs/modules/gates.md#dupschema001graphschema001-t-2390-epic-child-t-2437
# frob:ticket T-2437
GRAPH_KNOWN_KEYS: frozenset[str] = frozenset({"exclude"})


# ---------------------------------------------------------------------------
# shared plumbing (table-agnostic)
# ---------------------------------------------------------------------------


# frob:ticket T-2437
def _unresolved(rule: str, message: str) -> Violation:
    """One `Severity.UNRESOLVED` finding for `rule` -- this check could
    not determine an answer, never rendered as a clean zero."""
    return Violation(
        rule=rule,
        severity=Severity.UNRESOLVED,
        file="frob.toml",
        line=0,
        message=f"{rule}: {message}",
    )


# frob:ticket T-2437
def _resolve_table_known_keys(
    root: Path, schema_table: str, schema_key: str, rule: str
) -> tuple[frozenset[str] | None, Violation | None]:
    """Resolve `[<schema_table>] <schema_key>` to a real `frozenset[str]`,
    or return the `Violation` (tagged `rule`) explaining why not -- the
    one resolver both `[dup]` and `[graph]` share, parameterized by which
    declaration table/rule each is checking."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None, _unresolved(
            rule, "no frob.toml at all -- cannot determine this project's surface"
        )
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return None, _unresolved(rule, f"frob.toml unreadable: {exc}")

    schema_dotted = doc.get(schema_table, {}).get(schema_key)
    if not isinstance(schema_dotted, str) or not schema_dotted:
        return None, _unresolved(
            rule,
            f"no [{schema_table}] {schema_key} declared in frob.toml -- "
            f"cannot determine this project's known-key set at all; this "
            f"is an UNMEASURED project, not a clean pass. Declare "
            f'{schema_key} = "module:symbol" (a frozenset[str], or a '
            f"zero-arg callable returning one) to enable this check",
        )

    log_prefix = rule.lower()
    resolved = resolve_dotted_symbol(schema_dotted, log_prefix=log_prefix)
    if resolved is None:
        return None, _unresolved(
            rule,
            f"could not resolve {schema_key}={schema_dotted!r} -- see "
            f"the {log_prefix} warning log line for the underlying "
            f"import/attribute error; UNMEASURED, not clean",
        )

    known = cast(Any, resolved)() if callable(resolved) else resolved
    if not isinstance(known, frozenset | set):
        return None, _unresolved(
            rule,
            f"{schema_key}={schema_dotted!r} resolved to a "
            f"{type(known).__name__}, not a frozenset[str]/set[str] "
            f"(directly, or via a zero-arg callable) -- UNMEASURED, "
            f"not clean",
        )
    return cast("frozenset[str]", frozenset(known)), None


# frob:ticket T-2437
# frob:waive EXHAUST003 reason="the try/except here is narrowly scoped to \
# tomllib.load's own documented failure modes (OSError, tomllib.TOMLDecodeError), \
# identical in shape to _resolve_table_known_keys's own tomllib.load call above in \
# this same file (not flagged) -- the resolver's coverage gap is inherent ambiguity in \
# resolving doc.get(...).get(...) chains on an untyped tomllib result, not a real \
# unhandled-exception risk"
def _raw_table(root: Path, table_name: str) -> dict | None:
    """The RAW `[<table_name>]` table straight off `tomllib.load`.
    Returns `None` if frob.toml is missing/malformed, or the table is
    absent (same fail-open posture `_resolve_table_known_keys` uses)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    table = doc.get(table_name)
    if not isinstance(table, dict):
        return None
    return table


# frob:ticket T-2437
def _unknown_key_violation(rule: str, table_name: str, reader: str, key: str) -> Violation:
    """One `Severity.ERROR` finding for `rule`: `[<table_name>]` carries
    an undeclared key `key`, silently ignored by `reader`."""
    return Violation(
        rule=rule,
        severity=Severity.ERROR,
        file="frob.toml",
        line=0,
        message=(
            f"{rule}: [{table_name}] has an undeclared key {key!r} -- "
            f"not in this project's declared known-key set, so it is "
            f"silently ignored by {reader}; fix the typo, remove the "
            f"stray key, or extend the declared schema if this key is "
            f"genuinely meant to be supported"
        ),
    )


# ---------------------------------------------------------------------------
# DUPSCHEMA001: [dup]
# ---------------------------------------------------------------------------


# frob:enforces CHK-GATE-DUPSCHEMA001
# frob:doc docs/modules/gates.md#dupschema001graphschema001-t-2390-epic-child-t-2437
# frob:tests \
# tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate.test_dup_must_now_f\
# ire_reports_the_undeclared_key kind="unit"
# frob:tests \
# tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate.test_dup_must_still\
# _pass_this_repos_own_frob_toml kind="unit"
# frob:ticket T-2437
def dup_schema_gate(root: Path) -> tuple[Violation, ...]:
    """DUPSCHEMA001: the `[dup]` table's key set, checked against the
    declared `[dup_schema] known_keys` source. `Severity.UNRESOLVED`
    when no schema is declared or it fails to resolve; otherwise one
    ERROR per undeclared key found (no `[dup]` table at all is not
    itself an error -- the table is optional)."""
    known, violation = _resolve_table_known_keys(
        root, "dup_schema", "known_keys", "DUPSCHEMA001"
    )
    if violation is not None:
        return (violation,)
    assert known is not None  # noqa: S101 -- invariant: _resolve_table_known_keys returns exactly one of (known, violation) as non-None

    table = _raw_table(root, "dup")
    if table is None:
        return ()
    return tuple(
        _unknown_key_violation(
            "DUPSCHEMA001", "dup", "frob.gates._dup._dup_config", key
        )
        for key in table
        if key not in known
    )


# ---------------------------------------------------------------------------
# GRAPHSCHEMA001: [graph]
# ---------------------------------------------------------------------------


# frob:enforces CHK-GATE-GRAPHSCHEMA001
# frob:doc docs/modules/gates.md#dupschema001graphschema001-t-2390-epic-child-t-2437
# frob:tests \
# tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate.test_graph_must_now\
# _fire_reports_the_undeclared_key kind="unit"
# frob:tests \
# tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate.test_graph_must_sti\
# ll_pass_this_repos_own_frob_toml kind="unit"
# frob:ticket T-2437
def graph_schema_gate(root: Path) -> tuple[Violation, ...]:
    """GRAPHSCHEMA001: the `[graph]` table's key set, checked against
    the declared `[graph_schema] known_keys` source. `Severity.
    UNRESOLVED` when no schema is declared or it fails to resolve;
    otherwise one ERROR per undeclared key found (no `[graph]` table at
    all is not itself an error -- the table is optional)."""
    known, violation = _resolve_table_known_keys(
        root, "graph_schema", "known_keys", "GRAPHSCHEMA001"
    )
    if violation is not None:
        return (violation,)
    assert known is not None  # noqa: S101 -- invariant: _resolve_table_known_keys returns exactly one of (known, violation) as non-None

    table = _raw_table(root, "graph")
    if table is None:
        return ()
    return tuple(
        _unknown_key_violation("GRAPHSCHEMA001", "graph", "frob.excludes", key)
        for key in table
        if key not in known
    )
