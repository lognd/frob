---
id: T-1482
title: build policy refinement-monotonicity diff pass (INV-030)
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/strata/policy.md
- src/frob/strata/_mutation_audit.py
- src/frob/strata/_native_staleness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
designated_repro_test: null
threat: null
component: null
---
docs/strata/policy.md documents that policy refinement is DESIGNED to be
monotonic downward (a child may only strengthen an inherited policy,
never weaken it), but compile_policies/_resolve_scope only resolve scope
membership -- there is no refinement-diff pass that compares a child's
policy set against its parent's and flags a weakening. The paragraph
currently states design intent, not an enforced guarantee (also
disclosed via a frob:waive INV003 reason on the same section). Build
the refinement-diff pass. Found while draining NEGEXIST001
(T-1477): the doc's absence-claim had no frob:until binding.