---
id: T-2323
title: 'T-2303 child: SELFAUDIT001 capability declaration + ratchet ceiling bump (needs
  deliberate review, no auto-update per T-1870)'
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: T-2303
tier: ticket
sprint: null
runs_last: false
scope:
- design
- tests/unit/test_land_sibling_regression.py
- tests/unit/test_new_ticket_scope_overlap_warning.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Child of T-2303 (parent scope: ARCH001/ARCH103/PERF004/SELFAUDIT001 debt
found by T-2206's sweep). This is the SELFAUDIT001 piece.

NEEDS A DELIBERATE REVIEWED DECISION, not a blind edit. This requires:

1. A `design/frob.strata` capability declaration for the 2 undeclared
   effects found:
   - `tests/unit/test_land_sibling_regression.py:275` -- `fs.read`
     (`read_text()` on the testsuite node)
   - `tests/unit/test_new_ticket_scope_overlap_warning.py:24` -- `fs.write`
     (`write_text()` on the testsuite node)
   (Re-measure `frob check --only sys` before starting -- more undeclared
   effects may have accumulated since T-2206's sweep; a live land run
   already surfaced 5 MORE undeclared effects in
   `tests/unit/verify/test_watermark.py` while T-2314 was landing, all
   unrelated to this ticket's own scope -- they are the same class of
   finding and may belong here too, confirm current count first.)

2. A `docs/design/registry/capability-via-ratchet.lock.json` ceiling bump:
   `fs.write` via-list on `core` has grown to 22 sites, above the
   committed ratchet ceiling of 21.

WHY THIS IS NOT A QUICK FIX: per T-1870 (an explicit owner directive,
recorded in docs/guides/agent-playbook.md section 0 item 5), NO CODE PATH
MAY AUTO-UPDATE A DECLARED PUBLIC-SYMBOL SURFACE. A capability declaration
in `design/frob.strata` and a ratchet ceiling in the ratchet lock file are
exactly this class of declared surface -- widening either is a decision
about what this repo's security/capability model considers acceptable
growth, not a mechanical fix. The assigned agent should:
  - Read `design/frob.strata`'s existing capability declaration syntax and
    docs/strata/* (boundary.md, surface.md, waive.md) before touching
    anything.
  - For the 2 (or more, if re-measurement finds additional) undeclared
    test-file effects: determine whether they should be DECLARED (the
    test genuinely needs fs.read/fs.write and that's fine) or whether the
    test should be restructured to avoid the raw effect (e.g. via an
    existing test-fixture helper that already carries the declaration).
  - For the ratchet ceiling: determine whether 22 is genuine, accepted
    growth (bump the ceiling with a reason) or a site that should be
    consolidated/removed instead (do not bump reflexively).
  - This is a decision for whoever owns `design/frob.strata` and the
    ratchet lock file's policy, not something to resolve unilaterally in
    a burn-down pass.

Scope: design (frob.strata + docs/design/registry/capability-via-ratchet.lock.json),
tests/unit/test_land_sibling_regression.py,
tests/unit/test_new_ticket_scope_overlap_warning.py.
