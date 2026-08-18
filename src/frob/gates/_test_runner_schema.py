"""TESTRUNNERSCHEMA001 (T-2390 epic, child T-2436): an unknown key in a
`[[test.runner]]` entry is silently ignored today -- the "config-file
keys are never validated" defect class T-2390 exists to close, applied
to `[[test.runner]]` (16 leaves across 4 entries in this repo's own
frob.toml: `language`/`command`/`all_command`/`cwd` set on every entry;
`collector`/`timeout_s` are legitimate optional keys no entry currently
sets).

`frob.testing._runners._parse_runner_entry` reads `command`/
`all_command`/`language` (required, `entry[...]`, a missing one logs an
error and drops the whole entry) plus `cwd`/`collector`/`timeout_s`
(optional, `.get()` with a default) -- a seventh key (a typo like
"al_command", or a stray field) is never read, never validated, never
reported.

PORTABILITY (T-2384's doctrine): no hardcoded key list beyond this
module's own literal (see the COMPONENT MEMBERSHIP note below). The
known-key set is declared via `[test_runner_schema] known_keys =
"module:symbol"` (a dotted path to a `frozenset[str]` or a zero-arg
callable returning one), resolved through the same `frob.gates.
_docblocks_shared.resolve_dotted_symbol` idiom every T-2390 child uses.

COMPONENT MEMBERSHIP (the T-2429 lesson, re-applied): `frob.testing.
_runners` (the actual `[[test.runner]]` reader) lives in a different
strata component from `frob.gates` -- so, exactly as with T-2433's
`[arch]` child, the known-key set here is a plain hardcoded literal
tuple of key NAMES in this `frob.gates` module, never an import of
`frob.testing._runners`'s own internals (which would introduce an
undeclared cross-component Flow and trip SYS003/SELFAUDIT001).

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED` mechanism, same posture as every other T-2390 child): no
`[test_runner_schema] known_keys` declared, an unresolvable dotted path,
or a resolved value that is neither a set nor a set-returning callable
all report `Severity.UNRESOLVED` -- never a silently empty (and
therefore falsely "clean") violation list.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, cast

from frob.gates._docblocks_shared import resolve_dotted_symbol
from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

#: This repo's own declared known-key set for `[[test.runner]]` --
#: referenced by `[test_runner_schema] known_keys` in frob.toml, the same
#: module:symbol idiom every T-2390 child uses. Mirrors `frob.testing.
#: _runners._parse_runner_entry`'s own reads exactly (3 required:
#: language/command/all_command; 3 optional: cwd/collector/timeout_s) --
#: kept in sync by hand since that module lives in a different strata
#: component (see this module's COMPONENT MEMBERSHIP docstring note).
# frob:doc docs/modules/gates.md#testrunnerschema001-t-2390-epic-child-t-2436
# frob:ticket T-2436
TEST_RUNNER_KNOWN_KEYS: frozenset[str] = frozenset(
    {"language", "command", "all_command", "cwd", "collector", "timeout_s"}
)


# frob:ticket T-2436
def _unresolved(message: str) -> Violation:
    """One TESTRUNNERSCHEMA001 `Severity.UNRESOLVED` finding -- this
    check could not determine an answer, never rendered as a clean
    zero."""
    return Violation(
        rule="TESTRUNNERSCHEMA001",
        severity=Severity.UNRESOLVED,
        file="frob.toml",
        line=0,
        message=f"TESTRUNNERSCHEMA001: {message}",
    )


# frob:ticket T-2436
def _unknown_key_violation(index: int, key: str) -> Violation:
    """One TESTRUNNERSCHEMA001 `Severity.ERROR` finding: entry `index` of
    `[[test.runner]]` carries an undeclared key `key`."""
    return Violation(
        rule="TESTRUNNERSCHEMA001",
        severity=Severity.ERROR,
        file="frob.toml",
        line=0,
        message=(
            f"TESTRUNNERSCHEMA001: [[test.runner]] entry {index} has an "
            f"undeclared key {key!r} -- not in this project's declared "
            f"test_runner_schema known-key set, so it is silently "
            f"ignored by frob.testing._runners._parse_runner_entry; fix "
            f"the typo, remove the stray key, or extend the declared "
            f"schema if this key is genuinely meant to be supported"
        ),
    )


# frob:ticket T-2436
def _resolve_known_keys(root: Path) -> tuple[frozenset[str] | None, Violation | None]:
    """Resolve `[test_runner_schema] known_keys` to a real
    `frozenset[str]`, or return the `Violation` explaining why not."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None, _unresolved(
            "no frob.toml at all -- TESTRUNNERSCHEMA001 cannot determine "
            "this project's [[test.runner]] surface"
        )
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return None, _unresolved(f"frob.toml unreadable: {exc}")

    schema_dotted = doc.get("test_runner_schema", {}).get("known_keys")
    if not isinstance(schema_dotted, str) or not schema_dotted:
        return None, _unresolved(
            "no [test_runner_schema] known_keys declared in frob.toml "
            "-- TESTRUNNERSCHEMA001 cannot determine this project's "
            "[[test.runner]] known-key set at all; this is an "
            "UNMEASURED project, not a clean pass. Declare "
            'known_keys = "module:symbol" (a frozenset[str], or a '
            "zero-arg callable returning one) to enable this check"
        )

    resolved = resolve_dotted_symbol(schema_dotted, log_prefix="testrunnerschema001")
    if resolved is None:
        return None, _unresolved(
            f"could not resolve known_keys={schema_dotted!r} -- see the "
            f"testrunnerschema001 warning log line for the underlying "
            f"import/attribute error; TESTRUNNERSCHEMA001 is UNMEASURED, "
            f"not clean"
        )

    known = cast(Any, resolved)() if callable(resolved) else resolved
    if not isinstance(known, frozenset | set):
        return None, _unresolved(
            f"known_keys={schema_dotted!r} resolved to a "
            f"{type(known).__name__}, not a frozenset[str]/set[str] "
            f"(directly, or via a zero-arg callable) -- "
            f"TESTRUNNERSCHEMA001 is UNMEASURED, not clean"
        )
    return cast("frozenset[str]", frozenset(known)), None


