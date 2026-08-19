## Done report

Implements the coordinator-authorized A2 + A4 from this ticket's own
attachment (01-class-a-options-and-measured-costs-t-2377-survey.md).
A3 and A5 were explicitly not authorized and are not here.

A2 -- THE SUBSCRIPT RULE NAMES THE TYPE IT ACTUALLY KNOWS. An
unresolved-shape subscript contributed `KeyError` outright. Measured
across the 41 findings that default produced, 30 reach an integer-literal
index -- sequence indexing, where the real risk is `IndexError` -- and
only 9 reach a string-literal mapping key. The default was therefore
wrong in both directions at once: it named a type those sites cannot
raise AND never reported the one they can. It now contributes
`LookupError`, the common parent, which is exactly what a model with no
type information knows.

Measured cost of A2: ZERO findings (47 before, 47 after). This is the
number I got wrong in my first analysis -- I predicted A2 would be
"strictly noisier" because `except KeyError:` does not discharge a raised
`LookupError`. It does not materialise, because a site that catches
`KeyError` was never flagged in the first place; the predicted noise
lands only on sites that already pass.

A4 -- SPLIT BY PROVENANCE, NOT BY TYPE NAME. A named leak whose ONLY
source is the subscript rule is now EXHAUST004 rather than EXHAUST002 --
the same confidence split T-1402 made between EXHAUST001 and EXHAUST003
for the unresolved-callee case, for the same reason: reporting a resolver
coverage limit at the same volume and severity as a confirmed defect
converts a tool limitation into developer work, and the cheapest way to
satisfy it is the blanket `except Exception:` this family exists to
prevent.

The split had to be a PROVENANCE test, never a match on the type text
(this repo's own token-not-lexical directive). `compute_may_raise` runs a
second, identical fixpoint with only the subscript rule suppressed and
reports the difference as `FunctionMayRaise.subscript_derived`. Running
the whole resolution twice, rather than tagging provenance through the
fixpoint, was deliberate: the two passes are literally the same code
path, so they cannot drift apart as the resolver grows, and transitivity
comes free -- a caller that never indexes anything but calls something
that does is correctly subscript-derived, verified by test. A type
reachable by BOTH a subscript and another route keeps its
higher-confidence EXHAUST002 classification, and one function can emit
both rules at once rather than being demoted wholesale.

MEASURED, unbudgeted, `FROB_NO_GATE_CACHE=1`:
  EXHAUST002   47 -> 8
  EXHAUST004    0 -> 68
  EXHAUST003  141 -> 141 (untouched; held for the user's decision)

TWO CONSEQUENCES I WANT ON THE RECORD RATHER THAN BURIED.

(1) EXHAUST004's 68 is not the 39 the option table predicted. Minting a
new rule id means an existing `frob:waive EXHAUST002` no longer suppresses
a finding that has been re-coded, so 26 previously-waived findings became
visible under the new id (waived count 138 -> 112). Verified this does NOT
red the floor: EXHAUST004 is WARN, and an orphaned EXHAUST002 waiver does
not become a WAIVE002 error, since that id still matches elsewhere --
checked directly, zero WAIVE findings after the split. Retargeting those
waiver comments is mechanical follow-up, exactly as T-1402 retargeted its
own EXHAUST001 comments to EXHAUST003; it is called out in the gate
catalog so the next reader is not surprised.

(2) All 8 remaining EXHAUST002 findings are ONE class -- a guard
predicate the resolver cannot see (`if not entry.name.isdigit(): continue`
before `int(entry.name)`). Filed as T-2568 rather than fixed here,
because it needs guard-to-call flow, not a table edit. It is now the only
thing standing between EXHAUST002 and T-2377's promotion decision.

RULE ID AS AN API DECISION. EXHAUST004 is documented in
docs/modules/gates.md with an explicit statement of what it covers versus
EXHAUST002 (confirmed source vs. subscript-only), the provenance
mechanism, and the waiver consequence above. It is registered in
`_KNOWN_GATE_RULES` so `frob:waive EXHAUST004` binds, and added to that
list's `frob:enumerates` member set so DOCENUM001 stays clean.

Tests: 308 collected / 0 failed in tests/unit/test_arch.py; 9 collected /
0 failed for TestExhaustiveHandlingGate. Two pre-existing resolver tests
asserted the old `KeyError` contribution and were updated in place with
a comment recording why the expected value changed.

SCOPE NOTE: `src/frob/gates/_exhaustive_handling.py` and
`docs/modules/gates.md` were moved here from T-2377 for the duration (A4
edits both) and should return to T-2377 for its promotion work.
`src/frob/gates/_waive.py` and `tests/test_gates.py` were added for the
new rule id's allowlist entry and its gate-level test.

DISCLOSED: a `ruff format` pass had reformatted three unrelated,
recently-landed test classes in tests/test_gates.py, costing 10 COV002
errors for changes that were not this ticket's. Reverted; only my own
lines are hand-wrapped. Final unscoped gates-fast error count is 35 with
none in any file this ticket touched.

### Changed
```
 docs/modules/arch.md                   |  27 +++++++
 docs/modules/gates.md                  |  50 +++++++++++-
 frob.lock                              |  20 ++++-
 src/frob/arch/_mayraise.py             |  60 ++++++++++++---
 src/frob/gates/_exhaustive_handling.py |  53 ++++++++++++-
 src/frob/gates/_waive.py               |  13 +++-
 tests/test_gates.py                    |  79 +++++++++++++++++++
 tests/unit/test_arch.py                | 135 +++++++++++++++++++++++++++++++--
 tickets/T-2377/ticket.md               |  23 +++++-
 tickets/T-2543/ticket.md               |  43 ++++++++++-
 tickets/T-draft-e816f9da/ticket.md     |  94 +++++++++++++++++++++++
 11 files changed, 569 insertions(+), 28 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestBuiltinRaiserPrecision::test_int_does_not_contribute_type_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestBuiltinRaiserPrecision::test_getattr_with_default_raises_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestBuiltinRaiserPrecision::test_next_with_default_raises_no_stop_iteration` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSubscriptProvenance::test_subscript_raises_lookup_error_not_key_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSubscriptProvenance::test_subscript_provenance_propagates_through_callees` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSubscriptProvenance::test_type_with_a_confirmed_source_is_not_subscript_derived` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestSubscriptProvenance::test_slice_only_function_has_no_subscript_provenance` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestExhaustiveHandlingGate::test_subscript_only_leak_fires_exhaust004_not_exhaust002` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestExhaustiveHandlingGate::test_confirmed_and_subscript_leaks_split_across_both_rules` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2556/ticket.md, DOC006@tickets/T-2561/ticket.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2377/src/frob/app/ticket_runner/_verify.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2543, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
