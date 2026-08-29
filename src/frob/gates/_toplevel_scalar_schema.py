"""TOPSCALARSCHEMA001 (T-2390 epic, child T-2431): an unknown top-level
SCALAR key in `frob.toml` (a key with no enclosing `[table]` at all) is
silently ignored today -- the "config-file keys are never validated"
defect class T-2390 exists to close, applied to the two top-level scalars
this repo's own frob.toml declares (`min_frob_version`, `check_base`).

Structurally different from every other T-2390 child: there is no
`[table]` to iterate and no array-of-records, just a flat set of bare
key = value lines at the document root. `frob.repo_meta.
declared_min_frob_version` and `frob.app.check_runner`'s `check_base`
default-fill both read exactly ONE name each via `.get(...)` -- a
misspelled top-level key (`"min_frob_verison"`, "chek_base") is never
read, never validated, and frob.toml's own top-level namespace is shared
with every `[table]` name too, so a typo here could ALSO collide with (or
be mistaken for) a table header typo -- this check only concerns the
scalar-shaped keys, not tables.

PORTABILITY (T-2384's doctrine): no hardcoded key list. The known-key set
is declared via a dedicated `[toplevel_scalar_schema] known_keys =
"module:symbol"` sub-table (kept OUT of the document root itself so the
declaration key can never be mistaken for one of the scalars it
describes) -- a dotted path to a `frozenset[str]` or a zero-arg callable
returning one, resolved through the same `frob.gates._docblocks_shared.
resolve_dotted_symbol` idiom every T-2390 child uses.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED` mechanism, same posture as every other T-2390 child): no
`[toplevel_scalar_schema] known_keys` declared, an unresolvable dotted
path, or a resolved value that is neither a set nor a set-returning
callable all report `Severity.UNRESOLVED` -- never a silently empty (and
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

#: This repo's own declared known-key set for frob.toml's top-level
#: SCALAR keys -- referenced by `[toplevel_scalar_schema] known_keys` in
#: frob.toml, the same module:symbol idiom every T-2390 child uses.
# frob:doc docs/modules/gates.md#topscalarschema001-t-2390-epic-child-t-2431
# frob:ticket T-2431
TOPLEVEL_SCALAR_KNOWN_KEYS: frozenset[str] = frozenset(
    {"min_frob_version", "check_base"}
)


# frob:ticket T-2431
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _unresolved(message: str) -> Violation:
    """One TOPSCALARSCHEMA001 `Severity.UNRESOLVED` finding -- this check
    could not determine an answer, never rendered as a clean zero."""
    return Violation(
        rule="TOPSCALARSCHEMA001",
        severity=Severity.UNRESOLVED,
        file="frob.toml",
        line=0,
        message=f"TOPSCALARSCHEMA001: {message}",
    )


# frob:ticket T-2431
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _unknown_key_violation(key: str) -> Violation:
    """One TOPSCALARSCHEMA001 `Severity.ERROR` finding: a top-level
    scalar key `key` is undeclared."""
    return Violation(
        rule="TOPSCALARSCHEMA001",
        severity=Severity.ERROR,
        file="frob.toml",
        line=0,
        message=(
            f"TOPSCALARSCHEMA001: top-level key {key!r} is an undeclared "
            f"scalar -- not in this project's declared "
            f"[toplevel_scalar_schema] known_keys set, so it is silently "
            f"ignored by every reader that only ever looks for the two "
            f"known names (frob.repo_meta.declared_min_frob_version, "
            f"frob.app.check_runner's check_base default-fill); fix the "
            f"typo, remove the stray key, or extend the declared schema "
            f"if this key is genuinely meant to be supported"
        ),
    )


# frob:ticket T-2431
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _resolve_known_keys(root: Path) -> tuple[frozenset[str] | None, Violation | None]:
    """Resolve `[toplevel_scalar_schema] known_keys` to a real
    `frozenset[str]`, or return the `Violation` explaining why not."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None, _unresolved(
            "no frob.toml at all -- TOPSCALARSCHEMA001 cannot determine "
            "this project's top-level scalar surface"
        )
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return None, _unresolved(f"frob.toml unreadable: {exc}")

    schema_dotted = doc.get("toplevel_scalar_schema", {}).get("known_keys")
    if not isinstance(schema_dotted, str) or not schema_dotted:
        # T-3273: no [toplevel_scalar_schema] known_keys declared --
        # default to frob's own TOPLEVEL_SCALAR_KNOWN_KEYS rather than
        # UNMEASURED; nothing project-specific lives in this table.
        return TOPLEVEL_SCALAR_KNOWN_KEYS, None

    resolved = resolve_dotted_symbol(schema_dotted, log_prefix="topscalarschema001")
    if resolved is None:
        return None, _unresolved(
            f"could not resolve known_keys={schema_dotted!r} -- see the "
            f"topscalarschema001 warning log line for the underlying "
            f"import/attribute error; TOPSCALARSCHEMA001 is UNMEASURED, "
            f"not clean"
        )

    known = cast(Any, resolved)() if callable(resolved) else resolved
    if not isinstance(known, frozenset | set):
        return None, _unresolved(
            f"known_keys={schema_dotted!r} resolved to a "
            f"{type(known).__name__}, not a frozenset[str]/set[str] "
            f"(directly, or via a zero-arg callable) -- "
            f"TOPSCALARSCHEMA001 is UNMEASURED, not clean"
        )
    return cast("frozenset[str]", frozenset(known)), None