# frob:ticket T-2436
# frob:waive EXHAUST003 reason="the try/except here is narrowly scoped to \
# tomllib.load's own documented failure modes (OSError, tomllib.TOMLDecodeError), \
# identical in shape to _resolve_known_keys's own tomllib.load call a few lines above \
# in this same file (not flagged) -- the resolver's coverage gap is inherent ambiguity \
# in resolving doc.get(...).get(...) chains on an untyped tomllib result, not a real \
# unhandled-exception risk"
def _test_runner_records(root: Path) -> list[dict] | None:
    """The RAW `[[test.runner]]` records straight off `tomllib.load`.
    Returns `None` if frob.toml is missing/malformed (same fail-open
    posture `_resolve_known_keys` uses)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    entries = doc.get("test", {}).get("runner", [])
    if not isinstance(entries, list):
        return None
    return [e for e in entries if isinstance(e, dict)]


# frob:enforces CHK-GATE-TESTRUNNERSCHEMA001
# frob:doc docs/modules/gates.md#testrunnerschema001-t-2390-epic-child-t-2436
# frob:tests \
# tests/unit/test_test_table_schema.py::TestTestRunnerSchemaGate.test_must_now_fire_rep\
# orts_the_undeclared_key kind="unit"
# frob:tests \
# tests/unit/test_test_table_schema.py::TestTestRunnerSchemaGate.test_must_still_pass_t\
# his_repos_own_frob_toml kind="unit"
# frob:ticket T-2436
def test_runner_schema_gate(root: Path) -> tuple[Violation, ...]:
    """TESTRUNNERSCHEMA001: every `[[test.runner]]` entry's key set,
    checked against the declared `[test_runner_schema] known_keys`
    source. Reports `Severity.UNRESOLVED` (never a silent pass) when no
    schema is declared or it fails to resolve; otherwise one ERROR per
    undeclared key found."""
    known, violation = _resolve_known_keys(root)
    if violation is not None:
        return (violation,)
    assert known is not None  # noqa: S101 -- invariant: _resolve_known_keys returns exactly one of (known, violation) as non-None

    records = _test_runner_records(root)
    if records is None:
        return (
            _unresolved(
                "frob.toml unreadable while re-reading raw "
                "[[test.runner]] records after known_keys resolved "
                "successfully -- TESTRUNNERSCHEMA001 is UNMEASURED"
            ),
        )

    violations: list[Violation] = []
    for index, entry in enumerate(records):
        for key in entry:
            if key not in known:
                violations.append(_unknown_key_violation(index, key))
    return tuple(violations)
