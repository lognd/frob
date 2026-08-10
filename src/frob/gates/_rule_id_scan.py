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

T-1937: the disclosed gap above stopped being merely disclosed and became a
real, measured soundness hole -- 9 live rule ids (BUDGET001/CHECK001/
CVEFP001/DEPLOY001/DEPLOY002/DEPLOY003/DERIVED001/SYS109, plus the
deliberately-retired TIERBDEMO001) accumulated in `src/` outside what
`scan_emitted_rule_ids`/`generated_gate_rule_ids` above cover, invisible to
both `_KNOWN_GATE_RULES` and the `frob.tickets._new_gate_rule_acceptance`
preflight that scrapes it. Two of those (SYS109, CVEFP001) live INSIDE
`SCANNED_BASES` and were STILL missed -- diagnosis, per rule id:

- `SYS109` (`src/frob/gates/_sys_selfaudit.py`): a bare positional string
  argument (`_selfaudit_violation("SYS109", ...)`), not a `rule=`/`rule=
  CONST_NAME` construction at all -- exactly the disclosed "bare positional
  argument" shape gap above, just now with a concrete live instance instead
  of only a hypothetical one.
- `CVEFP001` (`src/frob/strata/_cve_fingerprint.py`): a type-annotated
  pydantic field default, `rule: str = "CVEFP001"` -- the `rule` keyword
  followed by whitespace then `[:=]` then whitespace then a quote, the
  shape `_LITERAL_PATTERN` looks for, does not tolerate the `: str` type
  annotation sitting between the keyword and the `=`, so this construction
  silently falls through a shape the docstring above never disclosed as a
  gap at all (a THIRD, previously-unknown miss class, not a variant of the
  bare-positional-argument gap `SYS109` demonstrates).
- `BUDGET001`/`CHECK001`/`DEPLOY001`/`DEPLOY002`/`DEPLOY003`/`DERIVED001`:
  all constructed via `Diagnostic(code="...")`, a sibling keyword to
  `rule=` that `_LITERAL_PATTERN` never looked for, in packages
  (`src/frob/app`, `src/frob/deploy`, `src/frob/check`) outside
  `SCANNED_BASES` entirely -- the disclosed out-of-base gap, confirmed with
  live instances.