# frob:ticket T-2431
# frob:waive EXHAUST003 reason="the try/except here is narrowly scoped to \
# tomllib.load's own documented failure modes (OSError, tomllib.TOMLDecodeError), \
# identical in shape to _resolve_known_keys's own tomllib.load call a few lines above \
# in this same file (not flagged) -- the resolver's coverage gap is inherent ambiguity \
# in resolving doc.get(...).get(...) chains on an untyped tomllib result, not a real \
# unhandled-exception risk"
def _toplevel_scalar_keys(root: Path) -> list[str] | None:
    """The RAW top-level SCALAR key names straight off `tomllib.load` --
    every document-root key whose value is NOT table-shaped (neither a
    `dict` nor a `list` of `dict`) (a `[table]`,
    `[[array-of-tables]]` heading), so a table name is never mistaken for
    a scalar. `toplevel_scalar_schema` and `profile_schema`/`refs`/etc's
    own declaration sub-tables are themselves dicts, so they are excluded
    automatically by this same rule -- no special-casing needed. Returns
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

    def _is_table_shaped(value: object) -> bool:
        """`True` for a `[table]` (`dict`) or an `[[array-of-tables]]`
        (a `list` whose elements are themselves `dict`, including the
        empty list -- an array-of-tables header with zero entries still
        parses as `[]`, indistinguishable from a genuinely empty plain
        list, so an empty list is conservatively treated as table-shaped
        rather than risk misclassifying a real `[[array]]` as a scalar)."""
        if isinstance(value, dict):
            return True
        if isinstance(value, list):
            return not value or all(isinstance(item, dict) for item in value)
        return False

    return [key for key, value in doc.items() if not _is_table_shaped(value)]


# frob:enforces CHK-GATE-TOPSCALARSCHEMA001
# frob:doc docs/modules/gates.md#topscalarschema001-t-2390-epic-child-t-2431
# frob:tests \
# tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate.test_must_now\
# _fire_reports_the_undeclared_key kind="unit"
# frob:tests \
# tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate.test_must_sti\
# ll_pass_this_repos_own_frob_toml kind="unit"
# frob:ticket T-2431
def toplevel_scalar_schema_gate(root: Path) -> tuple[Violation, ...]:
    """TOPSCALARSCHEMA001: frob.toml's top-level SCALAR key set (no
    enclosing `[table]`), checked against the declared
    `[toplevel_scalar_schema] known_keys` source. Reports `Severity.
    UNRESOLVED` (never a silent pass) when no schema is declared or it
    fails to resolve; otherwise one ERROR per undeclared scalar key
    found. See this module's docstring for the full fail-loudly
    rationale."""
    known, violation = _resolve_known_keys(root)
    if violation is not None:
        return (violation,)
    assert known is not None  # noqa: S101 -- invariant: _resolve_known_keys returns exactly one of (known, violation) as non-None

    keys = _toplevel_scalar_keys(root)
    if keys is None:
        return (
            _unresolved(
                "frob.toml unreadable while re-reading raw top-level "
                "keys after known_keys resolved successfully -- "
                "TOPSCALARSCHEMA001 is UNMEASURED"
            ),
        )

    return tuple(_unknown_key_violation(key) for key in keys if key not in known)
