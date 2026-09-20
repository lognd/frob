---
id: T-5122
title: land must fail when LAND-PROOF claims re-verification is SKIPPED-UNMEASURED
state: in-progress
kind: bug
origin: human
created: '2026-09-20'
priority: high
parent: T-4651
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_land_verify.py
- tests/ticket_land_suite/test_land_proof_unmeasured.py
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'T-5122: the claims-reverify outcome gate must run at land()''s own call
    site, immediately after the outcome is computed and before the dry-run early return,
    so the refusal is real for a dry run too'
  actor: logan
  at: '2026-09-20'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-20: /tmp/land-T-4550.log printed LAND-PROOF verified=SKIPPED-UNMEASURED and LAND-EXIT=0; the ancestry half was true but the claims re-verification half reported unknown while the command claimed success (silent-zero class). src/frob/tickets/_land_verify.py (lines near 61 and 83) renders measured and unmeasurable verdicts on the same line. Fix: in src/frob/tickets/_land_finalize.py, any verdict other than True is a non-zero exit from the land path unless an explicit override is recorded in force-overrides.jsonl through the T-1762 mechanism already used by ticket archive --force. Positive control: a land whose verification is forced to unmeasurable exits non-zero and leaves dev untouched; a measured-true land is unchanged.