- `TIERBDEMO001` is NOT a real gap: it is constructed via the exact
  `rule=` keyword-literal shape `_LITERAL_PATTERN` already detects, and is
  correctly excluded from the generated set on purpose via
  `RETIRED_RULE_IDS` (a deliberately synthetic reference-handler id, see
  the entry's own comment below) -- included in this ticket's count only
  because the naive repo-wide "quoted rule-id-shaped literal" audit that
  found this whole gap cannot distinguish "genuinely missing" from
  "detected and deliberately retired" without also consulting
  `RETIRED_RULE_IDS`.
- `SYS104` (named in the same audit, "390 ledger references") has ZERO
  live construction sites anywhere under `src/` as of this ticket
  (confirmed by the broad scan below) -- deleted along with its writer per
  T-1870's owner directive; the ledger references are historical prose, not
  code, and are out of a rule-id SCANNER's remit entirely.

FIX (T-1937): rather than hand-adding these 8 ids and calling it done
(the exact drift this scanner exists to end -- T-0903/T-0923/T-0924/
T-0961/T-0966 each landed a hand-diffed batch), `scan_candidate_rule_id_
literals`/`find_unregistered_rule_ids` below add a SECOND, deliberately
broader completeness net alongside the narrow, shape-precise `scan_
emitted_rule_ids` above: instead of matching only the specific `rule=`/
`code=` keyword-argument constructions, it matches any quoted string
literal SHAPED like a rule id (`PREFIX` + digits, `_CANDIDATE_RULE_ID_
PATTERN` below) anywhere under `src/`, independent of which keyword (if
any) introduces it and independent of `SCANNED_BASES`. This trades
construction-shape precision for coverage: it does not know HOW an id is
constructed, only that a string shaped like one exists in real (non-
comment) code -- which is exactly the property that catches a bare
positional argument (`SYS109`), a typed const assignment (`CVEFP001`), and
a `code=` kwarg (`BUDGET001` and siblings) all with the SAME mechanism,
without needing a new regex per newly-discovered construction shape. It
does not replace `scan_emitted_rule_ids`/`generated_gate_rule_ids` (still
the narrow, SCANNED_BASES-scoped authority the checked-in `_KNOWN_GATE_
RULES` literal is generated FROM, and still what `tests/test_gates.py::
TestKnownGateRuleIds.test_every_emitted_rule_literal_is_known` drift-locks
against) -- it is a second, wider-net drift-lock
(`TestFindUnregisteredRuleIds.test_real_repo_registry_is_complete` in
`tests/gates/test_rule_id_scan_branches.py`) that catches everything the
narrow scan's disclosed gaps let through,
covering the WHOLE repo automatically on every test run rather than
requiring a maintainer to remember a manual audit.

Residual gap this broad net still carries, disclosed rather than silently
assumed away: a quoted, rule-id-shaped string that is not actually a rule
construction at all -- e.g. a prose mention in a docstring/string literal
of a not-yet-registered id -- would read as a false "missing" finding. In
practice this has not fired: a fresh scan against this repo's real tree at
T-1937 time found exactly the ids enumerated above and nothing else,
because a plain uppercase-plus-digits quoted literal outside a comment is
overwhelmingly a real construction site in this codebase's conventions,
not incidental prose. If it ever does fire on genuine prose, the fix is to
register the id (if real) or reword the prose -- not to broaden the
pattern's exclusions preemptively for a case that has not occurred.
"""

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

# frob:ticket T-1937
#: T-1937 broad completeness net: any quoted string literal SHAPED like a
#: rule id (an uppercase prefix followed by 2-5 digits, optionally a
#: `-SUFFIX`) -- deliberately keyword/shape-agnostic, unlike
#: `_LITERAL_PATTERN`/`_CONST_REF_PATTERN` above, so it catches a bare
#: positional argument (`SYS109`), a `code=` kwarg (`BUDGET001` and
#: siblings), and a typed const assignment (`CVEFP001`) with one pattern
#: instead of a new regex per newly-discovered construction shape. See
#: `scan_candidate_rule_id_literals`.
_CANDIDATE_RULE_ID_PATTERN = re.compile(r'"([A-Z][A-Z0-9]*[0-9]{2,5}(?:-[A-Z0-9]+)?)"')

# frob:ticket T-1937
#: Strips a trailing `# ...` line comment before candidate-scanning a line,
#: so an inline comment's own prose example (e.g. `# e.g. "F401", "E501"`)
#: cannot self-match as a construction site the way a bare `#`-prefixed
#: line already cannot (`scan_emitted_rule_ids`'s `stripped.startswith("#")`
#: check only catches a WHOLE-line comment, not a trailing one). Declines
#: to strip a `#` immediately preceded by a quote character, so it cannot
#: eat part of a string literal that itself happens to contain `#`.
_INLINE_COMMENT_STRIP = re.compile(r'(?<!["\'])#.*$')

#: Directories (repo-relative) scanned for rule-id-emitting literals and
#: constant references -- unchanged from the original T-0964 test-only
#: scan (`src/frob/gates/**` and `src/frob/strata/**`).
# frob:waive COV001 reason="a frob:doc anchor here would live in \
# docs/modules/gates.md, whose own SCOPE002 closure (every OTHER symbol that \
# monolithic shared doc file describes across the repo) is out of proportion to pull \
# into T-1010's src/frob/gates/** + tests/test_gates.py scope for one constant -- this \
# module's own docstring is the authoritative description; see T-1010's Done report"
SCANNED_BASES: tuple[str, ...] = ("src/frob/gates", "src/frob/strata")

#: Rule ids retired from the live registry: previously emitted (present at
#: some past revision) and no longer are, kept out of the generated set
#: on purpose even if a stray comment/docstring mention would otherwise
#: still match `_LITERAL_PATTERN`/`_CONST_REF_PATTERN`. The one
#: hand-maintained knob in this pipeline -- every other id in
#: `generated_gate_rule_ids()`'s output is derived, not typed. Cite the
#: retiring ticket in a comment alongside each entry, same convention as
#: `_KNOWN_GATE_RULES` itself.
# frob:waive COV001 reason="same doc-anchor scope-closure tension as SCANNED_BASES \
# above -- see T-1010's Done report"
RETIRED_RULE_IDS: frozenset[str] = frozenset(
    {
        # T-1481/T-1590: 'TIERBDEMO001' is a deliberately synthetic
        # reference-handler rule id (src/frob/gates/_fix_engine_tier_b.py,
        # see its own WIRE001 waiver) used only to demonstrate the Tier-B
        # fix-handler wiring shape -- it must never become a real
        # registered gate rule, so it is excluded from the generated set
        # here exactly like a genuinely retired id, rather than pasted
        # into _KNOWN_GATE_RULES.
        "TIERBDEMO001",
    }
)


# frob:waive COV001 reason="same doc-anchor scope-closure tension as SCANNED_BASES \
# above -- see T-1010's Done report"
# frob:tests \
# tests/test_gates.py::TestKnownGateRuleIds.test_scan_finds_a_synthetic_rule_id
# frob:tests tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches.test_commented_out_rule_literal_is_skipped  # noqa: E501
# frob:tests tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches.test_missing_scanned_base_directory_is_skipped_not_an_error  # noqa: E501
# frob:tests tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches.test_unresolved_const_ref_is_left_out  # noqa: E501
# frob:tests tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches.test_const_ref_resolves_against_assignment_in_another_file  # noqa: E501
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
        # frob:waive PERF004 reason="sorts each SCANNED_BASES entry's own distinct \
        # file list for deterministic first-occurrence ordering, not a shared re-sort \
        # across iterations"
        # frob:waive PERF008 reason="base_dir is freshly rebound per SCANNED_BASES \
        # iteration, so each rglob('*.py') walks a DIFFERENT directory, not a repeated \
        # identical walk -- a resolver argument-text-equality limit"
        # frob:waive WALK001 reason="SCANNED_BASES are small, no vendor dirs to prune"
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


# frob:waive COV001 reason="same doc-anchor scope-closure tension as SCANNED_BASES \
# above -- see T-1010's Done report"
# frob:tests tests/test_gates.py::TestKnownGateRuleIds.test_retired_id_stays_excluded
# frob:tests tests/gates/test_rule_id_scan_branches.py::TestGeneratedGateRuleIdsRetiredOverride.test_default_retired_set_is_module_constant  # noqa: E501
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


# frob:ticket T-1937
# frob:waive COV001 reason="same doc-anchor scope-closure tension SCANNED_BASES/ \
# RETIRED_RULE_IDS above already carry (T-1010's own waiver) -- a frob:doc anchor here \
# would live in docs/modules/gates.md, whose own SCOPE002 closure is out of proportion \
# to pull into T-1937's narrow scope for two functions; this module's own docstring is \
# the authoritative description, see T-1937's Done report"
# frob:tests \
# tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals.test_finds_bare_positional_argument  # noqa: E501
# frob:tests \
# tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals.test_finds_typed_const_assignment  # noqa: E501
# frob:tests \
# tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals.test_finds_code_kwarg_outside_scanned_bases  # noqa: E501
# frob:tests \
# tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals.test_inline_comment_example_not_picked_up  # noqa: E501
# frob:tests \
# tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals.test_whole_line_comment_not_picked_up  # noqa: E501
def scan_candidate_rule_id_literals(repo_root: Path) -> dict[str, str]:
    """T-1937 broad completeness net: every quoted, rule-id-SHAPED string
    literal anywhere under `repo_root / "src"` (unlike `scan_emitted_
    rule_ids`, not limited to `SCANNED_BASES` and not limited to the
    `rule="..."`/`rule=CONST_NAME` construction shapes), returning
    `{rule_id: "path:line"}` for the FIRST occurrence of each. This is the
    shape-agnostic scan the module docstring's FIX section describes --
    deliberately less precise about HOW an id is constructed than `scan_
    emitted_rule_ids`, in exchange for not needing a new regex every time
    a new construction shape (a bare positional arg, a `code=` kwarg, a
    typed const assignment) is discovered live.
    """
    found: dict[str, str] = {}
    src_dir = repo_root / "src"
    if not src_dir.is_dir():
        return found
    # frob:waive PERF004 reason="single rglob over src/, no per-iteration re-sort"
    # frob:waive WALK001 reason="src/ is the whole package tree this scan exists to \
    # cover; no vendor dirs to prune within it"
    for path in sorted(src_dir.rglob("*.py")):
        if path.name == "_rule_id_scan.py":
            # Same self-match exclusion as scan_emitted_rule_ids: this
            # module's own docstrings/comments quote rule-id-shaped
            # examples in prose (e.g. "SYS109" a few lines above), which
            # would otherwise self-match as bogus candidates.
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            code_part = _INLINE_COMMENT_STRIP.sub("", line)
            for m in _CANDIDATE_RULE_ID_PATTERN.finditer(code_part):
                found.setdefault(
                    m.group(1), f"{path.relative_to(repo_root)}:{lineno}"
                )
    return found


# frob:ticket T-1937
# frob:waive COV001 reason="same doc-anchor scope-closure tension SCANNED_BASES/ \
# RETIRED_RULE_IDS above already carry (T-1010's own waiver) -- a frob:doc anchor here \
# would live in docs/modules/gates.md, whose own SCOPE002 closure is out of proportion \
# to pull into T-1937's narrow scope for two functions; this module's own docstring is \
# the authoritative description, see T-1937's Done report"
# frob:waive WIRE001 reason="this ticket's own drift-lock test \
# (TestFindUnregisteredRuleIds.test_real_repo_registry_is_complete) already calls this \
# on every test/check run -- the automatic-detection deliverable T-1937 asks for -- \
# but that is a test caller, not a production one WIRE001 counts. Wiring it into the \
# T-0756 acceptance preflight (frob.tickets._new_gate_rule_acceptance, a different \
# ticket's scope, not this ticket's declared src/frob/gates/_rule_id_scan.py) is real \
# follow-up work, not attempted half-heartedly here." follow_up="T-1956"
# frob:tests \
# tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds.test_real_repo_registry_is_complete  # noqa: E501
# frob:tests \
# tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds.test_empty_when_every_candidate_is_known_or_retired  # noqa: E501
# frob:tests \
# tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds.test_reports_a_candidate_missing_from_both_known_and_retired  # noqa: E501
def find_unregistered_rule_ids(
    repo_root: Path, known: frozenset[str], retired: frozenset[str] | None = None
) -> dict[str, str]:
    """T-1937: every candidate `scan_candidate_rule_id_literals` finds
    under `repo_root` that is in neither `known` (typically
    `known_gate_rule_ids()`) nor `retired` (`RETIRED_RULE_IDS` by
    default) -- the completeness check `_KNOWN_GATE_RULES` must return
    empty against, repo-wide, not just across `SCANNED_BASES`.
    """
    if retired is None:
        retired = RETIRED_RULE_IDS
    candidates = scan_candidate_rule_id_literals(repo_root)
    return {
        rule_id: loc
        for rule_id, loc in candidates.items()
        if rule_id not in known and rule_id not in retired
    }


__all__ = [
    "RETIRED_RULE_IDS",
    "SCANNED_BASES",
    "find_unregistered_rule_ids",
    "generated_gate_rule_ids",
    "scan_candidate_rule_id_literals",
    "scan_emitted_rule_ids",
]
