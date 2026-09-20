---
id: T-4533
title: frob ack cannot resolve a whole-file frob:describes target (yaml/non-python)
state: queued
kind: bug
origin: agent
created: '2026-09-16'
priority: low
parent: null
tier: ticket
sprint: v0.540.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/lock.py
- src/frob/graph/_resolve.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.540.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: GIVEN a frob:describes edge whose target is a bare tracked file with no graph
    symbol (e.g. a .yml workflow) WHEN frob ack <that path> is run THEN it acks the
    edge's whole-file content digest instead of failing UnknownRef
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-4532: docs/modules/tickets-landing.md has <!-- frob:describes .github/workflows/ci.yml --> (a bare non-python file, no python symbol). DRIFT002 flagged it as a dangling edge with 'no candidates found'. frob ack .github/workflows/ci.yml fails with UnknownRef because frob.graph._resolve.resolve() only searches snapshot.symbols (python/parsed-language symbols) -- a describes edge to a whole file that graph parsing never turns into a symbol record can never be acked, only waived. T-4532 worked around this with a frob:waive DRIFT002 on the doc side after manually re-verifying ci.yml still matches the doc paragraph; this ticket is to make ack itself handle a file-level (no ::symbol) describes target by tracking a whole-file content digest, so future re-verification of that section does not need a permanent waiver.