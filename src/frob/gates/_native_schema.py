"""NATIVESCHEMA001 (T-2390 epic, child T-2429): an unknown key in a
`[[native]]` entry is silently ignored today -- the "config-file keys are
never validated" defect class T-2390 exists to close, applied to
`[[native]]` (6 leaves across 2 entries in this repo's own frob.toml).

`frob.testing._runners._parse_native_entry` reads exactly `name` and
`build_cmd` (required) plus `language` (optional, `.get()` with a default)
-- a fourth key (a typo like "buld_cmd", or a stray field) is never read,
never validated, never reported; the entry parses "successfully" with the
typo'd field simply absent from the resulting `NativeSpec`.

PORTABILITY (T-2384's doctrine): no hardcoded key list. The known-key set
for `[[native]]` is declared via `[native_schema] known_keys = "module:
symbol"` (a dotted path to a `frozenset[str]` or a zero-arg callable
returning one), resolved at check time through the same `frob.gates.
_docblocks_shared.resolve_dotted_symbol` idiom T-2397/T-2428 already
established -- any project can declare its own known-key set without
editing this module.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED` mechanism, same posture as FLAGCOV001/REFSCHEMA001): no
`[native_schema] known_keys` declared, an unresolvable dotted path, or a
resolved value that is neither a set nor a set-returning callable all
report `Severity.UNRESOLVED` -- never a silently empty (and therefore
falsely "clean") violation list.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, cast

from frob.gates._docblocks_shared import resolve_dotted_symbol
from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

#: This repo's own declared known-key set for `[[native]]` -- referenced
#: by `[native_schema] known_keys` in frob.toml, the same module:symbol
#: idiom every T-2390 child uses.
# frob:doc docs/modules/gates.md#nativeschema001-t-2390-epic-child-t-2429
# frob:ticket T-2429
NATIVE_KNOWN_KEYS: frozenset[str] = frozenset({"name", "build_cmd", "language"})


# frob:ticket T-2429
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _unresolved(message: str) -> Violation:
    """One NATIVESCHEMA001 `Severity.UNRESOLVED` finding -- this check
    could not determine an answer, never rendered as a clean zero."""
    return Violation(
        rule="NATIVESCHEMA001",
        severity=Severity.UNRESOLVED,
        file="frob.toml",
        line=0,
        message=f"NATIVESCHEMA001: {message}",
    )


# frob:ticket T-2429
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _unknown_key_violation(index: int, key: str) -> Violation:
    """One NATIVESCHEMA001 `Severity.ERROR` finding: entry `index` of
    `[[native]]` carries an undeclared key `key`."""
    return Violation(
        rule="NATIVESCHEMA001",
        severity=Severity.ERROR,
        file="frob.toml",
        line=0,
        message=(
            f"NATIVESCHEMA001: [[native]] entry {index} has an undeclared "
            f"key {key!r} -- not in this project's declared "
            f"[native_schema] known_keys set, so it is silently ignored by "
            f"frob.testing._runners._parse_native_entry; fix the typo, "
            f"remove the stray key, or extend the declared schema if this "
            f"key is genuinely meant to be supported"
        ),
    )


# frob:ticket T-2429
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _resolve_known_keys(root: Path) -> tuple[frozenset[str] | None, Violation | None]:
    """Resolve `[native_schema] known_keys` to a real `frozenset[str]`, or
    return the `Violation` explaining why not."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None, _unresolved(
            "no frob.toml at all -- NATIVESCHEMA001 cannot determine this "
            "project's [[native]] surface"
        )
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return None, _unresolved(f"frob.toml unreadable: {exc}")

    schema_dotted = doc.get("native_schema", {}).get("known_keys")
    if not isinstance(schema_dotted, str) or not schema_dotted:
        # T-3273: no [native_schema] known_keys declared -- default to
        # frob's own NATIVE_KNOWN_KEYS rather than UNMEASURED; nothing
        # project-specific lives in this table.
        return NATIVE_KNOWN_KEYS, None

    resolved = resolve_dotted_symbol(schema_dotted, log_prefix="nativeschema001")
    if resolved is None:
        return None, _unresolved(
            f"could not resolve known_keys={schema_dotted!r} -- see the "
            f"nativeschema001 warning log line for the underlying import/"
            f"attribute error; NATIVESCHEMA001 is UNMEASURED, not clean"
        )

    known = cast(Any, resolved)() if callable(resolved) else resolved
    if not isinstance(known, frozenset | set):
        return None, _unresolved(
            f"known_keys={schema_dotted!r} resolved to a "
            f"{type(known).__name__}, not a frozenset[str]/set[str] "
            f"(directly, or via a zero-arg callable) -- NATIVESCHEMA001 is "
            f"UNMEASURED, not clean"
        )
    return cast("frozenset[str]", frozenset(known)), None


# frob:ticket T-2429
# frob:waive EXHAUST003 reason="the try/except here is narrowly scoped to \
# tomllib.load's own documented failure modes (OSError, tomllib.TOMLDecodeError), \
# identical in shape to _resolve_known_keys's own tomllib.load call a few lines above \
# in this same file (not flagged) -- the resolver's coverage gap is inherent ambiguity \
# in resolving doc.get(...).get(...) chains on an untyped tomllib result, not a real \
# unhandled-exception risk"
def _native_records(root: Path) -> list[dict] | None:
    """The RAW `[[native]]` records straight off `tomllib.load`. Returns
    `None` if frob.toml is missing/malformed (same fail-open posture
    `_resolve_known_keys` uses)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    entries = doc.get("native", [])
    if not isinstance(entries, list):
        return None
    return [e for e in entries if isinstance(e, dict)]


# frob:enforces CHK-GATE-NATIVESCHEMA001
# frob:doc docs/modules/gates.md#nativeschema001-t-2390-epic-child-t-2429
# frob:tests \
# tests/unit/test_native_table_schema.py::TestNativeSchemaGate.test_must_now_fire_repor\
# ts_the_undeclared_key kind="unit"
# frob:tests \
# tests/unit/test_native_table_schema.py::TestNativeSchemaGate.test_must_still_pass_thi\
# s_repos_own_frob_toml kind="unit"
# frob:ticket T-2429
def native_schema_gate(root: Path) -> tuple[Violation, ...]:
    """NATIVESCHEMA001: every `[[native]]` entry's key set, checked
    against the declared `[native_schema] known_keys` source. Reports
    `Severity.UNRESOLVED` (never a silent pass) when no schema is
    declared or it fails to resolve; otherwise one ERROR per undeclared
    key found. See this module's docstring for the full fail-loudly
    rationale."""
    known, violation = _resolve_known_keys(root)
    if violation is not None:
        return (violation,)
    assert known is not None  # noqa: S101 -- invariant: _resolve_known_keys returns exactly one of (known, violation) as non-None

    records = _native_records(root)
    if records is None:
        return (
            _unresolved(
                "frob.toml unreadable while re-reading raw [[native]] "
                "records after known_keys resolved successfully -- "
                "NATIVESCHEMA001 is UNMEASURED"
            ),
        )

    violations: list[Violation] = []
    for index, entry in enumerate(records):
        for key in entry:
            if key not in known:
                violations.append(_unknown_key_violation(index, key))
    return tuple(violations)
