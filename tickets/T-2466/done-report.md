## Done report

Changed:
  src/frob/gates/_detector_scope.py (new) -- `DETECTOR_PACKAGE_ROOTS`,
    `is_detector_package_file`: the ONE shared "which packages can
    contain a detector" declaration, MEASURED via `git grep -c
    "Violation("` per candidate package (gates/vet/strata/check all
    construct Violation(...); arch/ measured zero and is excluded, not
    guessed), intended for PORT001's own T-2405 widening to import
    rather than re-hardcode.
  src/frob/gates/_lexical_selfcheck.py -- `_tracked_gate_files` now
    filters via `is_detector_package_file` instead of a hardcoded
    `src/frob/gates/` prefix; `_calls_re_decision` renamed `_calls_
    lexical_decision`, widened to also trigger on a non-ElementTree
    `.find(` call (`_FIND_TRIGGER_EXCLUDED_BASE_SUFFIXES` excludes the
    one measured `_el`/`_element`-named ElementTree false-positive
    shape); `lexical_selfcheck_gate` now logs its scanned scope
    alongside its count on every call (PORT001's T-2388 convention,
    copied exactly).
  tests/unit/gates/test_lexical_selfcheck.py -- 3 new tests (must-now-
    fire on a vet/-shaped `.find(` detector, must-still-pass on an
    ElementTree `.find(` call, must-report-scope via caplog); the
    "every known module stays clean" test renamed and changed from a
    blind `== []` to an explicit, named, ticket-tracked backlog set
    (see below) so a genuinely new offender elsewhere in the widened
    scope still fails loudly.
  tests/unit/gates/test_detector_scope.py (new) -- 4 tests for the new
    shared module.
  docs/modules/gates.md#lexcheck001-t-2344 -- rewritten to describe the
    widened scope/trigger, the scope-disclosure log line, and both open
    backlogs (WIRE001/T-2348, pre-existing; the new _supplychain.py
    backlog this ticket's own widening surfaced).

Evidence:
  tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_vet_needle_matcher_shape_is_flagged  (accepts 0)
  tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_allowlisted_function_is_silent  (accepts 1)
  tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_semantic_function_with_incidental_regex_is_silent  (accepts 1)
  tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_elementtree_find_is_not_a_trigger  (accepts 1)
  tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_every_known_detector_package_module_stays_clean  (accepts 1)
  tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_non_gate_code_never_scanned  (accepts 1)
  tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_scans_scope_is_disclosed_in_log  (accepts 2)
  tests/unit/gates/test_detector_scope.py::TestDetectorScope::* (4 tests, accepts 0)
  `tests/unit/gates/test_lexical_selfcheck.py` + `test_detector_scope.py`:
  12 collected, 0 failed. `tests/unit/gates/` (full dir): 105 collected,
  0 failed.

Controls (this ticket's own three acceptance criteria):
  [0] must-now-fire: a `src/frob/vet/`-shaped `.find(`-based needle
      matcher building a symref-less Violation is now caught -- was NOT
      caught before this ticket (wrong package AND wrong trigger,
      confirmed by reverting either change alone during development).
  [1] must-still-pass: existing `_ALLOWLIST` entries stay silent
      (unchanged, not touched); the new ElementTree `.find(` exclusion
      is itself covered by its own must-still-pass test.
  [2] must-report-scope: `lexical_selfcheck_gate` logs
      "scanned N tracked file(s) under check/, gates/, strata/, vet/
      ONLY (not repo-wide -- see frob.gates._detector_scope.
      DETECTOR_PACKAGE_ROOTS), M violation(s)" on every call, verified
      via caplog.

MEASURED FALLOUT, disclosed rather than hidden behind a loosened
assertion: widening the scan surfaced 5 REAL, previously-invisible
LEXCHECK001 findings in `src/frob/vet/_supplychain.py` (5 functions
deciding from `re.search`/`re.match` over TOML/JSON/CI-workflow manifest
text with no `symref=`) -- confirmed via `frob check --only gates-fast
--ticket T-2466 --json`, exactly the 5 findings my own test's named
backlog set expects, no more, no fewer. This adds 5 to the error floor
once landed. Filed as T-2469 (renumbers at land) rather than
fixed inline (out of this ticket's declared scope) or silently
allowlisted -- `_lexical_selfcheck`'s own test names the backlog
explicitly by (file, function) so it cannot mask a different, new
offender, and the follow-up ticket's own body tells whoever picks it up
exactly which one line in this test file to shrink back to `== []`.

Coordination decision (T-2405, PORT001's own widening, not started by
anyone yet at T-2466 time -- checked via `frob ticket show T-2405` and
`git worktree list`): built the shared `DETECTOR_PACKAGE_ROOTS`
declaration now, in THIS ticket, per the coordinator's own "consider
whether both meta-checks should read ONE shared declaration" prompt --
decided yes, since T-2405's own body already lists `strata/`/`check/`
as widening candidates matching what T-2466 independently measured, and
two independently-authored scopes for the identical question is the
exact drift risk called out. T-2405 is expected to `from frob.gates.
_detector_scope import DETECTOR_PACKAGE_ROOTS` (or `is_detector_package_
file`) rather than hardcode its own tuple; left a note to that effect in
both the module docstring and `docs/modules/gates.md`. Did NOT touch
`_port_selfcheck.py` itself (out of T-2466's declared scope, and T-2405
is a separate ticket/kind=feature with its own acceptance criteria) --
only built the shared piece for it to consume.

LEXCHECK001 scanned-scope numbers, before/after (T-2466's own measured
before/after, `frob check --only gates-fast --ticket T-2466`):
  before (this ticket's investigation, T-2457 Done report): 0 findings
    against `src/frob/gates/**` alone (211-vs-however-many-were-gates-
    only files -- the narrower scan literally could not see vet/).
  after: 211 tracked files scanned across
    check/+gates/+strata/+vet/, 5 findings (all in the disclosed
    _supplychain.py backlog, all filed).

Gates: `frob check --only lint --ticket T-2466` -- 0 errors/warnings on
every file this ticket touched (checked precisely, `--json` +
per-file filter, not a grep-based floor count). `frob check --land-
parity` -- timed out under contention (`ticket land: land-parity
unscoped post-land sweep timed out after 360s -- skipping the sweep`),
re-run not attempted a second time given the same contention risk;
relying on the scoped `--only lint`/`--only gates-fast --ticket T-2466`
runs above plus the full `tests/unit/gates/` suite instead.

### Changed
```
 tickets/T-2466/ticket.md           | 77 ++++++++++++++++++++++++++++++++++++--
 tickets/T-2469/ticket.md | 74 ++++++++++++++++++++++++++++++++++++
 2 files changed, 147 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_vet_needle_matcher_shape_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_allowlisted_function_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_semantic_function_with_incidental_regex_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_elementtree_find_is_not_a_trigger` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_every_known_detector_package_module_stays_clean` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_non_gate_code_never_scanned` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_scans_scope_is_disclosed_in_log` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_detector_scope.py::TestDetectorScope::test_gates_vet_strata_check_are_members` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_detector_scope.py::TestDetectorScope::test_arch_is_not_a_member` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_detector_scope.py::TestDetectorScope::test_unrelated_package_is_not_a_member` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_detector_scope.py::TestDetectorScope::test_roots_are_sorted_and_slash_terminated` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2466/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2466/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2466/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2466/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2466/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2466, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py
