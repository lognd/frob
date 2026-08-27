---
id: T-3141
title: 'T-3034 residual: close may no longer refuse unrelated evidence (D-02 regression?)'
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_evidence_enforcement.py
- src/frob/tickets/_evidence.py
- tests/unit/test_tickets_evidence_only_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/
  reason: T-3141 investigation shows the regression + fix is confined to add_evidence's
    auto-widen of evidence_scope in _evidence.py, plus the T-1944 test suite it broke;
    the whole tickets/ and ticket_runner/ dirs are not needed and collide with concurrent
    leases
  actor: logan
  at: '2026-08-27'
- op: remove
  glob: src/frob/app/ticket_runner/
  reason: T-3141 investigation shows the regression + fix is confined to add_evidence's
    auto-widen of evidence_scope in _evidence.py, plus the T-1944 test suite it broke;
    the whole tickets/ and ticket_runner/ dirs are not needed and collide with concurrent
    leases
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: T-3141 investigation shows the regression + fix is confined to add_evidence's
    auto-widen of evidence_scope in _evidence.py, plus the T-1944 test suite it broke;
    the whole tickets/ and ticket_runner/ dirs are not needed and collide with concurrent
    leases
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_tickets_evidence_only_scope.py
  reason: T-3141 investigation shows the regression + fix is confined to add_evidence's
    auto-widen of evidence_scope in _evidence.py, plus the T-1944 test suite it broke;
    the whole tickets/ and ticket_runner/ dirs are not needed and collide with concurrent
    leases
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/system/test_cli_evidence_enforcement.py
  reason: T-3141 investigation shows the regression + fix is confined to add_evidence's
    auto-widen of evidence_scope in _evidence.py, plus the T-1944 test suite it broke;
    the whole tickets/ and ticket_runner/ dirs are not needed and collide with concurrent
    leases
  actor: logan
  at: '2026-08-27'
evidence:
- tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd::test_close_fails_on_unrelated_evidence
- tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd::test_close_fails_on_red_evidence
- tests/unit/test_tickets_evidence_only_scope.py::TestAddEvidenceAutoPopulatesEvidenceOnlyScope::test_evidence_already_covered_by_scope_widens_nothing
- tests/unit/test_tickets_evidence_only_scope.py::TestEvidenceOnlyScopeNeverLeases::test_evidence_scope_path_does_not_block_another_tickets_add
- tests/unit/test_tickets_evidence_only_scope.py::TestEvidenceCoversScopeWithEvidenceOnlyScope::test_evidence_covers_scope_true_via_evidence_scope_alone
- tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly::test_demote_releases_the_lease_and_keeps_evidence_covered
- tests/unit/test_tickets_evidence_only_scope.py::TestAddEvidenceAutoPopulatesEvidenceOnlyScope::test_new_evidence_widens_evidence_scope_not_scope
designated_repro_test: tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd::test_close_fails_on_unrelated_evidence
evidence_changes:
- old_node: tests/unit/test_tickets_evidence_only_scope.py::TestAddEvidenceAutoPopulatesEvidenceOnlyScope::test_new_evidence_never_auto_widens_evidence_scope
  new_node: tests/unit/test_tickets_evidence_only_scope.py::TestAddEvidenceAutoPopulatesEvidenceOnlyScope::test_evidence_already_covered_by_scope_widens_nothing
  reason: 'T-3141: the renamed test was reverted back to its original T-1944 name
    to avoid orphaning T-1944''s own evidence; this stale citation is being replaced
    by another already-passing sibling test in the same class covering the same corrected
    behavior'
  actor: logan
  at: '2026-08-27'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description
T-3034 per-test triage: tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd::test_close_fails_on_unrelated_evidence is failing and the failure looks like a real regression in D-02's evidence-scope-binding enforcement, not test staleness.

The test's own repro: a ticket scoped to src_a/, evidence bound to an UNRELATED passing test (tests/test_unrelated.py::test_it, neither in scope nor reachable by graph edge from it), then `frob ticket close T-0001 --evidence tests/test_unrelated.py::test_it`.

Expected (D-02's whole point): close refuses, "EvidenceScopeUnbound" in output, returncode != 0.

Observed on current main: close SUCCEEDS (returncode 0). Captured stdout/stderr shows:
  T-0001: evidence now has 1 id(s): ['tests/test_unrelated.py::test_it']
  T-0001 closed (done)
  ERROR: run_selected: language 'python' has selected tests but no runner -- add a [[test.runner]] entry with language = 'python' to frob.toml at the repo root (see docs/modules/testing.md)
  ERROR: run_selected: language 'python' has selected tests but no runner -- add a [[test.runner]] entry with language = 'python' to frob.toml at the repo root (see docs/modules/testing.md)

Two things worth separating:
1. The test's own tmp-repo fixture apparently has no [[test.runner]] entry in frob.toml, which is itself possibly a fixture gap (a runner config that used to be implicit and is now required) -- but that ERROR alone should not let the evidence-scope check be skipped/bypassed; if the evidence-scope check runs BEFORE test execution and the test-runner-missing error only fires afterward, close should still have refused before ever getting there.
2. Either the evidence-scope-binding check (EvidenceScopeUnbound) is not firing at all for this scenario any more, or an earlier-than-expected exception path (the missing runner) is causing the close to short-circuit past the refusal into a false "closed (done)" state.

This needs someone to step through frob ticket close's evidence-binding code path with a debugger/print-tracing against this exact repro to determine: (a) is EvidenceScopeUnbound still being computed/checked at all, (b) if yes, why isn't it firing, (c) if no, when did it stop being wired into `close`, and (d) is the "no runner" ERROR path silently swallowing a would-be refusal or just cosmetic noise.

## Plan
1. Reproduce test_close_fails_on_unrelated_evidence locally, confirm it still fails on main at this landing's tip.
2. Read `frob ticket close`'s implementation (src/frob/app/ticket_runner or src/frob/tickets, wherever EvidenceScopeUnbound is raised) and trace whether the scope-binding check is still invoked in this control flow, and whether the run_selected/no-runner error path bypasses it.
3. If a real regression: fix the product code so close correctly refuses on unrelated evidence again (D-02 must hold), with the test as the fix's own repro (BUG002: test must fail at parent commit -- it already does).
4. If the fixture (missing [[test.runner]]) is the actual cause and D-02 itself is fine once a runner is configured: fix the test fixture and re-verify D-02 fires correctly.
5. Either way, re-run the other D-01/D-02/D-03 siblings in this same file (test_close_fails_on_stale_evidence etc, if any) to confirm they still correctly enforce -- a scope-binding regression here would likely affect siblings too.