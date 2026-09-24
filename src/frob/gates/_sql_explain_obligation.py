"""SQLEXPLAIN001 (T-5339): an EXPLAIN-ANALYZE-artifact obligation on a
`frob:waive` of a SQL performance finding (`frob.sql._sqlfluff_plugin`'s
Frob_L001-L004, T-5335/T-5148-1) -- a bare `reason="..."` prose waiver is
not accepted for these findings the way it is for most rules; the
waiver must ALSO carry an `explain="path"` attribute naming a real,
tracked EXPLAIN ANALYZE artifact file, proving the waived query's plan
was actually checked, not merely asserted safe in prose.

## Precedent reused, not invented

T-5339's own ticket body: "reuse the closest existing 'proof required
before waiver' precedent in frob.gates ... rather than inventing a new
obligation shape." The closest precedent is INV008
(`frob.gates._design_invariants.inv008_violations`, T-0757): a
`frob:invariant ... establishes="..."` obligation is not discharged by
its own bare declaration -- it additionally requires a bound
`frob:tests ... kind="property"` edge at the SAME anchor before the
PROVABILITY CONSTRAINT (T-0331: "bare declaration never discharges an
obligation") is satisfied. This gate is that identical shape applied to
`frob:waive` instead of `frob:invariant`: the obligation-bearing
directive already exists (`frob:waive`'s own generic `key="value"` attr
grammar, `frob.graph.dsl._ATTR_RE`, already accepts an `explain=` attr
with no `frob.graph.dsl` change needed -- only `reason=`/`preset=`/
`until=` are validated there, any other attr simply rides along in
`Edge.attrs`), and the obligation is "is the attached PROOF real" rather
than "does a bound test exist" -- same two-part shape (declared,
proven), different proof kind.

## Rule-id scope (discovery, T-5308's convention)

`_DEFAULT_OBLIGATION_RULE_PREFIXES` names the one rule family this leaf
ships against (`Frob_L`, T-5335's sqlfluff plugin performance rules).
Future SQL rule families that need the same obligation (e.g. a later
`frob.sql._orm_rules` performance corpus) opt in without editing this
gate: `_discover_obligation_rule_prefixes` `pkgutil`-discovers every
`frob.sql._*` submodule exposing a module-level
`EXPLAIN_OBLIGATION_RULE_PREFIX: str` attribute and adds it to the set --
the same "leaf modules expose a hook, the gate discovers it" shape
`frob.gates._taint_gate._discover_websec_hook_modules` (T-5308) already
established for `frob.webapp._websec_*`. No `frob.sql` submodule
declares the hook yet (T-5335's `_sqlfluff_plugin.py` is out of this
ticket's own scope to edit), so discovery is additive-but-currently-
empty -- the default prefix set alone covers this leaf's own fixture.
"""

from __future__ import annotations

import pkgutil
from importlib import import_module
from pathlib import Path

import frob.sql
from frob.gates._models import Severity, Violation
from frob.graph import Edge, EdgeKind, GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["sql_explain_obligation_gate"]

#: T-5339: the one SQL rule-id prefix this leaf ships the EXPLAIN
#: obligation against -- `frob.sql._sqlfluff_plugin`'s `Frob_L001`-
#: `Frob_L004` (T-5335), sqlfluff's own `Rule_Frob_LNNN` -> `Frob_LNNN`
#: code composition (see that module's own docstring).
_DEFAULT_OBLIGATION_RULE_PREFIXES: frozenset[str] = frozenset({"Frob_L"})

#: T-5339: the module-level hook name `_discover_obligation_rule_prefixes`
#: looks for on each `frob.sql._*` submodule (T-5308's discovery
#: contract, applied to a plain `str` attribute instead of a callable --
#: a rule-id PREFIX is data, not behavior, so there is nothing to call).
_HOOK_ATTR_NAME = "EXPLAIN_OBLIGATION_RULE_PREFIX"

#: T-5339: the artifact directory an `explain="..."` attribute's value
#: must resolve inside (repo-root-relative) -- this ticket's own declared
#: fixture scope (`tests/fixtures/sql/explain/**`); a path pointing
#: anywhere else is treated the same as a missing artifact (an
#: `explain=` attribute is a proof-location claim, not a free-form note,
#: so a claim outside the one directory this obligation actually audits
#: is not proof of anything this gate can itself verify).
EXPLAIN_ARTIFACT_DIR = "tests/fixtures/sql/explain"


