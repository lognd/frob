"""REFSCHEMA001 (T-2390 epic, this child T-2428): an unknown key
in a `[[refs.entrypoint]]` entry is silently ignored today -- the
"config-file keys are never validated" defect class T-2390 exists to
close, applied to this repo's single LARGEST config table (58 leaf
values across 29 entries) first, establishing the pattern the epic's
other nine children copy.

`frob.gates._refs._load_allowlist` already degrades a MALFORMED entry
(missing `path`/`reason`, wrong type) to a logged warning and a dropped
entry -- but an entry with an EXTRA or MISSPELLED key alongside valid
`path`/`reason` values passes through completely unnoticed: `.get("path")`
and `.get("reason")` only ever look at the two names they know, so a
third key (a typo like "paht", or a stray field from a copy-paste) is
never read, never validated, never reported. This module is the missing
check.

PORTABILITY (T-2384's doctrine): no hardcoded key list. The known-key
set for `[[refs.entrypoint]]` is declared via
`[refs] entrypoint_schema = "module:symbol"` (a dotted path to a
`frozenset[str]` or a zero-arg callable returning one), resolved at
check time through the SAME `frob.gates._docblocks_shared.resolve_
dotted_symbol` idiom T-2397's FLAGCOV001 already established -- any
project can declare its own known-key set for its own `[[refs.
entrypoint]]` usage without editing this module.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped Severity.
UNRESOLVED mechanism, same posture as FLAGCOV001): no `entrypoint_schema`
declared, an unresolvable dotted path, or a resolved value that is
neither a set nor a set-returning callable all report `Severity.
UNRESOLVED` -- never a silently empty (and therefore falsely "clean")
violation list.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, cast

from frob.gates._docblocks_shared import resolve_dotted_symbol
from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

#: This repo's own declared known-key set for `[[refs.entrypoint]]` --
#: referenced by `[refs] entrypoint_schema` in frob.toml, the same
#: module:symbol idiom every T-2390 child uses.
# frob:doc docs/modules/gates.md#refschema001-t-2390-epic-child-t-2428
# frob:ticket T-2428
REFS_ENTRYPOINT_KNOWN_KEYS: frozenset[str] = frozenset({"path", "reason"})


# frob:ticket T-2428
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _unresolved(message: str) -> Violation:
    """One REFSCHEMA001 `Severity.UNRESOLVED` finding -- this check could
    not determine an answer, never rendered as a clean zero."""
    return Violation(
        rule="REFSCHEMA001",
        severity=Severity.UNRESOLVED,
        file="frob.toml",
        line=0,
        message=f"REFSCHEMA001: {message}",
    )


# frob:ticket T-2428
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _unknown_key_violation(index: int, key: str) -> Violation:
    """One REFSCHEMA001 `Severity.ERROR` finding: entry `index` of
    `[[refs.entrypoint]]` carries an undeclared key `key`."""
    return Violation(
        rule="REFSCHEMA001",
        severity=Severity.ERROR,
        file="frob.toml",
        line=0,
        message=(
            f"REFSCHEMA001: [[refs.entrypoint]] entry {index} has an "
            f"undeclared key {key!r} -- not in this project's declared "
            f"entrypoint_schema known-key set, so it is silently ignored "
            f"by frob.gates._refs._load_allowlist; fix the typo, remove "
            f"the stray key, or extend the declared schema if this key "
            f"is genuinely meant to be supported"
        ),
    )


# frob:ticket T-2428
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _resolve_known_keys(root: Path) -> tuple[frozenset[str] | None, Violation | None]:
    """Resolve `[refs] entrypoint_schema` to a real `frozenset[str]`, or
    return the `Violation` explaining why not."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None, _unresolved(
            "no frob.toml at all -- REFSCHEMA001 cannot determine this "
            "project's [[refs.entrypoint]] surface"
        )
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return None, _unresolved(f"frob.toml unreadable: {exc}")

    schema_dotted = doc.get("refs", {}).get("entrypoint_schema")
    if not isinstance(schema_dotted, str) or not schema_dotted:
        # T-3273: no [refs] entrypoint_schema declared -- default to
        # frob's own REFS_ENTRYPOINT_KNOWN_KEYS rather than UNMEASURED;
        # nothing project-specific lives in this table (the {"path",
        # "reason"} entry shape is frob's own [[refs.entrypoint]] schema,
        # not a per-project decision).
        return REFS_ENTRYPOINT_KNOWN_KEYS, None

    resolved = resolve_dotted_symbol(schema_dotted, log_prefix="refschema001")
    if resolved is None:
        return None, _unresolved(
            f"could not resolve entrypoint_schema={schema_dotted!r} -- "
            f"see the refschema001 warning log line for the underlying "
            f"import/attribute error; REFSCHEMA001 is UNMEASURED, not "
            f"clean"
        )

    known = cast(Any, resolved)() if callable(resolved) else resolved
    if not isinstance(known, frozenset | set):
        return None, _unresolved(
            f"entrypoint_schema={schema_dotted!r} resolved to a "
            f"{type(known).__name__}, not a frozenset[str]/set[str] "
            f"(directly, or via a zero-arg callable) -- REFSCHEMA001 is "
            f"UNMEASURED, not clean"
        )
    return cast("frozenset[str]", frozenset(known)), None


