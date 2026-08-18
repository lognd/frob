"""TESTINGSCHEMA001 (T-2390 epic, child T-2432): an unknown key in the
`[testing]` table is silently ignored today -- the "config-file keys are
never validated" defect class T-2390 exists to close, applied to
`[testing]` (5 leaves in this repo's own frob.toml).

UNLIKE every other T-2390 child, `[testing]` already has a real pydantic
model (`frob.gates._models.TestPolicy`) -- but `frob.gates._sys.
_load_test_config` filters the raw table down to known fields BEFORE
constructing it: `TestPolicy(**{k: v for k, v in testing_tbl.items() if
k in fields})`. That `if k in fields` guard is exactly the silent-drop
this epic exists to close -- an unknown/misspelled key never reaches
`TestPolicy` at all, so `model_config` (even `extra="forbid"`) never gets
a chance to see it, let alone reject it. Confirms the epic's own finding:
having a real pydantic model for a table is NOT sufficient when the
raw-table reader pre-filters before construction.

PORTABILITY (T-2384's doctrine): rather than hand-listing `TestPolicy`'s
field names a second time (a second copy that could drift from the model
itself), the known-key set is declared via `[testing_schema] known_keys
= "module:symbol"` pointed at a zero-arg callable that reads `TestPolicy.
model_fields` directly -- the model itself stays the single source of
truth, resolved through the same `frob.gates._docblocks_shared.
resolve_dotted_symbol` idiom every T-2390 child uses.

FAIL-LOUDLY (T-2391's doctrine, via the already-shipped `Severity.
UNRESOLVED` mechanism, same posture as every other T-2390 child): no
`[testing_schema] known_keys` declared, an unresolvable dotted path, or a
resolved value that is neither a set nor a set-returning callable all
report `Severity.UNRESOLVED` -- never a silently empty (and therefore
falsely "clean") violation list.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, cast

from frob.gates._docblocks_shared import resolve_dotted_symbol
from frob.gates._models import Severity, TestPolicy, Violation
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/gates.md#testingschema001-t-2390-epic-child-t-2432
# frob:tests \
# tests/unit/test_testing_table_schema.py::TestTestingSchemaGate.test_testing_known_key\
# s_reads_test_policy_model_fields kind="unit"
# frob:ticket T-2432
def testing_known_keys() -> frozenset[str]:
    """`[testing]`'s known-key set, read directly off `TestPolicy.
    model_fields` -- the model itself is the single source of truth, no
    hand-maintained second copy of its field names."""
    return frozenset(TestPolicy.model_fields)


# frob:ticket T-2432
def _unresolved(message: str) -> Violation:
    """One TESTINGSCHEMA001 `Severity.UNRESOLVED` finding -- this check
    could not determine an answer, never rendered as a clean zero."""
    return Violation(
        rule="TESTINGSCHEMA001",
        severity=Severity.UNRESOLVED,
        file="frob.toml",
        line=0,
        message=f"TESTINGSCHEMA001: {message}",
    )


# frob:ticket T-2432
def _unknown_key_violation(key: str) -> Violation:
    """One TESTINGSCHEMA001 `Severity.ERROR` finding: the `[testing]`
    table carries an undeclared key `key`."""
    return Violation(
        rule="TESTINGSCHEMA001",
        severity=Severity.ERROR,
        file="frob.toml",
        line=0,
        message=(
            f"TESTINGSCHEMA001: [testing] has an undeclared key {key!r} "
            f"-- not a real frob.gates._models.TestPolicy field, so it is "
            f"silently dropped by frob.gates._sys._load_test_config's own "
            f"'if k in fields' pre-filter before TestPolicy is even "
            f"constructed; fix the typo, remove the stray key, or add the "
            f"field to TestPolicy if this key is genuinely meant to be "
            f"supported"
        ),
    )


# frob:ticket T-2432
def _resolve_known_keys(root: Path) -> tuple[frozenset[str] | None, Violation | None]:
    """Resolve `[testing_schema] known_keys` to a real `frozenset[str]`,
    or return the `Violation` explaining why not."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return None, _unresolved(
            "no frob.toml at all -- TESTINGSCHEMA001 cannot determine "
            "this project's [testing] surface"
        )
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return None, _unresolved(f"frob.toml unreadable: {exc}")

    schema_dotted = doc.get("testing_schema", {}).get("known_keys")
    if not isinstance(schema_dotted, str) or not schema_dotted:
        return None, _unresolved(
            "no [testing_schema] known_keys declared in frob.toml -- "
            "TESTINGSCHEMA001 cannot determine this project's [testing] "
            "known-key set at all; this is an UNMEASURED project, not a "
            'clean pass. Declare known_keys = "module:symbol" (a '
            "frozenset[str], or a zero-arg callable returning one) to "
            "enable this check"
        )

    resolved = resolve_dotted_symbol(schema_dotted, log_prefix="testingschema001")
    if resolved is None:
        return None, _unresolved(
            f"could not resolve known_keys={schema_dotted!r} -- see the "
            f"testingschema001 warning log line for the underlying "
            f"import/attribute error; TESTINGSCHEMA001 is UNMEASURED, "
            f"not clean"
        )

    known = cast(Any, resolved)() if callable(resolved) else resolved
    if not isinstance(known, frozenset | set):
        return None, _unresolved(
            f"known_keys={schema_dotted!r} resolved to a "
            f"{type(known).__name__}, not a frozenset[str]/set[str] "
            f"(directly, or via a zero-arg callable) -- "
            f"TESTINGSCHEMA001 is UNMEASURED, not clean"
        )
    return cast("frozenset[str]", frozenset(known)), None


# frob:ticket T-2432
# frob:waive EXHAUST003 reason="the try/except here is narrowly scoped to \
# tomllib.load's own documented failure modes (OSError, tomllib.TOMLDecodeError), \
# identical in shape to _resolve_known_keys's own tomllib.load call a few lines above \
# in this same file (not flagged) -- the resolver's coverage gap is inherent ambiguity \
# in resolving doc.get(...).get(...) chains on an untyped tomllib result, not a real \
# unhandled-exception risk"
def _testing_table(root: Path) -> dict | None:
    """The RAW `[testing]` table straight off `tomllib.load`. Returns
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
    table = doc.get("testing")
    if not isinstance(table, dict):
        return None
    return table


# frob:enforces CHK-GATE-TESTINGSCHEMA001
# frob:doc docs/modules/gates.md#testingschema001-t-2390-epic-child-t-2432
# frob:tests \
# tests/unit/test_testing_table_schema.py::TestTestingSchemaGate.test_must_now_fire_rep\
# orts_the_undeclared_key kind="unit"
# frob:tests \
# tests/unit/test_testing_table_schema.py::TestTestingSchemaGate.test_must_still_pass_t\
# his_repos_own_frob_toml kind="unit"
# frob:ticket T-2432
def testing_schema_gate(root: Path) -> tuple[Violation, ...]:
    """TESTINGSCHEMA001: the `[testing]` table's key set, checked against
    the declared `[testing_schema] known_keys` source (by default,
    `TestPolicy.model_fields` itself -- see this module's docstring for
    why the raw-table pre-filter in `_load_test_config` makes the
    existing pydantic model insufficient on its own). Reports `Severity.
    UNRESOLVED` (never a silent pass) when no schema is declared or it
    fails to resolve; otherwise one ERROR per undeclared key found (no
    `[testing]` table at all is not itself an error -- the table is
    optional)."""
    known, violation = _resolve_known_keys(root)
    if violation is not None:
        return (violation,)
    assert known is not None  # noqa: S101 -- invariant: _resolve_known_keys returns exactly one of (known, violation) as non-None

    table = _testing_table(root)
    if table is None:
        return ()

    return tuple(
        _unknown_key_violation(key) for key in table if key not in known
    )
