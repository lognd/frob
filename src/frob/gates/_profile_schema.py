"""PROFILESCHEMA001 (T-2390 epic, child T-2430): an unknown key in the
`[profile]` table is silently ignored today -- the "config-file keys are
never validated" defect class T-2390 exists to close, applied to
`[profile]` (2 leaves in this repo's own frob.toml, the smallest T-2390
child table).

`frob.tickets._profile.effective_profile`/`_override_ratchet_enabled`
read exactly `profile` and `override_ratchet` via `.get(...)` -- a third
key (a typo like "overide_ratchet", or a stray field) is never read,
never validated, never reported; the entry parses "successfully" with the
typo'd field simply absent, silently falling back to defaults.

PORTABILITY (T-2384's doctrine): no hardcoded key list. The known-key set
for `[profile]` is declared via `[profile_schema] known_keys = "module:
symbol"` (a dotted path to a `frozenset[str]` or a zero-arg callable
returning one), resolved at check time through the same `frob.gates.
_docblocks_shared.resolve_dotted_symbol` idiom every T-2390 child uses --
any project can declare its own known-key set without editing this
module.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED` mechanism, same posture as every other T-2390 child): no
`[profile_schema] known_keys` declared, an unresolvable dotted path, or a
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

#: This repo's own declared known-key set for `[profile]` -- referenced
#: by `[profile_schema] known_keys` in frob.toml, the same module:symbol
#: idiom every T-2390 child uses.
# frob:doc docs/modules/gates.md#profileschema001-t-2390-epic-child-t-2430
# frob:ticket T-2430
PROFILE_KNOWN_KEYS: frozenset[str] = frozenset({"profile", "override_ratchet"})


# frob:ticket T-2430
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _unresolved(message: str) -> Violation:
    """One PROFILESCHEMA001 `Severity.UNRESOLVED` finding -- this check
    could not determine an answer, never rendered as a clean zero."""
    return Violation(
        rule="PROFILESCHEMA001",
        severity=Severity.UNRESOLVED,
        file="frob.toml",
        line=0,
        message=f"PROFILESCHEMA001: {message}",
    )


# frob:ticket T-2430
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _unknown_key_violation(key: str) -> Violation:
    """One PROFILESCHEMA001 `Severity.ERROR` finding: the `[profile]`
    table carries an undeclared key `key`."""
    return Violation(
        rule="PROFILESCHEMA001",
        severity=Severity.ERROR,
        file="frob.toml",
        line=0,
        message=(
            f"PROFILESCHEMA001: [profile] has an undeclared key {key!r} "
            f"-- not in this project's declared [profile_schema] "
            f"known_keys set, so it is silently ignored by frob.tickets."
            f"_profile's own .get()-based reads; fix the typo, remove the "
            f"stray key, or extend the declared schema if this key is "
            f"genuinely meant to be supported"
        ),
    )


# frob:ticket T-2430
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _resolve_known_keys(root: Path) -> tuple[frozenset[str] | None, Violation | None]:
    """Resolve `[profile_schema] known_keys` to a real `frozenset[str]`,
    or return the `Violation` explaining why not."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None, _unresolved(
            "no frob.toml at all -- PROFILESCHEMA001 cannot determine "
            "this project's [profile] surface"
        )
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return None, _unresolved(f"frob.toml unreadable: {exc}")

    schema_dotted = doc.get("profile_schema", {}).get("known_keys")
    if not isinstance(schema_dotted, str) or not schema_dotted:
        return None, _unresolved(
            "no [profile_schema] known_keys declared in frob.toml -- "
            "PROFILESCHEMA001 cannot determine this project's [profile] "
            "known-key set at all; this is an UNMEASURED project, not a "
            'clean pass. Declare known_keys = "module:symbol" (a '
            "frozenset[str], or a zero-arg callable returning one) to "
            "enable this check"
        )

    resolved = resolve_dotted_symbol(schema_dotted, log_prefix="profileschema001")
    if resolved is None:
        return None, _unresolved(
            f"could not resolve known_keys={schema_dotted!r} -- see the "
            f"profileschema001 warning log line for the underlying "
            f"import/attribute error; PROFILESCHEMA001 is UNMEASURED, "
            f"not clean"
        )

    known = cast(Any, resolved)() if callable(resolved) else resolved
    if not isinstance(known, frozenset | set):
        return None, _unresolved(
            f"known_keys={schema_dotted!r} resolved to a "
            f"{type(known).__name__}, not a frozenset[str]/set[str] "
            f"(directly, or via a zero-arg callable) -- PROFILESCHEMA001 "
            f"is UNMEASURED, not clean"
        )
    return cast("frozenset[str]", frozenset(known)), None


# frob:ticket T-2430
# frob:waive EXHAUST003 reason="the try/except here is narrowly scoped to \
# tomllib.load's own documented failure modes (OSError, tomllib.TOMLDecodeError), \
# identical in shape to _resolve_known_keys's own tomllib.load call a few lines above \
# in this same file (not flagged) -- the resolver's coverage gap is inherent ambiguity \
# in resolving doc.get(...).get(...) chains on an untyped tomllib result, not a real \
# unhandled-exception risk"
def _profile_table(root: Path) -> dict | None:
    """The RAW `[profile]` table straight off `tomllib.load`. Returns
    `None` if frob.toml is missing/malformed, or the table is absent
    (same fail-open posture `_resolve_known_keys` uses)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    table = doc.get("profile")
    if not isinstance(table, dict):
        return None
    return table


# frob:enforces CHK-GATE-PROFILESCHEMA001
# frob:doc docs/modules/gates.md#profileschema001-t-2390-epic-child-t-2430
# frob:tests \
# tests/unit/test_profile_table_schema.py::TestProfileSchemaGate.test_must_now_fire_rep\
# orts_the_undeclared_key kind="unit"
# frob:tests \
# tests/unit/test_profile_table_schema.py::TestProfileSchemaGate.test_must_still_pass_t\
# his_repos_own_frob_toml kind="unit"
# frob:ticket T-2430
def profile_schema_gate(root: Path) -> tuple[Violation, ...]:
    """PROFILESCHEMA001: the `[profile]` table's key set, checked against
    the declared `[profile_schema] known_keys` source. Reports `Severity.
    UNRESOLVED` (never a silent pass) when no schema is declared or it
    fails to resolve; otherwise one ERROR per undeclared key found (no
    `[profile]` table at all is not itself an error -- the table is
    optional). See this module's docstring for the full fail-loudly
    rationale."""
    known, violation = _resolve_known_keys(root)
    if violation is not None:
        return (violation,)
    assert known is not None  # noqa: S101 -- invariant: _resolve_known_keys returns exactly one of (known, violation) as non-None

    table = _profile_table(root)
    if table is None:
        return ()

    return tuple(_unknown_key_violation(key) for key in table if key not in known)
