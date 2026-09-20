---
id: T-draft-af37d815
title: 'templated-assume gate: refuse assumes identical after node/module substitution
  and shared expiry across modules (D-M8), red on todays design/frob.strata'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-draft-0a0c7b43
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_assume_template.py
- src/frob/gates/_sys_selfaudit.py
- tests/gates_suite/test_sys_assume_template.py
- docs/strata/selfconform.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: Given today's design/frob.strata, when the templated-assume gate runs, then
    it is RED and reports the 33 boilerplate CWE assumes (SF-08) by node and rule
    id -- this is the gate's positive control and a green result is a failure of the
    leaf.
  evidence: []
- text: Given two assumes whose text differs only by the node or module name, when
    the gate runs, then both are reported, and the comparison is shown to be token-level
    (a rename-only difference is caught; an assume with genuinely different wording
    that shares keywords is NOT reported).
  evidence: []
- text: Given more than N modules whose assumes share one expiry date, when the gate
    runs, then the shared-expiry finding names every participating module.
  evidence: []
- text: Given a module-owned specific assume whose reason names a concrete mechanism
    or evidence gap, when the gate runs, then it is not reported.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Templated-assume gate (owner decision D-M8, OVERRIDDEN and strengthened from the
proposal). The 33 boilerplate CWE assumes (SF-08: one template per node per CWE,
identical owner and date) are NOT carried over. An assume must be module-owned
and specific: its reason text names the concrete mechanism or evidence gap for
THAT module.

Ship a structural gate that refuses templated assumes:
  - two assumes whose text is IDENTICAL AFTER SUBSTITUTING the node/module name
    are a finding. Token-level comparison over the parsed assume text, not a
    keyword or regex heuristic (owner directive: checks decide from parsed
    symbols, never lexically).
  - assumes sharing a single expiry date across more than N modules are a
    finding (N configurable, defaulted and documented).
Gate lives alongside the self-audit rules in src/frob/gates/_sys_selfaudit.py
with its detector in a new src/frob/strata/_assume_template.py.

POSITIVE CONTROL, mandatory: the gate must be RED on today's design/frob.strata,
reporting the 33 boilerplate CWE assumes. A green run against the current
monolith means the gate does not work and the leaf is not done.

## Unblock log
- 2026-09-19: unblocked by T-draft-a693d397 -- the gate groups by file until the kernel module attribute lands; owner wants the gate red on today's design now, the kernel leaf is itself blocked by T-3964
