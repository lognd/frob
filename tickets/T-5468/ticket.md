---
id: T-5468
title: 'REG008 burn-down: 249 findings against check-coverage.yaml registry'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 're-measured 2026-09-24: all 248 REG008 findings against
  check-coverage.yaml are reserved-not-yet-implemented WEBSEC/A11Y/COMPLY/LAUNCH/SEO/SQL/WEBPERF
  entries (T-5140/T-5301 epic), 100% inside src/frob/webapp/** and src/frob/sql/**,
  both out of touch-scope per standing brief; zero non-webapp/sql findings exist to
  fix here'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: '3'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
body_changes:
- mode: append
  reason: investigated per coordinator priority; every REG008 finding is in webapp/sql-owned
    rule families, 100% out of touch-scope
  actor: logan
  at: '2026-09-24'
  old_length: 828
  new_length: 1932
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml

The test expects zero REG008 findings against
docs/design/registry/check-coverage.yaml; the real repo currently produces
249 ERROR-severity REG008 findings (assert [...] == [] fails with "Left
contains 248 more items" i.e. 249 total). Sample finding: "REG008: ...
relative to the enforcing rule, or re-disposition the entry".

Size (249) suggests either a bulk-generated registry file gone stale
against real coverage, or a detector regression that started flagging
entries it previously accepted. This drain pass did not have time to
root-cause which; needs a dedicated read of REG008's detector plus
check-coverage.yaml's recent history.


BLOCKED (investigated, not fixed): all 248 REG008 findings against
docs/design/registry/check-coverage.yaml resolve to entry ids in exactly
these families: CHK-GATE-WEBSEC101-115 (108 entries), CHK-GATE-A11Y102-131
(30 entries), CHK-GATE-COMPLY101-127 (27), CHK-GATE-LAUNCH101-107 (7),
CHK-GATE-SEO101-127 (27), CHK-GATE-SQL101-130 (30), CHK-GATE-WEBPERF101-115
(15) -- every single one is a WEBSEC/A11Y/webapp-adjacent or SQL rule
family, i.e. entirely inside src/frob/webapp/** and src/frob/sql/**, both
explicitly out of touch-scope for this drain (other-agent-owned). There is
no non-webapp/non-sql REG008 finding in this set at all -- this whole
cluster is 100% blocked, not partially fixable. Each entry needs either a
`frob:enforces CHK-GATE-<RULE>` directive added to its implementing rule
function (if the rule is actually implemented and the directive was
simply omitted), or re-dispositioning in check-coverage.yaml if the rule
is not yet implemented (a large registry apparently pre-populated ahead
of the rules' actual implementation). Handing off whole to the webapp/sql
owning agent(s).