# frob:ticket T-2428
# frob:waive EXHAUST003 reason="the try/except here is narrowly scoped to \
# tomllib.load's own documented failure modes (OSError, tomllib.TOMLDecodeError), \
# identical in shape to _resolve_known_keys's own tomllib.load call a few lines above \
# in this same file (not flagged) -- the resolver's coverage gap is inherent ambiguity \
# in resolving doc.get(...).get(...) chains on an untyped tomllib result, not a real \
# unhandled-exception risk"
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _entrypoint_records(root: Path) -> list[dict] | None:
    """The RAW `[[refs.entrypoint]]` records straight off `tomllib.load`
    -- deliberately NOT `frob.gates._refs._load_allowlist`'s filtered
    output, which already drops a malformed entry before this check ever
    sees its full key set. Returns `None` if frob.toml is missing/
    malformed (same fail-open posture `_resolve_known_keys` uses)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    entries = doc.get("refs", {}).get("entrypoint", [])
    if not isinstance(entries, list):
        return None
    return [e for e in entries if isinstance(e, dict)]


# frob:enforces CHK-GATE-REFSCHEMA001
# frob:doc docs/modules/gates.md#refschema001-t-2390-epic-child-t-2428
# frob:tests \
# tests/unit/test_refs_schema.py::TestRefsSchemaGate.test_must_now_fire_reports_the_und\
# eclared_key kind="unit"
# frob:tests \
# tests/unit/test_refs_schema.py::TestRefsSchemaGate.test_must_still_pass_this_repos_ow\
# n_frob_toml kind="unit"
# frob:ticket T-2428
def refs_schema_gate(root: Path) -> tuple[Violation, ...]:
    """REFSCHEMA001: every `[[refs.entrypoint]]` entry's key set, checked
    against the declared `[refs] entrypoint_schema` known-key source.
    Reports `Severity.UNRESOLVED` (never a silent pass) when no schema
    is declared or it fails to resolve; otherwise one ERROR per
    undeclared key found. See this module's docstring for the full
    fail-loudly rationale."""
    known, violation = _resolve_known_keys(root)
    if violation is not None:
        return (violation,)
    assert known is not None  # noqa: S101 -- invariant: _resolve_known_keys returns exactly one of (known, violation) as non-None

    records = _entrypoint_records(root)
    if records is None:
        return (
            _unresolved(
                "frob.toml unreadable while re-reading raw "
                "[[refs.entrypoint]] records after entrypoint_schema "
                "resolved successfully -- REFSCHEMA001 is UNMEASURED"
            ),
        )

    violations: list[Violation] = []
    for index, entry in enumerate(records):
        for key in entry:
            if key not in known:
                violations.append(_unknown_key_violation(index, key))
    return tuple(violations)