# frob:ticket T-5339
def _discover_obligation_rule_prefixes() -> frozenset[str]:
    """`_DEFAULT_OBLIGATION_RULE_PREFIXES` plus every `frob.sql._*`
    submodule's own declared `EXPLAIN_OBLIGATION_RULE_PREFIX` (T-5308's
    discovery convention, applied here) -- a submodule with no such
    attribute is silently skipped, matching
    `_discover_websec_hook_modules`'s own "discovery is additive" posture."""
    prefixes = set(_DEFAULT_OBLIGATION_RULE_PREFIXES)
    for module_info in sorted(
        pkgutil.iter_modules(frob.sql.__path__), key=lambda m: m.name
    ):
        if not module_info.name.startswith("_"):
            continue
        dotted = f"{frob.sql.__name__}.{module_info.name}"
        module = import_module(dotted)
        prefix = getattr(module, _HOOK_ATTR_NAME, None)
        if isinstance(prefix, str) and prefix:
            _log.debug(
                "sql_explain_obligation: discovered prefix %r from %s",
                prefix,
                dotted,
            )
            prefixes.add(prefix)
    return frozenset(prefixes)


def _needs_explain_obligation(rule: str, prefixes: frozenset[str]) -> bool:
    """Whether a waived `rule` id falls under the EXPLAIN obligation
    (any discovered prefix is a literal string-prefix match, e.g.
    `Frob_L002`.startswith(`Frob_L`))."""
    return any(rule.startswith(prefix) for prefix in prefixes)


def _has_real_explain_artifact(root: Path, edge: Edge) -> bool:
    """Whether `edge`'s `explain="..."` attribute names a real, existing
    file under `EXPLAIN_ARTIFACT_DIR` -- both "no `explain=` attribute at
    all" and "`explain=` names a file that does not exist / lives outside
    the audited directory" are treated identically (not proof)."""
    value = edge.attrs.get("explain")
    if not value:
        return False
    candidate = (root / value).resolve()
    try:
        artifact_dir = (root / EXPLAIN_ARTIFACT_DIR).resolve()
        candidate.relative_to(artifact_dir)
    except ValueError:
        return False
    return candidate.is_file()


# frob:doc docs/modules/gates.md#sqlexplain001-t-5339
# frob:ticket T-5339
# frob:enforces CHK-GATE-SQLEXPLAIN001
def sql_explain_obligation_gate(
    root: Path, snapshot: GraphSnapshot
) -> tuple[Violation, ...]:
    """SQLEXPLAIN001: every `frob:waive` edge targeting a rule under
    `_discover_obligation_rule_prefixes()` (T-5335's `Frob_L001`-
    `Frob_L004` by default) whose `explain="..."` attribute does not name
    a real artifact file under `EXPLAIN_ARTIFACT_DIR`
    (`_has_real_explain_artifact`) -- a bare `reason="..."` prose waiver,
    with no `explain=` at all, is exactly as unproven as one naming a
    file that does not exist: this obligation's PROVABILITY CONSTRAINT
    (T-0331, reused from INV008's own identical posture) is "a real
    artifact was checked", never "the waiver author asserted one was"."""
    root = Path(root)
    prefixes = _discover_obligation_rule_prefixes()
    violations: list[Violation] = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.WAIVE:
            continue
        if not _needs_explain_obligation(edge.target, prefixes):
            continue
        if _has_real_explain_artifact(root, edge):
            continue
        file, _, line = edge.origin.rpartition(":")
        _log.warning(
            "SQLEXPLAIN001: %s waived at %s with no real EXPLAIN artifact (explain=%r)",
            edge.target,
            edge.origin,
            edge.attrs.get("explain"),
        )
        violations.append(
            Violation(
                rule="SQLEXPLAIN001",
                severity=Severity.ERROR,
                file=file or edge.origin,
                line=int(line) if line.isdigit() else 0,
                message=(
                    f"SQLEXPLAIN001: frob:waive {edge.target} at {edge.src} "
                    f"has no real EXPLAIN ANALYZE artifact -- add "
                    f'explain="{EXPLAIN_ARTIFACT_DIR}/<name>.explain.txt" '
                    "naming a real, tracked artifact file proving the "
                    "waived query's plan was actually checked"
                ),
            )
        )
    return tuple(violations)
