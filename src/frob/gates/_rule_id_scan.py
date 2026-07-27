"""T-1010: the static rule-id scanner `_KNOWN_GATE_RULES`
(`frob.gates.__init__`) is generated-and-verified against, promoted here
from `tests/test_gates.py` so it is importable production code instead of
test-only logic (the T-0964 constant+literal scan class).

Root cause this closes: the registry (`_KNOWN_GATE_RULES`) drifted
repeatedly by hand (T-0903/T-0923/T-0924/T-0961/T-0966 each landed a batch
of ids someone had to manually diff in after the drift-lock test failed).
Inverting the relationship -- this scan is now the AUTHORITY for which
`rule="..."`/`rule=CONST_NAME` ids are live, and `_KNOWN_GATE_RULES`'s
literal is the GENERATED artifact kept in sync with it -- means adding a
missing entry is "copy what `generated_gate_rule_ids()` reports", not
"manually reconstruct the diff by inspection".

DESIGN CHOICE (checked-in generated literal, not a runtime cached scan):
`_KNOWN_GATE_RULES` stays a plain `frozenset({...})` literal in
`frob.gates.__init__` rather than becoming `= generated_gate_rule_ids(...)`
computed at import, for two concrete reasons, not just habit:

1. `frob.tickets._new_gate_rule_acceptance` reads that literal's SOURCE
   TEXT (via `git show <rev>:...` + a regex over the frozenset syntax, not
   via import) to detect newly-added rule ids for its T-0756 close/land
   acceptance-policy preflight. A computed expression has no such literal
   text to scrape -- replacing it would silently blind that consumer
   forever, in a file this ticket's scope does not touch to compensate.
2. Gate startup stays exactly as cheap as before: importing
   `frob.gates` still costs one frozenset literal parse, zero filesystem
   scanning. A cached-scan design would add an `rglob` + per-line regex
   pass (over `SCANNED_BASES`) to the first gate invocation of every
   process -- cheap in isolation, but paid by every `frob check`/`frob
   test` invocation for a set that changes on the order of "a few times a
   month".

So generation is a deliberate, occasional action ("when generation runs"),
not an implicit one on every import: `generated_gate_rule_ids()` is called
by a maintainer (or a future `make`/CLI target, not built here) to produce
the current live id set, which is then pasted into the `_KNOWN_GATE_RULES`
literal; `tests/test_gates.py::TestKnownGateRuleIds` re-verifies the
checked-in literal against a fresh scan every test run, so a maintainer who
adds a rule and forgets the paste step fails loud immediately, exactly as
the T-0964 drift-lock always has -- the difference is the scan itself no
longer lives only in the test file.

DISCLOSED RESIDUAL GAP (v1, matching this repo's usual disclosed-not-
silently-dropped posture -- see `frob.tickets._new_gate_rule_acceptance`'s
own module docstring for the same pattern): this scan recognizes only the
`rule="RULE_ID"` / `rule=CONST_NAME` construction shapes (the T-0964
class). Rule ids constructed via a bare positional argument or a
dict-literal value (`frob.gates._secrets`'s `_pat(name, "SEC001", ...)`
tuples, `frob.gates._arch`'s category-to-id dict, `frob.gates.
_registry_exhaustiveness`'s bare `"REG001"` returns) are NOT detected here,
nor are ids whose home module lives outside `SCANNED_BASES` entirely
(`DUP001`/`DUP002` in `src/frob/dup`, `PERF001`-`PERF009` in `src/frob/
perf`). Those ids remain hand-added to `_KNOWN_GATE_RULES` exactly as
before this ticket; extending detection to those shapes is real work this
ticket's scope (`src/frob/gates/**`, `tests/test_gates.py`) does not cover
and is left for a follow-up ticket rather than attempted half-heartedly
here.
"""
# frob:waive INV006 reason="module-docstring exclusivity-vocabulary hits are \
# source-level design-rationale prose describing this file's own already-implemented \
# scan-shape scope and startup-cost trade-off, verifiable by reading the code it \
# annotates -- not a separate cross-module contract needing its own tracked invariant, \
# same calibration posture as frob.tickets._new_gate_rule_acceptance's own T-0756 \
# INV006 waiver"

from __future__ import annotations

import re
from pathlib import Path

#: `rule="RULE_ID"` / `"rule": "RULE_ID"` inline string literal shape.
_LITERAL_PATTERN = re.compile(r'rule\s*[:=]\s*"([A-Z][A-Z0-9_-]*)"')

#: A module-level constant assignment shaped like `NAME = "RULE_ID"` --
#: resolved below so `rule=NAME` kwargs are checked identically to inline
#: `rule="..."` literals (the `REL_*`/`SYS_*` convention `src/frob/
#: strata/**` uses instead of inline literals, T-0964).
_CONST_ASSIGN_PATTERN = re.compile(r'^([A-Z][A-Z0-9_]*)\s*=\s*"([A-Z][A-Z0-9_-]*)"\s*$')

#: A `rule=NAME` kwarg where NAME is a bare identifier (not a string
#: literal), resolved against `_CONST_ASSIGN_PATTERN` matches collected
#: across the same file set.
_CONST_REF_PATTERN = re.compile(r"rule\s*=\s*([A-Z][A-Z0-9_]*)\b")

