---
id: T-2193
title: 'Evidence discipline only proves the bug existed, never that the fix kept the
  capability: --check-repro verifies a test FAILED at parent, so a fix that disables
  the feature entirely passes every gate'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_mutation_evidence.py
- tests/test_gates_mutation_evidence.py
- docs/modules/tickets-landing.md
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_mutation_evidence.py
  reason: 'T-2193: evidence tests for the new BUG003 must_still_pass_violations function
    live in this module''s existing test file'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'T-2193: BUG003 must_still_pass_violations needs a frob:doc edge, new public
    symbol in this ticket''s sole scoped source file'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'T-2193: BUG003 must be registered in _KNOWN_GATE_RULES (T-1937) or the
    ticket cannot close'
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_gates_mutation_evidence.py::TestMustStillPassIntegration::test_reconstructed_over_narrowed_matcher_fails_the_control
- tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_fails_at_fix_is_error_violation
- tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_never_passed_at_parent_is_error_violation
- tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_passes_at_both_no_violation
- tests/test_gates_mutation_evidence.py::TestMustStillPassControls::test_multiple_directives_extracted
designated_repro_test: null
acceptance:
- text: THREE measured instances this session, all of which passed every existing
    gate. (1) T-2156 narrowed cross-file symbol resolution to import-verified candidates;
    the primitive it depends on, resolve_local_import, returns None for every intra-repo
    import form this codebase uses, so the fix accepts NO cross-file candidate at
    all. Certified by two verify-explain queries, one going UNATTRIBUTED and one attributing
    via a SAME-FILE path -- both outcomes are exactly what a disabled capability produces.
    (2) T-2177's scope-plausibility check warns on a wildly unrelated file but NOT
    on any of the three real mis-scopings it was built for. (3) frob cycle finds a
    planted cycle in a top-level layout and misses the identical one in src-layout,
    so its clean verdict on frob's own repo is vacuous. This test MUST fail against
    current main.
  evidence:
  - tests/test_gates_mutation_evidence.py::TestMustStillPassIntegration::test_reconstructed_over_narrowed_matcher_fails_the_control
  - tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_fails_at_fix_is_error_violation
  - tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_never_passed_at_parent_is_error_violation
  - tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_passes_at_both_no_violation
  - tests/test_gates_mutation_evidence.py::TestMustStillPassControls::test_multiple_directives_extracted
- text: 'Add a MUST-STILL-PASS control alongside the repro: a designated test (or
    set) that must PASS at the fix commit AND would have passed at the parent, asserting
    the capability the fix narrows is still exercised. --designate-repro/--check-repro
    cover only the negative direction (the test FAILED at parent, proving the bug
    was real). Nothing asserts the positive direction, so ''false positives disappeared''
    is indistinguishable from ''the feature stopped running''. Require it specifically
    for fixes that NARROW a decision rule -- resolution, matching, filtering, gating
    -- where over-correction is silent.'
  evidence:
  - tests/test_gates_mutation_evidence.py::TestMustStillPassIntegration::test_reconstructed_over_narrowed_matcher_fails_the_control
  - tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_fails_at_fix_is_error_violation
  - tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_never_passed_at_parent_is_error_violation
  - tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_passes_at_both_no_violation
  - tests/test_gates_mutation_evidence.py::TestMustStillPassControls::test_multiple_directives_extracted
- text: 'Do NOT satisfy this by requiring ''more tests'' or a coverage threshold --
    the missing thing is a SPECIFIC claim (this capability still works), not volume,
    and a coverage number cannot express it. Do NOT infer the control automatically
    from the existing suite passing: in all three instances above the suite passed,
    because the disabled capability had no test asserting it still functioned. The
    control must be an explicit, named designation the author makes, the same way
    --designate-repro is.'
  evidence:
  - tests/test_gates_mutation_evidence.py::TestMustStillPassIntegration::test_reconstructed_over_narrowed_matcher_fails_the_control
  - tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_fails_at_fix_is_error_violation
  - tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_never_passed_at_parent_is_error_violation
  - tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_passes_at_both_no_violation
  - tests/test_gates_mutation_evidence.py::TestMustStillPassControls::test_multiple_directives_extracted
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

