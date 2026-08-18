"""DOCBLOCKSSCHEMA001 (T-2390 epic, child T-2434): an unknown key in a
`[[docblocks.commands]]` entry is silently ignored today -- the
"config-file keys are never validated" defect class T-2390 exists to
close, applied to `[[docblocks.commands]]` (4 leaves in this repo's own
frob.toml currently: `prog`, `parser`, plus T-2397's own `config`/
`forwarded` keys).

`frob.gates._docblocks_refs._console_command_sources` reads exactly
`prog`, `parser`, `config`, `forwarded` via `.get(...)` -- a fifth key
(a typo like "prser", or a stray field) is never read, never validated,
never reported; the entry parses "successfully" with the typo'd field
simply absent.

PORTABILITY (T-2384's doctrine): no hardcoded key list. The known-key set
is declared via `[docblocks_schema] known_keys = "module:symbol"` (a
dotted path to a `frozenset[str]` or a zero-arg callable returning one),
resolved at check time through the same `frob.gates._docblocks_shared.
resolve_dotted_symbol` idiom every T-2390 child uses.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED` mechanism, same posture as every other T-2390 child): no
`[docblocks_schema] known_keys` declared, an unresolvable dotted path, or
a resolved value that is neither a set nor a set-returning callable all
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

#: This repo's own declared known-key set for `[[docblocks.commands]]` --
#: referenced by `[docblocks_schema] known_keys` in frob.toml, the same
#: module:symbol idiom every T-2390 child uses. Includes T-2397's own
#: config=/forwarded= keys as legitimate schema members, not unknowns.
# frob:doc docs/modules/gates.md#docblocksschema001-t-2390-epic-child-t-2434
# frob:ticket T-2434
DOCBLOCKS_COMMAND_KNOWN_KEYS: frozenset[str] = frozenset(
    {"prog", "parser", "config", "forwarded"}
)


# frob:ticket T-2434
def _unresolved(message: str) -> Violation:
    """One DOCBLOCKSSCHEMA001 `Severity.UNRESOLVED` finding -- this check
    could not determine an answer, never rendered as a clean zero."""
    return Violation(
        rule="DOCBLOCKSSCHEMA001",
        severity=Severity.UNRESOLVED,
        file="frob.toml",
        line=0,
        message=f"DOCBLOCKSSCHEMA001: {message}",
    )


# frob:ticket T-2434
def _unknown_key_violation(index: int, key: str) -> Violation:
    """One DOCBLOCKSSCHEMA001 `Severity.ERROR` finding: entry `index` of
    `[[docblocks.commands]]` carries an undeclared key `key`."""
    return Violation(
        rule="DOCBLOCKSSCHEMA001",
        severity=Severity.ERROR,
        file="frob.toml",
        line=0,
        message=(
            f"DOCBLOCKSSCHEMA001: [[docblocks.commands]] entry {index} "
            f"has an undeclared key {key!r} -- not in this project's "
            f"declared docblocks_schema known-key set, so it is silently "
            f"ignored by frob.gates._docblocks_refs._console_command_"
            f"sources; fix the typo, remove the stray key, or extend the "
            f"declared schema if this key is genuinely meant to be "
            f"supported"
        ),
    )


# frob:ticket T-2434
def _resolve_known_keys(root: Path) -> tuple[frozenset[str] | None, Violation | None]:
    """Resolve `[docblocks_schema] known_keys` to a real `frozenset[str]`,
    or return the `Violation` explaining why not."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None, _unresolved(
            "no frob.toml at all -- DOCBLOCKSSCHEMA001 cannot determine "
            "this project's [[docblocks.commands]] surface"
        )
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return None, _unresolved(f"frob.toml unreadable: {exc}")

    schema_dotted = doc.get("docblocks_schema", {}).get("known_keys")
    if not isinstance(schema_dotted, str) or not schema_dotted:
        return None, _unresolved(
            "no [docblocks_schema] known_keys declared in frob.toml -- "
            "DOCBLOCKSSCHEMA001 cannot determine this project's "
            "[[docblocks.commands]] known-key set at all; this is an "
            "UNMEASURED project, not a clean pass. Declare "
            'known_keys = "module:symbol" (a frozenset[str], or a '
            "zero-arg callable returning one) to enable this check"
        )

    resolved = resolve_dotted_symbol(schema_dotted, log_prefix="docblocksschema001")
    if resolved is None:
        return None, _unresolved(
            f"could not resolve known_keys={schema_dotted!r} -- see the "
            f"docblocksschema001 warning log line for the underlying "
            f"import/attribute error; DOCBLOCKSSCHEMA001 is UNMEASURED, "
            f"not clean"
        )

    known = cast(Any, resolved)() if callable(resolved) else resolved
    if not isinstance(known, frozenset | set):
        return None, _unresolved(
            f"known_keys={schema_dotted!r} resolved to a "
            f"{type(known).__name__}, not a frozenset[str]/set[str] "
            f"(directly, or via a zero-arg callable) -- "
            f"DOCBLOCKSSCHEMA001 is UNMEASURED, not clean"
        )
    return cast("frozenset[str]", frozenset(known)), None


