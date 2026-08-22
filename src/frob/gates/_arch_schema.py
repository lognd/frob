"""ARCHSCHEMA001 (T-2390 epic, child T-2433): an unknown key in the
`[arch]` table is silently ignored today -- the "config-file keys are
never validated" defect class T-2390 exists to close, applied to
`[arch]` (10 known keys: the 5 T-0373 size thresholds plus the 5 T-0728
SRP/cohesion knobs -- this repo's own frob.toml currently sets 5 of the
10).

`frob.repo_meta.load_arch_config` hand-lists its 10 named keys against
its own calibrated-defaults dict and reads each via `arch_cfg.get(key,
default)` -- a misspelled key (e.g. "max_fuction_lines", this epic's own
filing-time example) silently reverts to the built-in default with no
diagnostic: the typo'd entry sits in frob.toml, looking configured, doing
nothing.

PORTABILITY (T-2384's doctrine): the known-key set is declared via
`[arch_schema] known_keys = "module:symbol"` pointed at `arch_known_
keys` below, resolved through the same `frob.gates._docblocks_shared.
resolve_dotted_symbol` idiom every T-2390 child uses. `load_arch_
config` lives in `frob.repo_meta` -- a different strata component from
`frob.gates` -- so, following the T-2429 lesson (importing its default
constants directly here would introduce an undeclared cross-component
Flow and trip SYS003/SELFAUDIT001), the 10 known key NAMES are
hardcoded as a literal tuple in this module rather than imported from
`frob.repo_meta`'s own default-value constants; any project can still
declare its own known-key set for its own [arch]-shaped table without
touching this module.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED` mechanism, same posture as every other T-2390 child): no
`[arch_schema] known_keys` declared, an unresolvable dotted path, or a
resolved value that is neither a set nor a set-returning callable all
report `Severity.UNRESOLVED` -- never a silently empty (and therefore
falsely "clean") violation list.


NESTED SUB-TABLE EXCLUSION: `[arch.layering]` (T-0620's DIP layering
contract, `frob.arch._layering`) is a genuinely different, deliberately
inert, documented sub-table nested one level inside `[arch]` -- its
`layers`/`allow` schema has nothing to do with `load_arch_config`'s flat
integer-threshold known-key set, so a dict-valued key inside `[arch]` is
excluded from this check entirely (a real, intentional sub-table, not a
stray/misspelled leaf value).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, cast

from frob.gates._docblocks_shared import resolve_dotted_symbol
from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

#: The exact key set `frob.repo_meta.load_arch_config` reads -- kept as
#: one shared tuple so both this module and a future refactor of
#: `load_arch_config` itself have a single place to add a new arch knob.
# frob:doc docs/modules/gates.md#archschema001-t-2390-epic-child-t-2433
# frob:ticket T-2433
# frob:waive COV007 reason="docs/modules/gates.md's ARCHSCHEMA001 (T-2390 epic child, \
# T-2433) section documents several symbols under one section, not just a public entry \
# point -- the many-symbols- one-section convention this repo already accepted for \
# vet.md (T-2810 declined to touch it), not a T-2810-shaped duplicate"
_ARCH_DEFAULT_KEYS: tuple[str, ...] = (
    "max_function_lines",
    "max_class_methods",
    "max_local_imports",
    "max_nesting_depth",
    "max_file_lines",
    "lcom4_min_methods",
    "lcom4_min_field_using_methods",
    "god_module_min_exports",
    "god_module_min_clusters",
    "mixed_concern_min_decision_points",
)


# frob:doc docs/modules/gates.md#archschema001-t-2390-epic-child-t-2433
# frob:tests \
# tests/unit/test_arch_table_schema.py::TestArchSchemaGate.test_arch_known_keys_matches\
# _load_arch_configs_own_defaults kind="unit"
# frob:ticket T-2433
def arch_known_keys() -> frozenset[str]:
    """`[arch]`'s known-key set -- the exact 10 names `frob.repo_meta.
    load_arch_config` reads, kept in ONE place (`_ARCH_DEFAULT_KEYS`
    above) rather than duplicated separately in this module and that
    one."""
    return frozenset(_ARCH_DEFAULT_KEYS)


# frob:ticket T-2433
def _unresolved(message: str) -> Violation:
    """One ARCHSCHEMA001 `Severity.UNRESOLVED` finding -- this check
    could not determine an answer, never rendered as a clean zero."""
    return Violation(
        rule="ARCHSCHEMA001",
        severity=Severity.UNRESOLVED,
        file="frob.toml",
        line=0,
        message=f"ARCHSCHEMA001: {message}",
    )


# frob:ticket T-2433
def _unknown_key_violation(key: str) -> Violation:
    """One ARCHSCHEMA001 `Severity.ERROR` finding: the `[arch]` table
    carries an undeclared key `key`."""
    return Violation(
        rule="ARCHSCHEMA001",
        severity=Severity.ERROR,
        file="frob.toml",
        line=0,
        message=(
            f"ARCHSCHEMA001: [arch] has an undeclared key {key!r} -- not "
            f"one of the 10 names frob.repo_meta.load_arch_config reads "
            f"via arch_cfg.get(key, default), so it silently reverts to "
            f"the built-in calibrated default with no diagnostic; fix "
            f"the typo, remove the stray key, or extend load_arch_"
            f"config's own defaults dict if this key is genuinely meant "
            f"to be supported"
        ),
    )


# frob:ticket T-2433
def _resolve_known_keys(root: Path) -> tuple[frozenset[str] | None, Violation | None]:
    """Resolve `[arch_schema] known_keys` to a real `frozenset[str]`, or
    return the `Violation` explaining why not."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None, _unresolved(
            "no frob.toml at all -- ARCHSCHEMA001 cannot determine this "
            "project's [arch] surface"
        )
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return None, _unresolved(f"frob.toml unreadable: {exc}")

    schema_dotted = doc.get("arch_schema", {}).get("known_keys")
    if not isinstance(schema_dotted, str) or not schema_dotted:
        return None, _unresolved(
            "no [arch_schema] known_keys declared in frob.toml -- "
            "ARCHSCHEMA001 cannot determine this project's [arch] "
            "known-key set at all; this is an UNMEASURED project, not a "
            'clean pass. Declare known_keys = "module:symbol" (a '
            "frozenset[str], or a zero-arg callable returning one) to "
            "enable this check"
        )

    resolved = resolve_dotted_symbol(schema_dotted, log_prefix="archschema001")
    if resolved is None:
        return None, _unresolved(
            f"could not resolve known_keys={schema_dotted!r} -- see the "
            f"archschema001 warning log line for the underlying import/"
            f"attribute error; ARCHSCHEMA001 is UNMEASURED, not clean"
        )

    known = cast(Any, resolved)() if callable(resolved) else resolved
    if not isinstance(known, frozenset | set):
        return None, _unresolved(
            f"known_keys={schema_dotted!r} resolved to a "
            f"{type(known).__name__}, not a frozenset[str]/set[str] "
            f"(directly, or via a zero-arg callable) -- ARCHSCHEMA001 "
            f"is UNMEASURED, not clean"
        )
    return cast("frozenset[str]", frozenset(known)), None


# frob:ticket T-2433
# frob:waive EXHAUST003 reason="the try/except here is narrowly scoped to \
# tomllib.load's own documented failure modes (OSError, tomllib.TOMLDecodeError), \
# identical in shape to _resolve_known_keys's own tomllib.load call a few lines above \
# in this same file (not flagged) -- the resolver's coverage gap is inherent ambiguity \
# in resolving doc.get(...).get(...) chains on an untyped tomllib result, not a real \
# unhandled-exception risk"
def _arch_table(root: Path) -> dict | None:
    """The RAW `[arch]` table straight off `tomllib.load`. Returns `None`
    if frob.toml is missing/malformed, or the table is absent (same
    fail-open posture `_resolve_known_keys` uses)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    table = doc.get("arch")
    if not isinstance(table, dict):
        return None
    return table


# frob:enforces CHK-GATE-ARCHSCHEMA001
# frob:doc docs/modules/gates.md#archschema001-t-2390-epic-child-t-2433
# frob:tests \
# tests/unit/test_arch_table_schema.py::TestArchSchemaGate.test_must_now_fire_reports_t\
# he_undeclared_key kind="unit"
# frob:tests \
# tests/unit/test_arch_table_schema.py::TestArchSchemaGate.test_must_still_pass_this_re\
# pos_own_frob_toml kind="unit"
# frob:ticket T-2433
def arch_schema_gate(root: Path) -> tuple[Violation, ...]:
    """ARCHSCHEMA001: the `[arch]` table's key set, checked against the
    declared `[arch_schema] known_keys` source (by default, the exact 10
    names `load_arch_config` reads). Reports `Severity.UNRESOLVED` (never
    a silent pass) when no schema is declared or it fails to resolve;
    otherwise one ERROR per undeclared key found (no `[arch]` table at
    all is not itself an error -- the table is optional, same posture
    `load_arch_config` itself uses)."""
    known, violation = _resolve_known_keys(root)
    if violation is not None:
        return (violation,)
    assert known is not None  # noqa: S101 -- invariant: _resolve_known_keys returns exactly one of (known, violation) as non-None

    table = _arch_table(root)
    if table is None:
        return ()

    # T-0620's `[arch.layering]` is a genuinely DIFFERENT, deliberately
    # inert, documented sub-table (its own layers/allow schema, not yet
    # wired into frob check) nested one level inside [arch] -- a dict-
    # valued key here is a real sub-table, not a stray/misspelled leaf
    # value of load_arch_config's flat known-key set, so it is excluded
    # from consideration the same way TOPSCALARSCHEMA001 excludes real
    # [table] headers from ITS scalar-key check.
    return tuple(
        _unknown_key_violation(key)
        for key, value in table.items()
        if key not in known and not isinstance(value, dict)
    )
