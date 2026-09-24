---
id: T-draft-5f8f0b95
title: 'mutation_audit: may-clause annotations drifted from real repo mutation findings'
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
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing (both
node ids, same file/class):
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing

test_second_detector_gaps: gap_kinds now includes 'html_render' which the
test's hardcoded expected set {"process-control", "net-mutate",
"net.connect"} does not name.

test_every_may_is_load_bearing: 6 MutationFinding entries fail the
assertion; sample -- node='graphlang', atom='eval', mode='substitute',
sys100_fired=True, sys101_fired=False, sys101_expected=True (detector says
SYS101 should have fired for this mutation but it did not).

Both point at design/frob.strata's may-clause mutation-audit annotations
(or the detectors reading them) having drifted from what the real repo now
does. Needs the strata module's mutation-audit maintainer to reconcile
design/frob.strata against tests/unit/strata/test_mutation_audit.py's
current expectations -- not root-caused to a one-line fix in this pass;
filed with full finding detail above.