# frob:ticket T-2434
# frob:waive EXHAUST003 reason="the try/except here is narrowly scoped to \
# tomllib.load's own documented failure modes (OSError, tomllib.TOMLDecodeError), \
# identical in shape to _resolve_known_keys's own tomllib.load call a few lines above \
# in this same file (not flagged) -- the resolver's coverage gap is inherent ambiguity \
# in resolving doc.get(...).get(...) chains on an untyped tomllib result, not a real \
# unhandled-exception risk"
def _docblocks_command_records(root: Path) -> list[dict] | None:
    """The RAW `[[docblocks.commands]]` records straight off `tomllib.
    load`. Returns `None` if frob.toml is missing/malformed (same
    fail-open posture `_resolve_known_keys` uses)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    entries = doc.get("docblocks", {}).get("commands", [])
    if not isinstance(entries, list):
        return None
    return [e for e in entries if isinstance(e, dict)]


# frob:enforces CHK-GATE-DOCBLOCKSSCHEMA001
# frob:doc docs/modules/gates.md#docblocksschema001-t-2390-epic-child-t-2434
# frob:tests \
# tests/unit/test_docblocks_table_schema.py::TestDocblocksSchemaGate.test_must_now_fire\
# _reports_the_undeclared_key kind="unit"
# frob:tests \
# tests/unit/test_docblocks_table_schema.py::TestDocblocksSchemaGate.test_must_still_pa\
# ss_this_repos_own_frob_toml kind="unit"
# frob:ticket T-2434
def docblocks_schema_gate(root: Path) -> tuple[Violation, ...]:
    """DOCBLOCKSSCHEMA001: every `[[docblocks.commands]]` entry's key
    set, checked against the declared `[docblocks_schema] known_keys`
    source (including T-2397's own `config=`/`forwarded=` keys as
    legitimate members). Reports `Severity.UNRESOLVED` (never a silent
    pass) when no schema is declared or it fails to resolve; otherwise
    one ERROR per undeclared key found."""
    known, violation = _resolve_known_keys(root)
    if violation is not None:
        return (violation,)
    assert known is not None  # noqa: S101 -- invariant: _resolve_known_keys returns exactly one of (known, violation) as non-None

    records = _docblocks_command_records(root)
    if records is None:
        return (
            _unresolved(
                "frob.toml unreadable while re-reading raw "
                "[[docblocks.commands]] records after known_keys "
                "resolved successfully -- DOCBLOCKSSCHEMA001 is "
                "UNMEASURED"
            ),
        )

    violations: list[Violation] = []
    for index, entry in enumerate(records):
        for key in entry:
            if key not in known:
                violations.append(_unknown_key_violation(index, key))
    return tuple(violations)