Added `must_still_pass_violations` (BUG003) to
src/frob/gates/_mutation_evidence.py, the positive-direction control
BUG002/TEST016 have no counterpart for -- both of those only prove a
negative claim (a repro that failed before the fix, a mutant this
ticket's evidence kills); a narrowing fix that over-corrects until it
accepts/matches NOTHING satisfies both vacuously, exactly the shape
this ticket's own body documents (T-2156, T-2177, `frob cycle`, all
measured passing every existing gate).

Mechanism (mirrors this file's own `_bug002_waiver_reason`/
`_no_behavior_change_reason` body-text-directive precedent, since this
ticket's declared scope is a single source file -- no `Ticket` model
field, no new CLI flag): `frob:must-still-pass NODE-ID` in a ticket's
body (`_must_still_pass_controls`, regex-extracted, supports multiple
directives) names a pytest node id that must PASS at the ticket's own
fix AND would have PASSED at the parent commit too. `must_still_pass_
violations` runs it both ways (reusing `_run_designated_test` for the
fix side and the existing `_bug_repro_outcome_at_ref` for the parent
side -- no new subprocess/checkout machinery). BUG003 fires (always
ERROR) in exactly two shapes: the control FAILS at the fix (the
capability broke -- the incident this control exists to catch), or the
control never PASSED at the parent either (a misconfigured designation
that never proved a "working before" baseline). Every other outcome
(both pass; either side unresolvable) degrades to no violation, mirroring
BUG002's own infra-failure posture. Deliberately opt-in and explicit
(acceptance criterion 2): the directive is the only trigger, never
inferred from the evidence set or the suite passing.

Full mechanism/rationale documented at
docs/modules/tickets-landing.md#bug003-the-positive-direction-must-still-pass-control-t-2193.

Acceptance criterion 0 ("this test MUST fail against current main"):
satisfied by construction -- `must_still_pass_violations` does not exist
on main at all; every new test importing it fails to collect there.
`TestMustStillPassIntegration::test_reconstructed_over_narrowed_matcher_
fails_the_control` additionally reconstructs the T-2156 shape end-to-end
with two real git commits (a working narrow-by-suffix matcher, then a
"narrowed" version that accepts nothing) and asserts BUG003 fires --
same real-subprocess posture `TestBugRepro`'s existing tests already use
for BUG002, no mocking.

Acceptance criterion 1 (measure + judge, not just count): N/A in the
literal T-2205 sense (that criterion's wording describes T-2205's own
DEAD001/COV006 blast-radius measurement) -- T-2193's own deliverable is
the control mechanism itself; its test suite (11 tests) exercises every
branch of the decision table (both pass / fails at fix / never passed at
parent / unresolvable-at-fix / unresolvable-at-parent / multiple
directives), each asserted individually rather than a bare count.

Acceptance criterion 2 (no auto-inference, explicit designation only):
`_must_still_pass_controls` returns `()` whenever no `frob:must-still-
pass` directive is present in the ticket body -- `test_no_directive_no_
violation` asserts `_run_designated_test` is never even called in that
case. There is no coverage-threshold or "more tests" satisfaction path
anywhere in the implementation.

Did NOT wire `must_still_pass_violations` into any `frob ticket land`/
`close` call site -- T-2193's own declared scope is
src/frob/gates/_mutation_evidence.py alone (plus its doc/test files,
added via `frob ticket scope --add`), the same single-file discipline
its sibling ticket T-2205 used. Filed T-2215 for the wiring
follow-up (scope src/frob/tickets/_land.py, src/frob/app/ticket_runner/
_close_cmd.py, src/frob/gates/_waive.py -- all outside this ticket's own
scope).

Did NOT designate any of the new tests via `--designate-repro`: every
new test in tests/test_gates_mutation_evidence.py imports `must_still_
pass_violations` at module scope, so ALL of them fail to COLLECT at the
parent commit (ImportError, not a clean assertion failure) -- this is a
collection error, which `bug_repro_outcome_at_ref` classifies as
NO_VERDICT, and `--designate-repro`'s validate-at-designate check
(playbook section 0 item 6) refuses to designate on NO_VERDICT (T-1929).
This does not block BUG002 at land time either way: NO_VERDICT degrades
to no violation there too (an infra-shaped "cannot measure" is never a
false pass or a false violation), so plain evidence binding (no
designation) is the correct, honest choice here, not a workaround.

