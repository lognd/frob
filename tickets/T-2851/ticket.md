---
id: T-2851
title: Split BUG002/must-still-pass repro-classification family out of frob.gates._mutation_evidence
state: done
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_mutation_evidence.py
evidence_scope:
- tests/gates/test_bug_repro_at_ref_public.py
- tests/test_gates_mutation_evidence.py
- tests/unit/test_ticket_runner_designate_repro.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: T-2851 is a pure code-move refactor with no intended behavior change; BUG002
    needs this directive to check the correct (inverted) obligation instead of requiring
    a fails-then-passes repro test that does not apply to a refactor
  actor: logan
  at: '2026-08-22'
  old_length: 2267
  new_length: 2790
evidence:
- tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic::test_wraps_the_private_classifier
- tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_failed_at_parent_no_violation
- tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent::test_refuses_passed_at_parent
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 3a3d153c3ebccd2504f05f2e5ab75275915fb5e6
---
src/frob/gates/_mutation_evidence.py's module docstring claims it implements only TEST016 (T-0755's diff-scoped adversarial evidence obligation), but the file also contains the entire BUG002/MUST-STILL-PASS repro-classification family: _BugReproOutcome, _checkout_bug_repro_worktree, _spawn_designated_test, _classify_designated_test_exit, _run_designated_test, bug_repro_outcome_at_ref, bug_repro_violations, must_still_pass_violations, and their message builders -- roughly 800 of the file's 1267 lines, lines ~463-1267.

This is a real consumer-set seam: TEST016/TEST018 (lines ~72-260) plus the shared quoted-range helpers (_quoted_char_ranges/_double_quote_char_ranges/_is_quoted, lines ~277-462, re-imported by frob.gates._tickets_gate) are one concern (diff-scoped mutation-evidence confirmation), while BUG002/must-still-pass is a completely separate concern (repro-outcome classification for bug/security tickets, worktree checkout, subprocess spawn/classify) with no shared helper calls into the TEST016 side.

Filed rather than split in T-2827's own diff because frob.gates.bug_repro_outcome_at_ref is a load-bearing, land-critical shared entrypoint (frob.tickets._land's pre-land check AND frob.app.ticket_runner's close-time CLI path both call it directly, per this repo's own recorded incident history around BUG002/T-1929/T-2019). A split of this scope deserves its own dedicated review pass (verify every caller's import path, re-run the full BUG002 test suite, confirm no behavior change) rather than being folded into a LARGE001 line-count batch -- the same 'waived rather than force-split in the same diff to preserve review guarantee' precedent T-2833 already used for src/frob/tickets/_land_git_ops.py.

Plan: extract _BugReproOutcome and everything from _bug002_waiver_reason through must_still_pass_violations (plus their message builders) into a new src/frob/gates/_bug_repro.py; re-export bug_repro_outcome_at_ref/bug_repro_violations/must_still_pass_violations from frob.gates._mutation_evidence (or update the two known call sites directly) so no import path outside this file needs to change without review; verify the resulting _mutation_evidence.py (TEST016/018 plus shared quoting helpers) drops under the LARGE001 threshold on its own.

frob:no-behavior-change reason="pure module split -- BUG002/must-still-pass classification code moved verbatim from _mutation_evidence.py into new _bug_repro.py, re-exported so every external caller (frob.tickets._land, frob.app.ticket_runner) keeps the same import path; verified via full affected test suite (96 tests) plus land-adjacent suites (29 tests), arch_gate()+_apply_waivers() clean, and a positive control confirming the rewritten mock.patch targets actually intercept. No intended behavior change anywhere."