---
id: T-3324
title: Live-repo self-conformance tests need landing-time enforcement, not just periodic
  re-verification
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_sys.py
- src/frob/tickets/_land_squash.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3283 fixed 6 of T-3041's 13 live-repo self-conformance tests
(test_sys_gate_zero_violations, test_repo_unrestricted_scan_is_clean,
test_repo_design_and_declarations_are_self_conformant,
test_real_repo_design_selfconform_has_no_eval_gap,
test_doc004_doc006_zero_against_live_repo,
test_no_reg008_findings_for_check_coverage_yaml) -- all had gone from
GENUINELY GREEN at their respective fixing ticket's land (verified by
land-history bisection: T-3041's own land commit 034f4fbae, T-3224's
land commit 0b723f1fe) to red again, purely from ~40 unrelated,
individually-correct ticket lands accumulating drift onto the same
shared self-conformance surface (design/frob.strata's capability
declarations, docs/design/registry/check-coverage.yaml's REG008
exhaustiveness, ticket-body DOC006 pointers).

THE STRUCTURAL PROBLEM (T-3283's own finding, restated here as its own
ticket per that ticket's explicit ask not to let this go unaddressed):
a test that asserts "this repo is currently clean against the live
gates" cannot stay true under continuous, unrelated development -- it
passes at close and rots as later work lands, because no individual
land's own frob check scope covers cross-ticket self-conformance
drift (each land only checks its own diff). This is not bad luck or a
one-off regression; it is a structural property of the whole class of
"clean against a live, changing repo" test. Two prior occurrences of
the identical mechanism are already tracked: T-3227/T-3236/T-3237/
T-3238 (a repeating "post-land sweep regression" pattern) and now this
one, observed through the direct pytest lens instead of the sweep's
lens. A third occurrence is close to guaranteed without a structural
fix.

T-3283 names two options, neither built yet:
(a) LATE GATING: keep the current shape (a slow, periodic/manual
    full-repo re-verification), but shrink the window between
    "known broken" and "someone notices" -- e.g. wire the existing
    slow self-conformance tests (or a cheaper incremental variant) into
    the rapid-sweep post-land detached check (T-1684's architecture)
    so a land that pushes the shared surface non-conformant gets
    reported within one land cycle, not discovered cold the next time
    someone happens to run the slow test file directly.
(b) LANDING-TIME ENFORCEMENT: make cross-ticket self-conformance drift
    a real land-time gate for any land that touches the shared surface
    (design/frob.strata, docs/design/registry/*.yaml, capability-via-
    ratchet.lock.json) -- a land that pushes SYS100/DOC006/REG008
    non-conformant on repo-wide scope (not just its own diff) refuses,
    the same way other structural gates already do. T-3247 already had
    to raise these tests' own pytest-timeout specifically because
    whole-repo scans are expensive (docs/strata/selfconform.md) -- that
    cost is exactly why this class of drift is currently caught late
    (a slow full test) instead of early (a fast per-land check); a
    land-time gate needs an answer to that cost question (incremental
    check against a cached prior-green baseline, most likely) before
    it can run on every land without becoming the next frob check
    performance complaint.

Whoever picks this up should choose (a) or (b) explicitly (or both --
they are not mutually exclusive) rather than re-deferring the decision
again.

ACCEPTANCE
- A decision recorded: (a), (b), both, or an explicit reasoned
  "neither, because X" -- not silence.
- If (a) and/or (b) is built: a demonstrated case where a change that
  would have caused another silent SYS100/DOC006/REG008 regression is
  now caught within one land cycle (or refused outright for (b)),
  not discovered cold by the next slow full-repo test run.