#: Directories (repo-relative) scanned for rule-id-emitting literals and
#: constant references -- unchanged from the original T-0964 test-only
#: scan (`src/frob/gates/**` and `src/frob/strata/**`).
# frob:waive COV001 reason="a frob:doc anchor here would live in \
# docs/modules/gates.md, whose own SCOPE002 closure (every OTHER symbol that \
# monolithic shared doc file describes across the repo) is out of proportion \
# to pull into T-1010's src/frob/gates/** + tests/test_gates.py scope for one \
# constant -- this module's own docstring is the authoritative description; \
# see T-1010's Done report"
SCANNED_BASES: tuple[str, ...] = ("src/frob/gates", "src/frob/strata")

#: Rule ids retired from the live registry: previously emitted (present at
#: some past revision) and no longer are, kept out of the generated set
#: on purpose even if a stray comment/docstring mention would otherwise
#: still match `_LITERAL_PATTERN`/`_CONST_REF_PATTERN`. The one
#: hand-maintained knob in this pipeline -- every other id in
#: `generated_gate_rule_ids()`'s output is derived, not typed. Cite the
#: retiring ticket in a comment alongside each entry, same convention as
#: `_KNOWN_GATE_RULES` itself.
# frob:waive COV001 reason="same doc-anchor scope-closure tension as \
# SCANNED_BASES above -- see T-1010's Done report"
RETIRED_RULE_IDS: frozenset[str] = frozenset()


# frob:waive COV001 reason="same doc-anchor scope-closure tension as \
# SCANNED_BASES above -- see T-1010's Done report"
# frob:tests \
# tests/test_gates.py::TestKnownGateRuleIds.test_scan_finds_a_synthetic_rule_id
def scan_emitted_rule_ids(repo_root: Path) -> dict[str, str]:
    """Statically enumerate every rule id constructed under
    `SCANNED_BASES` beneath `repo_root` (inline `rule="..."` literal, or
    `rule=CONST_NAME` resolved against a module-level `CONST_NAME =
    "..."` assignment), returning `{rule_id: "path:line"}` for the FIRST
    occurrence of each -- the T-0964 scan class, promoted from
    `tests/test_gates.py` so `generated_gate_rule_ids` (and any future
    caller) can invoke it without duplicating the regex pair by hand.
    """
    found: dict[str, str] = {}
    const_values: dict[str, str] = {}
    const_refs: dict[str, str] = {}
    for base in SCANNED_BASES:
        base_dir = repo_root / base
        if not base_dir.is_dir():
            continue
        # frob:waive PERF004 reason="sorts each SCANNED_BASES entry's own \
        # distinct file list for deterministic first-occurrence ordering, \
        # not a shared re-sort across iterations"
        for path in sorted(base_dir.rglob("*.py")):
            if path.name == "_rule_id_scan.py":
                # This module's own docstrings/comments describe the
                # `rule="..."`/`rule=CONST_NAME` shapes in prose, which
                # would otherwise self-match as bogus rule ids (e.g.
                # `"RULE_ID"` in the module docstring) -- it emits no
                # `Violation`s itself and is excluded from its own scan.
                continue
            for lineno, line in enumerate(path.read_text().splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for m in _LITERAL_PATTERN.finditer(line):
                    found.setdefault(
                        m.group(1), f"{path.relative_to(repo_root)}:{lineno}"
                    )
                assign_m = _CONST_ASSIGN_PATTERN.match(stripped)
                if assign_m:
                    const_values.setdefault(assign_m.group(1), assign_m.group(2))
                ref_m = _CONST_REF_PATTERN.search(line)
                if ref_m:
                    const_refs.setdefault(
                        ref_m.group(1), f"{path.relative_to(repo_root)}:{lineno}"
                    )

    # Resolve every `rule=CONST_NAME` reference to the constant's assigned
    # string value and fold it into `found` -- a constant referenced but
    # never assigned in the scanned tree is left unresolved (nothing
    # statically checkable) rather than raising.
    for name, loc in const_refs.items():
        value = const_values.get(name)
        if value is not None:
            found.setdefault(value, loc)

    return found


# frob:waive COV001 reason="same doc-anchor scope-closure tension as \
# SCANNED_BASES above -- see T-1010's Done report"
# frob:tests tests/test_gates.py::TestKnownGateRuleIds.test_retired_id_stays_excluded
def generated_gate_rule_ids(
    repo_root: Path, retired: frozenset[str] | None = None
) -> frozenset[str]:
    """The live, generated rule-id set `_KNOWN_GATE_RULES` must be kept in
    sync with: every id `scan_emitted_rule_ids` finds beneath `repo_root`,
    minus `retired` (`RETIRED_RULE_IDS` by default -- overridable so tests
    can inject a synthetic retired id without mutating module state).
    """
    if retired is None:
        retired = RETIRED_RULE_IDS
    return frozenset(scan_emitted_rule_ids(repo_root)) - retired


__all__ = [
    "RETIRED_RULE_IDS",
    "SCANNED_BASES",
    "generated_gate_rule_ids",
    "scan_emitted_rule_ids",
]
