## Done report

Changed:
- src/frob/gates/_wire.py::_wire_reach_patterns

Root cause: `_wire_reach_patterns`'s `call_pattern` for a symbol's reach
scan used a negative lookbehind that excludes ANY match preceded by a
dot (`(?<![A-Za-z0-9_.])`). Correct for a bare module-level function/
class/const/type (a dot-preceded `short(` there belongs to someone
else's attribute of the same name, not a real call to this symbol) but
wrong for a `METHOD` record: a classmethod/staticmethod's ONLY legal
Python call shape is dotted-qualified (`ClassName.method(...)` or
`instance.method(...)`), so the exclusion made every genuine, working
call site invisible to WIRE001's reach scan. Confirmed the exact T-2530
incident: `SealedGrantSet.from_root_node`, a real classmethod called
exactly once at its only sanctioned call site, was flagged unreached and
forced a `frob:waive` for code that was not actually unwired.

This module is DELIBERATELY a lexical text scan, not a resolved
call-graph match (its own docstring: "broader recall over precision" --
a false "reached" costs nothing, a false "unreached" wrongly blocks a
build). The fix stays inside that same documented design rather than
rewriting the gate to a symbol-resolved scan (a much larger change, and
one the module's own architecture note argues against for this specific
check): for `kind == SymbolKind.METHOD` only (this codebase's
`SymbolKind` has no separate staticmethod/classmethod bucket -- both
collapse into `METHOD`), `call_pattern` now ALSO matches a
dotted-qualified call (`(?:Ident\.)+short\s*\(`), guarded by its own
leading negative lookbehind so a same-named different symbol embedded in
a longer identifier still does not match. Bare function/class/const/type
records are unaffected -- the widening is scoped to method records only.

Evidence:
- tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_classmethod_called_dotted_qualified_is_not_flagged
  (accepts 0) -- FAILED_AT_PARENT confirmed at c2c247773 (test-only
  commit, fix not yet applied) via `frob ticket evidence --designate-repro`.
- tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_genuinely_unwired_method_still_flagged
  (accepts 1) -- positive control: a method with no caller anywhere,
  bare or dotted, still fires; the fix does not widen into a blanket
  method exemption.
- tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_similarly_named_dotted_call_does_not_false_positive_reach
  (accepts 1) -- positive control, other direction: a DIFFERENT method
  whose short name is a superstring of the target's is not counted as a
  reach for the target (the widened pattern is not a bare substring
  match).

Also manually verified (guard temporarily removed, restored after) that
all 3 tests pass WITH the fix and the first one fails WITHOUT it -- see
commit history (c2c247773 test-only, d741025b9 fix).

Regression runs (all passed):
- tests/unit/test_wire001_dotted_method_call.py -- 3 passed
- tests/unit/test_wire_autouse_fixture.py,
  tests/unit/test_wire001_pydantic_validator_rescue.py,
  tests/unit/gates/test_wire001_cli_dest_semantic.py -- 15 passed total
- tests/test_gates.py -k Wire (excluding
  test_new_cli_dest_present_in_config_external_is_not_flagged, a
  PRE-EXISTING failure on main unrelated to this change -- confirmed by
  temporarily reverting this ticket's fix and re-running: it fails
  identically with or without the fix) -- 33 passed, 0 failed.

Gates: land dry-run reached the Done-report gate cleanly after merging
current main (T-2374's DOC004/DOC006 promotion included); no
scope/leakage refusal. Merged current main before landing.

### Changed
```
 src/frob/gates/_wire.py                       |  23 +++++
 tests/unit/test_wire001_dotted_method_call.py | 140 ++++++++++++++++++++++++++
 tickets/T-2532/ticket.md                      |  21 +++-
 3 files changed, 182 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_classmethod_called_dotted_qualified_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_genuinely_unwired_method_still_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_similarly_named_dotted_call_does_not_false_positive_reach` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2561/ticket.md, DOC006@tickets/T-2565/ticket.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2532/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2532/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2532, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