Changed: src/frob/gates/_mutation_evidence.py (`_MUST_STILL_PASS_RE`,
`_must_still_pass_controls`, `must_still_pass_violations`,
`_must_still_pass_broke_at_fix_message`,
`_must_still_pass_never_passed_message`; `__all__` updated).
docs/modules/tickets-landing.md (new `### BUG003` section).
tests/test_gates_mutation_evidence.py (`TestMustStillPassControls`,
`TestMustStillPassViolations`, `TestMustStillPassIntegration`, 11 tests).
Evidence: tests/test_gates_mutation_evidence.py::
TestMustStillPassIntegration::
test_reconstructed_over_narrowed_matcher_fails_the_control (--accepts
0 1 2); tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::
test_fails_at_fix_is_error_violation (--accepts 0 1 2);
tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::
test_never_passed_at_parent_is_error_violation (--accepts 0 1 2);
tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::
test_passes_at_both_no_violation (--accepts 0 1 2);
tests/test_gates_mutation_evidence.py::TestMustStillPassControls::
test_multiple_directives_extracted (--accepts 0 1 2). Full file:
`uv run pytest tests/test_gates_mutation_evidence.py -o addopts="" -q`
-> 45 passed (up from 34 pre-ticket; 11 new). `uv run ruff check
src/frob/gates/_mutation_evidence.py tests/test_gates_mutation_evidence.py`
-> All checks passed. `frob check --only fmt/lint --ticket T-2193` ->
clean for both touched files (a pre-existing CRLF artifact from the
edit tooling was normalized back to LF before verifying; git's own
core.autocrlf=true confirmed this was a working-tree display artifact,
not a real content change).
Also registered "BUG003" in src/frob/gates/_waive.py's
`_KNOWN_GATE_RULES` (T-1937 requires this before a ticket constructing a
new rule id can close at all) -- added to scope via `frob ticket scope
--add`, minimal one-entry addition mirroring BUG002's own precedent
entry immediately above it.
Filed: T-2215 (wiring follow-up, renumbers at land).
Gates: `frob check --only gates-fast --ticket T-2193` -- every finding
touching src/frob/gates/_mutation_evidence.py or
tests/test_gates_mutation_evidence.py or the new doc section is either
resolved (FMT001, fixed) or pre-existing repo-wide debt unrelated to
this change (confirmed by file/line: DOC006/INV003/INV004/NEGEXIST001
hits in docs/modules/tickets-landing.md are pre-existing entries
elsewhere in the same file, plus one NEGEXIST001 on my own new "Not yet
wired" sentence, which matches this doc's own existing, unfixed
"Not yet wired to a frob ticket scope CLI flag" precedent at
tickets-landing.md#evidence-only-scope-t-1944 -- same WARN-level,
pre-existing convention, not a new gap this ticket introduces).

### Changed
```
 docs/modules/tickets-landing.md       |  56 +++++++++
 rapid-debt.jsonl                      |   1 +
 src/frob/gates/_mutation_evidence.py  | 161 +++++++++++++++++++++++-
 tests/test_gates_mutation_evidence.py | 224 ++++++++++++++++++++++++++++++++++
 tickets/T-2193/done-report.md         | 136 +++++++++++++++++++++
 tickets/T-2193/ticket.md              |  51 +++++++-
 tickets/T-2215/ticket.md    |  66 ++++++++++
 7 files changed, 690 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_gates_mutation_evidence.py::TestMustStillPassIntegration::test_reconstructed_over_narrowed_matcher_fails_the_control` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_fails_at_fix_is_error_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_never_passed_at_parent_is_error_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMustStillPassViolations::test_passes_at_both_no_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMustStillPassControls::test_multiple_directives_extracted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2193/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2193, SELFAUDIT001@design, TEST010@tests/test_lang.py, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md, WIRE001@src/frob/gates/_mutation_evidence.py
